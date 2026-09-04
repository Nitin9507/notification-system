from rest_framework import serializers

from .models import (
    Channel,
    NotificationLog,
    NotificationTemplate,
    Trigger,
    TriggerKind,
)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    body = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = NotificationTemplate
        fields = (
            "id",
            "trigger",
            "channel",
            "subject",
            "body",
            "wa_template_name",
            "wa_language_code",
            "wa_body_params",
            "variables",
            "is_enabled",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "trigger", "channel", "created_at", "updated_at")

    def validate_variables(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("variables must be an object.")
        for key, path in value.items():
            if not isinstance(path, str):
                raise serializers.ValidationError(
                    f"variables['{key}'] must be a dotted path string."
                )
        return value

    def validate_wa_body_params(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("wa_body_params must be a list.")
        return value

    def validate(self, attrs):
        """
        A cell must carry something sendable.

        The channel comes from the URL, never the request body, so the view
        passes it through the serializer context.
        """
        channel = self.instance.channel if self.instance else self.context.get("channel")
        body = attrs.get("body", getattr(self.instance, "body", ""))
        wa_name = attrs.get(
            "wa_template_name", getattr(self.instance, "wa_template_name", "")
        )
        if channel == Channel.WHATSAPP:
            if not (body or wa_name):
                raise serializers.ValidationError(
                    "Provide a message, an approved WhatsApp template name, or both."
                )
        elif not body:
            raise serializers.ValidationError({"body": "This field is required."})
        return attrs


class TriggerSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        """A scheduled trigger without a window would silently never fire."""
        kind = attrs.get("kind", getattr(self.instance, "kind", TriggerKind.EVENT))
        days = attrs.get(
            "inactivity_days", getattr(self.instance, "inactivity_days", None)
        )
        if kind == TriggerKind.SCHEDULED and not days:
            raise serializers.ValidationError(
                {"inactivity_days": "Scheduled triggers need a number of days."}
            )
        if kind == TriggerKind.EVENT and days:
            attrs["inactivity_days"] = None
        return attrs

    class Meta:
        model = Trigger
        fields = (
            "id",
            "code",
            "name",
            "description",
            "kind",
            "inactivity_days",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class MatrixRowSerializer(serializers.ModelSerializer):
    """One admin table row: the trigger plus its cell per channel."""

    templates = serializers.SerializerMethodField()

    class Meta:
        model = Trigger
        fields = (
            "id",
            "code",
            "name",
            "description",
            "kind",
            "inactivity_days",
            "is_active",
            "templates",
        )

    def get_templates(self, trigger) -> dict:
        by_channel = {t.channel: t for t in trigger.templates.all()}
        return {
            channel: (
                NotificationTemplateSerializer(by_channel[channel]).data
                if channel in by_channel
                else None
            )
            for channel, _label in Channel.choices
        }


class NotificationLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", default="", read_only=True)

    class Meta:
        model = NotificationLog
        fields = (
            "id",
            "created_at",
            "trigger_code",
            "channel",
            "username",
            "recipient",
            "subject",
            "body",
            "status",
            "provider",
            "provider_message_id",
            "error",
            "is_test",
        )


class TestSendSerializer(serializers.Serializer):
    """Optional override so an admin can test against any address."""

    recipient = serializers.CharField(required=False, allow_blank=True)
