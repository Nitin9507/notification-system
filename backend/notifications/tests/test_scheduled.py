from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from notifications.models import (
    Channel,
    DeliveryStatus,
    NotificationLog,
    NotificationTemplate,
    Trigger,
    TriggerKind,
)
from notifications.services.scheduled import run_scheduled_triggers, users_inactive_for

User = get_user_model()


class ScheduledTriggerTests(TestCase):
    def setUp(self):
        self.trigger = Trigger.objects.create(
            code="user.inactive_1d",
            name="Not logged in 1 day",
            kind=TriggerKind.SCHEDULED,
            inactivity_days=1,
        )
        NotificationTemplate.objects.create(
            trigger=self.trigger,
            channel=Channel.EMAIL,
            subject="We miss you",
            body="Come back!",
        )
        self.away = User.objects.create_user(
            username="away", email="away@example.com", last_login=timezone.now() - timedelta(days=3)
        )
        self.active = User.objects.create_user(
            username="active", email="active@example.com", last_login=timezone.now()
        )

    def test_only_inactive_users_match(self):
        usernames = set(users_inactive_for(1).values_list("username", flat=True))
        self.assertIn("away", usernames)
        self.assertNotIn("active", usernames)

    def test_never_logged_in_users_count_as_inactive(self):
        User.objects.create_user(username="ghost", email="ghost@example.com")
        User.objects.filter(username="ghost").update(
            date_joined=timezone.now() - timedelta(days=5)
        )
        self.assertIn("ghost", set(users_inactive_for(1).values_list("username", flat=True)))

    def test_dry_run_sends_nothing(self):
        summary = run_scheduled_triggers(dry_run=True)

        self.assertEqual(summary["results"][0]["matched"], 1)
        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_second_run_does_not_notify_twice(self):
        with patch("notifications.dispatcher.get_adapter") as get_adapter:
            get_adapter.return_value = _AlwaysSends()
            first = run_scheduled_triggers()
            second = run_scheduled_triggers()

        self.assertEqual(first["results"][0]["notified"], 1)
        self.assertEqual(second["results"][0]["notified"], 0)
        self.assertEqual(second["results"][0]["skipped_recently_notified"], 1)


class _AlwaysSends:
    provider = "fake"

    def resolve_recipient(self, user):
        return user.email

    def build_message(self, template, ctx, recipient):
        from notifications.channels.base import Message

        return Message(recipient=recipient, subject=template.subject, body=template.body)

    def send(self, message):
        from notifications.channels.base import SendResult

        return SendResult(status=DeliveryStatus.SENT, provider="fake")
