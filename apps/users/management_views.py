"""
User Management views — Admin only.
Handles listing, creating, updating, and deactivating users.
"""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import User
from .permissions import IsAdmin
from .serializers import UserSerializer, CreateUserSerializer, UpdateUserSerializer
from . import services


@extend_schema(tags=['Users'])
@extend_schema_view(
    list=extend_schema(
        summary='List all users',
        description='Returns a paginated list of all users. Admin only.',
    ),
    retrieve=extend_schema(
        summary='Get user details',
        description='Returns the details of a specific user by ID. Admin only.',
    ),
    create=extend_schema(
        summary='Create a new user',
        description='Admin creates a new user with a specified role (VIEWER, ANALYST, or ADMIN). Password is hashed automatically.',
    ),
    partial_update=extend_schema(
        summary='Update user',
        description='Updates a user\'s role or active status. Admin only.',
    ),
    destroy=extend_schema(
        summary='Deactivate user',
        description='Soft-deactivates a user by setting is_active=False. The user is preserved in the database.',
        responses={200: None},
    ),
)
class UserManagementViewSet(viewsets.ModelViewSet):
    """
    Admin-only viewset for managing users.

    GET    /api/users/        — List all users
    POST   /api/users/        — Create a new user (admin assigns role)
    GET    /api/users/{id}/   — Get single user
    PATCH  /api/users/{id}/   — Update role or status
    DELETE /api/users/{id}/   — Deactivate user (soft delete)
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateUserSerializer
        if self.action in ('update', 'partial_update'):
            return UpdateUserSerializer
        return UserSerializer

    def perform_create(self, serializer):
        """Admin creates a user with a specified role."""
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """
        Soft-delete: deactivate the user instead of hard deleting.
        """
        user = self.get_object()
        if user == request.user:
            return Response(
                {'error': True, 'message': 'You cannot deactivate yourself.', 'details': {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        services.deactivate_user(user)
        return Response(
            {'message': f'User {user.username} has been deactivated.'},
            status=status.HTTP_200_OK,
        )

