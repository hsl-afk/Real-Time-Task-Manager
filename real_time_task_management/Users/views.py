from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model, logout
from django.shortcuts import render, redirect
from .serializers import UserSerializer, TaskSerializer
from .permissions import IsAdminOrManagerReadOnly, IsManagerOrAssignedEmployeeTaskPermission
from .models import Task

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing user instances.
    Admins have full CRUD access. Managers have read-only access.
    """
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrManagerReadOnly]

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
            return Task.objects.all()
        elif user.role.name == 'employee':
            return Task.objects.filter(assigned_to=user)    
        return Task.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

def custom_logout(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    return render(request, 'Users/logout.html')
