"""
User service layer.
Business logic for user operations lives here, not in views.
"""
from .models import User


def create_user(validated_data):
    """
    Create a new user with hashed password.
    Called by admin when creating users.
    """
    password = validated_data.pop('password')
    user = User(**validated_data)
    user.set_password(password)
    user.save()
    return user


def deactivate_user(user):
    """
    Soft-deactivate a user by setting is_active=False.
    We never hard-delete users — their records must survive.
    """
    user.is_active = False
    user.save(update_fields=['is_active'])
    return user


def get_all_users():
    """
    Return all users queryset.
    """
    return User.objects.all()
