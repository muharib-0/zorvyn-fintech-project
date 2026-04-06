"""
User Management URL configuration.
Admin-only endpoints for user CRUD.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .management_views import UserManagementViewSet

router = DefaultRouter()
router.register('', UserManagementViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
]
