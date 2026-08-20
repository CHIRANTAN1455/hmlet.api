from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public representation of a user. Never includes the password hash."""

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "is_staff", "created_at"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Minimum 8 characters. Checked against Django's password validators.",
    )

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        # Normalise before the uniqueness check so casing cannot be used to
        # register the same address twice.
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        # Run Django's configured validators (length, commonness, all-numeric)
        # and re-raise as a DRF error so it lands in the standard envelope.
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        # create_user hashes the password; Model.objects.create would store it
        # in plain text.
        return User.objects.create_user(**validated_data)


class RegisterResponseSerializer(serializers.Serializer):
    """Shape of a successful registration: the user plus a ready-to-use token pair.

    Returning tokens here saves the client an immediate second call to /login,
    which is the only thing it could sensibly do next.
    """

    user = UserSerializer(read_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class LoginSerializer(TokenObtainPairSerializer):
    """Standard JWT login, extended to return the user alongside the tokens.

    Without this the client gets two opaque strings and has to decode the JWT
    or call /me to discover who just logged in.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Embedded so downstream services can identify the caller without a
        # database round trip. Non-sensitive fields only.
        token["email"] = user.email
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
