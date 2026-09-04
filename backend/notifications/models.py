"""
Data model for the trigger x channel notification matrix.

    Trigger              one row  in the admin table  (an event or a condition)
    NotificationTemplate one cell in the admin table  (message + on/off toggle)
    NotificationLog      one delivery attempt         (audit trail)

The unique constraint on (trigger, channel) is what makes the admin screen a
true matrix: a trigger has at most one template per channel.
"""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Channel(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"
    WEB_PUSH = "web_push", "Web Push"


class TriggerKind(models.TextChoices):
    EVENT = "event", "Event"
    SCHEDULED = "scheduled", "Scheduled"


class Trigger(models.Model):
    """One row of the admin table."""

    code = models.CharField(
        max_length=64,
        unique=True,
        validators=[
            RegexValidator(
                r"^[a-zA-Z0-9._-]+$",
                "Use letters, numbers, dots, underscores or hyphens only.",
            )
        ],
        help_text="Stable identifier used in code, e.g. 'user.login'.",
    )
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    kind = models.CharField(
        max_length=16, choices=TriggerKind.choices, default=TriggerKind.EVENT
    )
    inactivity_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Scheduled triggers only: fire for users inactive this many days.",
    )
    is_active = models.BooleanField(
        default=True, help_text="Master switch for the whole row."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    @property
    def is_scheduled(self) -> bool:
        return self.kind == TriggerKind.SCHEDULED


class NotificationTemplate(models.Model):
    """One cell of the admin table: the message for a trigger on a channel."""

    trigger = models.ForeignKey(
        Trigger, on_delete=models.CASCADE, related_name="templates"
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)

    subject = models.CharField(
        max_length=255,
        blank=True,
        help_text="Email subject / web push title. Unused for WhatsApp.",
    )
    body = models.TextField(
        help_text="Message body. Supports {{ placeholders }} from the variable map."
    )

    wa_template_name = models.CharField(
        max_length=128,
        blank=True,
        help_text="Approved WhatsApp template used outside the 24h session window.",
    )
    wa_language_code = models.CharField(max_length=16, default="en_US", blank=True)
    wa_body_params = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered {{1}}, {{2}}... values for the approved template. "
        "Each entry may itself contain {{ placeholders }}.",
    )

    variables = models.JSONField(
        default=dict,
        blank=True,
        help_text="Maps a placeholder to a dotted path in the trigger context, "
        'e.g. {"first_name": "user.first_name"}.',
    )

    is_enabled = models.BooleanField(
        default=True, help_text="The per-cell on/off toggle."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["trigger_id", "channel"]
        constraints = [
            models.UniqueConstraint(
                fields=["trigger", "channel"], name="unique_template_per_trigger_channel"
            )
        ]

    def __str__(self) -> str:
        return f"{self.trigger.code} / {self.channel}"

    @property
    def is_live(self) -> bool:
        """True when both the row switch and the cell toggle are on."""
        return self.is_enabled and self.trigger.is_active


class DeliveryStatus(models.TextChoices):
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"
    DRY_RUN = "dry_run", "Dry run"


class NotificationLog(models.Model):
    """One delivery attempt. Never deleted when a template changes."""

    trigger = models.ForeignKey(
        Trigger, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs"
    )
    trigger_code = models.CharField(max_length=64, blank=True)
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
    )

    recipient = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)

    status = models.CharField(max_length=16, choices=DeliveryStatus.choices)
    provider = models.CharField(max_length=32, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error = models.TextField(blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    is_test = models.BooleanField(
        default=False, help_text="True for admin 'Test send', excluded from dedupe."
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "trigger", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.trigger_code} / {self.channel} -> {self.recipient} [{self.status}]"
