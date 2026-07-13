from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from .serializers import UserSerializer, TaskSerializer, NotificationSerializer
from .permissions import IsAdminOrManagerReadOnly, IsManagerOrAssignedEmployeeTaskPermission
from .models import Task, Notification

User = get_user_model()


class EmailTokenObtainView(APIView):
    """
    POST /api/token/
    Accepts { "email": "...", "password": "..." }
    Returns  { "success": true, "access": "...", "refresh": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        if not email or not password:
            return Response(
                {'success': False, 'error': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {'success': False, 'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'success': True,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)


class TokenRefreshCustomView(APIView):
    """
    POST /api/token/refresh/
    Accepts { "refresh": "..." }
    Returns  { "success": true, "access": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh', '')

        if not refresh_token:
            return Response(
                {'success': False, 'error': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            return Response({
                'success': True,
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {'success': False, 'error': 'Invalid or expired refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

class logout_view(APIView):
    """
    POST /api/logout/
    Accepts { "refresh": "..." }
    Returns  { "success": true, "message": "Successfully logged out." }
    """
    permission_classes = [AllowAny]
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"success": True, "message": "Successfully logged out."})
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    """
    GET  /login/  → renders the HTML login page (browser).
    POST /login/  → accepts { "email": "...", "password": "..." }
                    returns  { "success": true, "access": "...", "refresh": "..." }
    CSRF-exempt for API clients (Postman, mobile apps, etc.)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        if not email or not password:
            return Response(
                {'success': False, 'error': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {'success': False, 'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        userDetail = UserSerializer(user).data
        return Response({
            'success': True,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'userDetail': userDetail,
        }, status=status.HTTP_200_OK)


def logout_page(request):
    """Render the JWT-powered logout page."""
    return render(request, 'Users/logout.html')


class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing user instances.
    Admins have full CRUD access. Managers have read-only access.
    Requires a valid JWT Bearer token.
    """
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrManagerReadOnly]


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class TaskViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing task instances.
    Managers have full CRUD access. Employees can view and update status of their assigned tasks.
    Requires a valid JWT Bearer token.
    """
    serializer_class = TaskSerializer
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated, IsManagerOrAssignedEmployeeTaskPermission]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.role:
            return Task.objects.none()

        if user.role.name == 'manager':
            qs = Task.objects.all()
        elif user.role.name == 'employee':
            qs = Task.objects.filter(assigned_to=user)
        else:
            return Task.objects.none()

        # Exclude completed tasks on list view by default, unless requested by a manager
        if self.action == 'list':
            status_param = self.request.query_params.get('status')
            if status_param == 'completed' and user.role.name == 'manager':
                qs = qs.filter(status='completed')
            else:
                qs = qs.exclude(status='completed')
                
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        
        # Notify assigned employees
        channel_layer = get_channel_layer()
        for employee in instance.assigned_to.all():
            msg = f"You have been assigned a new task: '{instance.title}'"
            Notification.objects.create(recipient=employee, message=msg)
            async_to_sync(channel_layer.group_send)(
                f"user_{employee.id}_notifications",
                {
                    "type": "notification.message",
                    "message": msg,
                    "notification_type": "info"
                }
            )

    def perform_update(self, serializer):
        old_status = self.get_object().status
        instance = serializer.save()
        
        channel_layer = get_channel_layer()

        # If an employee marks the task as COMPLETED, notify the manager
        if (old_status != 'completed' and 
            instance.status == 'completed' and 
            self.request.user.role.name == 'employee'): 
            msg = f"Task '{instance.title}' was marked as completed by {self.request.user.username}."
            Notification.objects.create(recipient=instance.created_by, message=msg)
            async_to_sync(channel_layer.group_send)(
                f"user_{instance.created_by.id}_notifications",
                {
                    "type": "notification.message",
                    "message": msg,
                    "notification_type": "success"
                }
            )
        # Notify assigned employees if a manager updates the task
        elif self.request.user.role.name == 'manager':
            msg = f"Task '{instance.title}' was updated by the manager."
            for employee in instance.assigned_to.all():
                async_to_sync(channel_layer.group_send)(
                    f"user_{employee.id}_notifications",
                    {
                        "type": "notification.message",
                        "message": msg,
                        "notification_type": "info"
                    }
                )

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset for managers to view their notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
