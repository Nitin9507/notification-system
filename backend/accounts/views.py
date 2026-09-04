"""
Auth endpoints.

Login and logout do not call ``notify()`` directly — they send Django's
``user_logged_in`` / ``user_logged_out`` signals, and ``notifications.triggers``
listens. So a login through the Django admin fires the same notification as one
through this API, and no future call site has to remember.
"""

from django.contrib.auth.signals import user_logged_in, user_logged_out
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import UserProfile
from .serializers import (
    PushSubscriptionSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """JWT login that also fires the `user.login` trigger."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=False)
            user = getattr(serializer, "user", None)
            if user is not None:
                user_logged_in.send(sender=user.__class__, request=request, user=user)
                response.data["user"] = UserSerializer(user).data
        return response


class LogoutView(APIView):
    """Fires the `user.logout` trigger. The client discards its JWT."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_logged_out.send(
            sender=request.user.__class__, request=request, user=request.user
        )
        return Response({"detail": "Logged out."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()

        profile_data = request.data.get("profile")
        if profile_data:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile_serializer = UserProfileSerializer(
                profile, data=profile_data, partial=True
            )
            profile_serializer.is_valid(raise_exception=True)
            profile_serializer.save()

        return Response(UserSerializer(request.user).data)


class PushSubscriptionView(APIView):
    """Stores the browser's web push subscription id against the user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.onesignal_player_id = serializer.validated_data["onesignal_player_id"]
        profile.save(update_fields=["onesignal_player_id", "updated_at"])
        return Response(UserProfileSerializer(profile).data)
