"""
User views — Auth endpoints and user profile.
"""
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiExample

from .serializers import UserSerializer, CustomTokenObtainPairSerializer


@extend_schema(tags=['Auth'])
class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Authenticate with username and password to receive JWT tokens.
    Returns access token, refresh token, and user profile information.
    """
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(tags=['Auth'])
class RefreshTokenView(TokenRefreshView):
    """
    POST /api/auth/refresh/

    Submit a valid refresh token to receive a new access token.
    The refresh token is rotated on each use.
    """
    permission_classes = [AllowAny]


class MeView(APIView):
    """
    GET /api/auth/me/

    Returns the authenticated user's profile including role information.
    Requires a valid JWT access token in the Authorization header.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth'],
        responses={200: UserSerializer},
        summary='Get current user profile',
        description='Returns the profile of the currently authenticated user.',
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

