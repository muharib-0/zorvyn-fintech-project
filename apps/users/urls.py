"""
Auth URL configuration.
Handles login, token refresh, and user profile.
"""
from django.urls import path
from .views import LoginView, RefreshTokenView, MeView

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),
]
