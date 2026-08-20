from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    LoginSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    UserSerializer,
    tokens_for_user,
)


@extend_schema(
    tags=["Auth"],
    summary="Register a staff user",
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(
            response=RegisterResponseSerializer,
            description="User created; access and refresh tokens issued.",
        ),
        400: OpenApiResponse(description="Validation failed (e.g. email already taken)."),
    },
)
class RegisterView(generics.CreateAPIView):
    """Open endpoint -- there has to be a way to create the first account."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserSerializer(user).data, **tokens_for_user(user)},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Auth"],
    summary="Log in and obtain a JWT pair",
    responses={
        200: OpenApiResponse(description="Access token, refresh token and the user."),
        401: OpenApiResponse(description="Invalid credentials."),
    },
)
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


@extend_schema(
    tags=["Auth"],
    summary="Exchange a refresh token for a new access token",
)
class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


@extend_schema(
    tags=["Auth"],
    summary="The currently authenticated user",
    responses={200: UserSerializer, 401: OpenApiResponse(description="Missing or invalid token.")},
)
class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
