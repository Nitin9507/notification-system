from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import UserProfile

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    whatsapp_session_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            "phone_e164",
            "onesignal_player_id",
            "last_whatsapp_inbound_at",
            "whatsapp_session_open",
        )
        read_only_fields = ("last_whatsapp_inbound_at",)


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "last_login",
            "profile",
        )
        read_only_fields = ("id", "is_staff", "last_login")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    phone_e164 = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="WhatsApp number in E.164 without '+', e.g. 918559050811.",
    )

    class Meta:
        model = User
        fields = ("username", "email", "password", "first_name", "last_name", "phone_e164")

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def create(self, validated_data):
        phone = validated_data.pop("phone_e164", "")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if phone:
            profile = user.profile
            profile.phone_e164 = phone
            profile.save(update_fields=["phone_e164", "updated_at"])
        return user


class PushSubscriptionSerializer(serializers.Serializer):
    """The subscription id the OneSignal browser SDK hands back after opt-in."""

    onesignal_player_id = serializers.CharField(max_length=64)
