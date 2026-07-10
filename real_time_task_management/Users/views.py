from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, TaskSerializer
from .permissions import IsAdminOrManagerReadOnly, IsManagerOrAssignedEmployeeTaskPermission
from .models import Task

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

        # EmailBackend maps the 'username' kwarg to email lookup
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


def login_page(request):
    """Render the JWT-powered login page (no session logic)."""
    return render(request, 'Users/login.html')


class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing user instances.
    Admins have full CRUD access. Managers have read-only access.
    Requires a valid JWT Bearer token.
    """
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrManagerReadOnly]


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
            return Task.objects.all()
        elif user.role.name == 'employee':
            return Task.objects.filter(assigned_to=user)
        return Task.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
