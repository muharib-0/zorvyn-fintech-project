from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for user data. Never exposes password.
    """

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'is_active', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']


class CreateUserSerializer(serializers.ModelSerializer):
    """
    Serializer for admin to create new users.
    Password is write-only and will be hashed.
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='Minimum 8 characters.',
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'password', 'role', 'is_active']
        read_only_fields = ['id']

    def validate_role(self, value):
        """Ensure role is a valid choice."""
        valid_roles = [choice[0] for choice in User.Role.choices]
        if value not in valid_roles:
            raise serializers.ValidationError(
                f'Invalid role. Must be one of: {", ".join(valid_roles)}'
            )
        return value

    def create(self, validated_data):
        """Create user with hashed password."""
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UpdateUserSerializer(serializers.ModelSerializer):
    """
    Serializer for admin to update user role and status.
    Only allows updating role and is_active.
    """

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'is_active']
        read_only_fields = ['id', 'username', 'email']

    def validate_role(self, value):
        """Ensure role is a valid choice."""
        valid_roles = [choice[0] for choice in User.Role.choices]
        if value not in valid_roles:
            raise serializers.ValidationError(
                f'Invalid role. Must be one of: {", ".join(valid_roles)}'
            )
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that includes user info in the response.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Add custom claims as top-level fields
        data['role'] = self.user.role
        data['username'] = self.user.username
        return data
