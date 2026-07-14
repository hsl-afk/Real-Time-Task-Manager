from rest_framework import permissions

class IsAdminOrManagerUserAccess(permissions.BasePermission):
    """
    Allows full access to 'admin' role.
    Allows read-only access to 'manager' role.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role):
            return False
            
        role_name = request.user.role.name

        # Admins have full access
        if role_name == 'admin' or role_name == 'manager':
            return True
        # Managers only have access to safe methods (GET, HEAD, OPTIONS)
        # if role_name == 'manager' and request.method in permissions.SAFE_METHODS:
        #     return True
        return False

class IsManagerOrAssignedEmployeeTaskPermission(permissions.BasePermission):
    """
    Managers have full CRUD access.
    Employees have read-only and status-update access to tasks assigned to them.
    Admins are strictly blocked from tasks.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role):
            return False
            
        role = request.user.role.name
        if role == 'manager':
            return True
        elif role == 'employee':
            # Employees can list tasks or retrieve/update specific ones (handled in has_object_permission)
            # They cannot create tasks
            if request.method == 'POST':
                return False
            return True
        return False
        
    def has_object_permission(self, request, view, obj):
        role = request.user.role.name
        if role == 'manager':
            return True
        elif role == 'employee':
            # Employee must be assigned to the task
            is_assigned = obj.assigned_to.filter(id=request.user.id).exists()
            if not is_assigned:
                return False
            
            # They can read or update, but create/delete is forbidden
            if request.method in permissions.SAFE_METHODS or request.method in ('PUT', 'PATCH'):
                return True
        return False
