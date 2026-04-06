"""
Custom permission classes for role-based access control.

Usage in views:
    permission_classes = [IsAuthenticated, IsAdmin]
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    permission_classes = [IsAuthenticated, IsViewerOrAbove]
"""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """
    Allows access only to users with ADMIN role.
    """
    message = 'Admin access required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'ADMIN'
        )


class IsAnalystOrAbove(BasePermission):
    """
    Allows access to users with ANALYST or ADMIN role.
    """
    message = 'Analyst or Admin access required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ('ANALYST', 'ADMIN')
        )


class IsViewerOrAbove(BasePermission):
    """
    Allows access to any authenticated user (VIEWER, ANALYST, or ADMIN).
    This is essentially the same as IsAuthenticated but makes intent explicit.
    """
    message = 'Authentication required.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
