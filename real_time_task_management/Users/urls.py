from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, TaskViewSet, NotificationViewSet, TokenRefreshCustomView, logout_view, ChangePasswordView, ForceChangePasswordView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('token/refresh/', TokenRefreshCustomView.as_view(), name='token_refresh'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/force-change-password/', ForceChangePasswordView.as_view(), name='force_change_password'),
]
