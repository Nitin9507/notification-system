from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from notifications.channels.base import ChannelAdapter, Message, SendResult
from notifications.dispatcher import already_notified, notify, send_test
from notifications.models import (
    Channel,
    DeliveryStatus,
    NotificationLog,
    NotificationTemplate,
    Trigger,
)

User = get_user_model()


class RecordingAdapter(ChannelAdapter):
    """Stands in for a real provider so tests never touch the network."""

    channel = Channel.EMAIL
    provider = "fake"

    def __init__(self):
        self.sent: list[Message] = []

    def is_configured(self):
        return True

    def resolve_recipient(self, user):
        return user.email

    def build_message(self, template, ctx, recipient):
        from notifications.renderer import render_text

        return Message(
            recipient=recipient,
            subject=render_text(template.subject, ctx),
            body=render_text(template.body, ctx),
        )

    def deliver(self, message):
        self.sent.append(message)
        return SendResult.sent(self.provider, "fake-id-1")


class DispatcherTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="nitin", email="nitin@example.com", first_name="Nitin"
        )
        self.trigger = Trigger.objects.create(code="user.login", name="Login")
        self.template = NotificationTemplate.objects.create(
            trigger=self.trigger,
            channel=Channel.EMAIL,
            subject="Hello {{ name }}",
            body="Welcome back, {{ name }}.",
            variables={"name": "user.first_name"},
        )
        self.adapter = RecordingAdapter()
        self.patcher = patch.dict(
            "notifications.channels.ADAPTERS", {Channel.EMAIL: self.adapter}
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_sends_and_renders_variables(self):
        logs = notify("user.login", user=self.user)

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].status, DeliveryStatus.SENT)
        self.assertEqual(self.adapter.sent[0].body, "Welcome back, Nitin.")
        self.assertEqual(self.adapter.sent[0].recipient, "nitin@example.com")

    def test_disabled_cell_is_skipped_but_still_logged(self):
        self.template.is_enabled = False
        self.template.save()

        logs = notify("user.login", user=self.user)

        self.assertEqual(logs[0].status, DeliveryStatus.SKIPPED)
        self.assertIn("toggle", logs[0].error)
        self.assertEqual(self.adapter.sent, [])

    def test_inactive_trigger_blocks_every_channel(self):
        self.trigger.is_active = False
        self.trigger.save()

        logs = notify("user.login", user=self.user)

        self.assertEqual(logs[0].status, DeliveryStatus.SKIPPED)
        self.assertIn("switched off", logs[0].error)

    def test_missing_recipient_is_skipped_not_an_error(self):
        self.user.email = ""
        self.user.save()

        logs = notify("user.login", user=self.user)

        self.assertEqual(logs[0].status, DeliveryStatus.SKIPPED)

    def test_unknown_trigger_is_a_no_op(self):
        self.assertEqual(notify("does.not.exist", user=self.user), [])

    def test_test_send_ignores_the_toggle(self):
        self.template.is_enabled = False
        self.template.save()

        log = send_test(self.template, user=self.user)

        self.assertEqual(log.status, DeliveryStatus.SENT)
        self.assertTrue(log.is_test)

    def test_provider_exception_is_recorded_not_raised(self):
        with patch.object(
            self.adapter, "deliver", side_effect=RuntimeError("provider down")
        ):
            logs = notify("user.login", user=self.user)

        self.assertEqual(logs[0].status, DeliveryStatus.FAILED)
        self.assertIn("provider down", logs[0].error)

    def test_dedupe_ignores_test_sends(self):
        send_test(self.template, user=self.user)
        self.assertFalse(
            already_notified(self.user, self.trigger, within=timedelta(days=1))
        )

        notify("user.login", user=self.user)
        self.assertTrue(
            already_notified(self.user, self.trigger, within=timedelta(days=1))
        )

    def test_dedupe_window_expires(self):
        notify("user.login", user=self.user)
        NotificationLog.objects.update(created_at=timezone.now() - timedelta(days=3))

        self.assertFalse(
            already_notified(self.user, self.trigger, within=timedelta(days=1))
        )
