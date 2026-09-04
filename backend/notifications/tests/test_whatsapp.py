from unittest.mock import patch

from django.test import TestCase, override_settings

from notifications.channels.whatsapp import WhatsAppAdapter
from notifications.models import Channel, DeliveryStatus, NotificationTemplate, Trigger


class FakeResponse:
    def __init__(self, ok, payload, status_code=200):
        self.ok = ok
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


ACCEPTED = FakeResponse(True, {"messages": [{"id": "wamid.OK"}]})
WINDOW_CLOSED = FakeResponse(
    False,
    {"error": {"code": 131047, "message": "Re-engagement message"}},
    status_code=400,
)
TOKEN_EXPIRED = FakeResponse(
    False, {"error": {"code": 190, "message": "Authentication Error"}}, status_code=401
)


@override_settings(
    WHATSAPP_ACCESS_TOKEN="token", WHATSAPP_PHONE_NUMBER_ID="123", DEBUG=True
)
class WhatsAppFallbackTests(TestCase):
    def setUp(self):
        self.adapter = WhatsAppAdapter()
        trigger = Trigger.objects.create(code="user.login", name="Login")
        self.template = NotificationTemplate.objects.create(
            trigger=trigger,
            channel=Channel.WHATSAPP,
            body="Welcome back, friend!",
            wa_template_name="hello_world",
            wa_language_code="en_US",
        )

    def _message(self):
        return self.adapter.build_message(self.template, {}, "918559050811")

    def test_free_text_is_tried_first(self):
        with patch("notifications.channels.whatsapp.requests.post") as post:
            post.return_value = ACCEPTED
            result = self.adapter.deliver(self._message())

        self.assertEqual(result.status, DeliveryStatus.SENT)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["json"]["type"], "text")

    def test_closed_window_falls_back_to_the_approved_template(self):
        with patch("notifications.channels.whatsapp.requests.post") as post:
            post.side_effect = [WINDOW_CLOSED, ACCEPTED]
            result = self.adapter.deliver(self._message())

        self.assertEqual(result.status, DeliveryStatus.SENT)
        self.assertEqual(post.call_count, 2)
        second = post.call_args_list[1].kwargs["json"]
        self.assertEqual(second["type"], "template")
        self.assertEqual(second["template"]["name"], "hello_world")

    def test_other_errors_do_not_trigger_a_retry(self):
        with patch("notifications.channels.whatsapp.requests.post") as post:
            post.return_value = TOKEN_EXPIRED
            result = self.adapter.deliver(self._message())

        self.assertEqual(result.status, DeliveryStatus.FAILED)
        self.assertEqual(post.call_count, 1)
        self.assertIn("regenerate", result.error)

    def test_without_a_template_a_closed_window_is_reported_plainly(self):
        self.template.wa_template_name = ""
        self.template.save()

        with patch("notifications.channels.whatsapp.requests.post") as post:
            post.return_value = WINDOW_CLOSED
            result = self.adapter.deliver(self._message())

        self.assertEqual(result.status, DeliveryStatus.FAILED)
        self.assertEqual(post.call_count, 1)
        self.assertIn("24h window closed", result.error)

    def test_template_only_cell_sends_the_template_directly(self):
        self.template.body = ""
        self.template.save()

        with patch("notifications.channels.whatsapp.requests.post") as post:
            post.return_value = ACCEPTED
            result = self.adapter.deliver(self._message())

        self.assertEqual(result.status, DeliveryStatus.SENT)
        self.assertEqual(post.call_args.kwargs["json"]["type"], "template")
