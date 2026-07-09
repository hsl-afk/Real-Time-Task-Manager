from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model, logout
from django.shortcuts import render, redirect
from .serializers import UserSerializer, TaskSerializer, NotificationSerializer
from .permissions import IsAdminOrManagerReadOnly, IsManagerOrAssignedEmployeeTaskPermission
from .models import Task, Notification

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing user instances.
    Admins have full CRUD access. Managers have read-only access.
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

def custom_logout(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    return render(request, 'Users/logout.html')
