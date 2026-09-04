"""User profile carrying the per-channel delivery addresses."""

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserProfile(models.Model):
    """
    Where to reach a user on each of the three channels.

    A channel is silently skipped (and logged as SKIPPED) when its address is
    missing, so a user without a phone number simply gets email + web push.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    phone_e164 = models.CharField(
        max_length=20,
        blank=True,
        help_text="WhatsApp destination in E.164 without '+', e.g. 918559050811.",
    )
    onesignal_player_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Web push subscription id returned by the OneSignal browser SDK.",
    )
    last_whatsapp_inbound_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user last messaged our WhatsApp number. Free-form text "
        "is only permitted for 24h after this.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile<{self.user.username}>"

    @property
    def whatsapp_session_open(self) -> bool:
        """True while Meta still allows free-form (non-template) WhatsApp text."""
        if not self.last_whatsapp_inbound_at:
            return False
        window = timezone.timedelta(hours=settings.WHATSAPP_SESSION_WINDOW_HOURS)
        return timezone.now() - self.last_whatsapp_inbound_at < window


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    """Every user has exactly one profile, including superusers made via CLI."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
