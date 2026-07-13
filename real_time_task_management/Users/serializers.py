# pyrefly: ignore [missing-import]
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification, Task

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        # Hash the password when creating a user
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        # Hash the password if it's being updated
        if 'password' in validated_data:
            instance.set_password(validated_data.pop('password'))
        return super().update(instance, validated_data)

# pyrefly: ignore [missing-import]
class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.filter(role__name='employee'),
        required=True
    )

    class Meta:
        model = Task
        fields = ['id', 'url', 'title', 'description', 'attachment', 'priority', 'assigned_to', 'status', 'due_date']
        read_only_fields = ['created_by']

    def validate_assigned_to(self, value):
        for user in value:
            if not user.role or user.role.name != 'employee':
                raise serializers.ValidationError(f"User '{user.username}' is not an employee. Tasks can only be assigned to employees.")
        return value

    def update(self, instance, validated_data):
        user = self.context['request'].user
        if user.role and user.role.name == 'employee':
            # Employees can only update the status field
            allowed_fields = {'status'}
            validated_data = {k: v for k, v in validated_data.items() if k in allowed_fields}
        return super().update(instance, validated_data)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['recipient', 'message', 'created_at']
