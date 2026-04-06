from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model with role-based access control.
    Roles: VIEWER (read-only), ANALYST (read + analytics), ADMIN (full access).
    """

    class Role(models.TextChoices):
        VIEWER = 'VIEWER', 'Viewer'
        ANALYST = 'ANALYST', 'Analyst'
        ADMIN = 'ADMIN', 'Admin'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
        help_text='User role determining access level.',
    )

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.username} ({self.role})'

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_analyst_or_above(self):
        return self.role in (self.Role.ANALYST, self.Role.ADMIN)
