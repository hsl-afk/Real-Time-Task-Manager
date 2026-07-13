from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, TaskViewSet, NotificationViewSet, EmailTokenObtainView, TokenRefreshCustomView, logout_view

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', EmailTokenObtainView.as_view(), name='token_obtain'),
    path('token/refresh/', TokenRefreshCustomView.as_view(), name='token_refresh'),
]
