from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from notifications.models import Channel, NotificationTemplate, Trigger

User = get_user_model()


class AdminMatrixApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="admin-pass-123"
        )
        self.member = User.objects.create_user(
            username="member", email="member@example.com", password="member-pass-123"
        )
        self.trigger = Trigger.objects.create(code="user.login", name="Login")
        self.client.force_login(self.admin)

    def test_matrix_returns_a_cell_per_channel(self):
        response = self.client.get("/api/admin/matrix/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        row = payload["triggers"][0]
        self.assertEqual(set(row["templates"]), set(Channel.values))
        self.assertIsNone(row["templates"][Channel.EMAIL])
        self.assertTrue(all("configured" in c for c in payload["channels"]))

    def test_non_staff_cannot_reach_the_admin_api(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get("/api/admin/matrix/").status_code, 403)

    def test_put_upserts_a_cell(self):
        url = f"/api/admin/triggers/{self.trigger.id}/templates/{Channel.EMAIL}/"

        created = self.client.put(
            url,
            data={"subject": "Hi", "body": "Welcome {{ name }}", "variables": {"name": "user.first_name"}},
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)

        updated = self.client.put(
            url, data={"body": "Changed"}, content_type="application/json"
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(NotificationTemplate.objects.count(), 1)
        self.assertEqual(NotificationTemplate.objects.get().body, "Changed")

    def test_rejects_an_unknown_channel(self):
        response = self.client.put(
            f"/api/admin/triggers/{self.trigger.id}/templates/telegram/",
            data={"body": "x"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_toggle_flips_the_cell(self):
        template = NotificationTemplate.objects.create(
            trigger=self.trigger, channel=Channel.EMAIL, subject="s", body="b"
        )
        response = self.client.patch(
            f"/api/admin/triggers/{self.trigger.id}/templates/{Channel.EMAIL}/toggle/",
            data={"is_enabled": False},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        template.refresh_from_db()
        self.assertFalse(template.is_enabled)

    @override_settings(
        BREVO_API_KEY="",
        POSTMARK_TOKEN="",
        WHATSAPP_ACCESS_TOKEN="",
        ONESIGNAL_REST_API_KEY="",
    )
    def test_test_send_dry_runs_without_credentials(self):
        NotificationTemplate.objects.create(
            trigger=self.trigger, channel=Channel.EMAIL, subject="s", body="b"
        )
        response = self.client.post(
            f"/api/admin/triggers/{self.trigger.id}/templates/{Channel.EMAIL}/test-send/",
            data={"recipient": "someone@example.com"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "dry_run")


class AuthTriggerTests(TestCase):
    def setUp(self):
        self.trigger = Trigger.objects.create(code="user.login", name="Login")
        NotificationTemplate.objects.create(
            trigger=self.trigger, channel=Channel.EMAIL, subject="Hi", body="Welcome"
        )
        User.objects.create_user(
            username="nitin", email="nitin@example.com", password="a-good-pass-123"
        )

    def test_login_fires_the_login_trigger(self):
        with patch("notifications.triggers.notify") as mock_notify:
            response = self.client.post(
                "/api/auth/login/",
                data={"username": "nitin", "password": "a-good-pass-123"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[0], "user.login")

    def test_login_still_succeeds_when_notification_blows_up(self):
        with patch("notifications.triggers.notify", side_effect=RuntimeError("boom")):
            response = self.client.post(
                "/api/auth/login/",
                data={"username": "nitin", "password": "a-good-pass-123"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)


class InternalCronTests(TestCase):
    def test_wrong_secret_is_rejected(self):
        response = self.client.post(
            "/api/internal/run-scheduled-triggers/", HTTP_X_CRON_SECRET="nope"
        )
        self.assertEqual(response.status_code, 403)

    def test_correct_secret_runs_the_scan(self):
        with self.settings(INTERNAL_CRON_SECRET="s3cret"):
            response = self.client.post(
                "/api/internal/run-scheduled-triggers/", HTTP_X_CRON_SECRET="s3cret"
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())


class EventListTests(TestCase):
    def setUp(self):
        Trigger.objects.create(code="user.login", name="Login")
        Trigger.objects.create(code="user.inactive_1d", name="Away a day", kind="scheduled")
        Trigger.objects.create(code="user.logout", name="Logout", is_active=False)
        self.user = User.objects.create_user(username="member", password="member-pass-123")

    def test_lists_only_active_event_triggers(self):
        self.client.force_login(self.user)

        codes = [row["code"] for row in self.client.get("/api/events/").json()]

        self.assertEqual(codes, ["user.login"])

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/api/events/").status_code, 401)


class ValidationEdgeCaseTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin2", email="a@example.com", password="admin-pass-123"
        )
        self.client.force_login(self.admin)

    def test_dotted_trigger_codes_are_allowed(self):
        response = self.client.post(
            "/api/admin/triggers/",
            data={"code": "order.placed", "name": "Order placed", "kind": "event"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_trigger_code_rejects_spaces_and_slashes(self):
        for bad in ["order placed", "order/placed", "order?placed"]:
            response = self.client.post(
                "/api/admin/triggers/",
                data={"code": bad, "name": "Bad", "kind": "event"},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400, bad)

    def test_scheduled_trigger_requires_a_window(self):
        response = self.client.post(
            "/api/admin/triggers/",
            data={"code": "never.fires", "name": "Never", "kind": "scheduled"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("inactivity_days", response.json())

    def test_event_trigger_clears_a_stray_window(self):
        response = self.client.post(
            "/api/admin/triggers/",
            data={
                "code": "order.paid",
                "name": "Paid",
                "kind": "event",
                "inactivity_days": 5,
            },
            content_type="application/json",
        )
        self.assertIsNone(response.json()["inactivity_days"])

    def test_whatsapp_cell_accepts_an_approved_template_with_no_body(self):
        trigger = Trigger.objects.create(code="user.login", name="Login")
        response = self.client.put(
            f"/api/admin/triggers/{trigger.id}/templates/whatsapp/",
            data={"wa_template_name": "hello_world", "wa_language_code": "en_US"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_whatsapp_cell_rejects_an_entirely_empty_message(self):
        trigger = Trigger.objects.create(code="user.logout", name="Logout")
        response = self.client.put(
            f"/api/admin/triggers/{trigger.id}/templates/whatsapp/",
            data={"body": ""},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_email_cell_still_requires_a_body(self):
        trigger = Trigger.objects.create(code="user.reset", name="Reset")
        response = self.client.put(
            f"/api/admin/triggers/{trigger.id}/templates/email/",
            data={"subject": "Hello"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_a_junk_limit_does_not_crash_the_log(self):
        for value in ["abc", "", "-5", "99999"]:
            response = self.client.get(f"/api/admin/logs/?limit={value}")
            self.assertEqual(response.status_code, 200, value)


class WebhookSecurityTests(TestCase):
    PAYLOAD = {
        "entry": [
            {"changes": [{"value": {"messages": [{"from": "918559050811"}]}}]}
        ]
    }

    @override_settings(WHATSAPP_APP_SECRET="app-secret")
    def test_unsigned_payload_is_rejected(self):
        response = self.client.post(
            "/api/webhooks/whatsapp/",
            data=self.PAYLOAD,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(WHATSAPP_APP_SECRET="app-secret")
    def test_correctly_signed_payload_is_accepted(self):
        import hashlib
        import hmac
        import json

        body = json.dumps(self.PAYLOAD)
        signature = hmac.new(
            b"app-secret", body.encode(), hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            "/api/webhooks/whatsapp/",
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=f"sha256={signature}",
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(WHATSAPP_APP_SECRET="")
    def test_unconfigured_secret_still_accepts_but_is_documented(self):
        response = self.client.post(
            "/api/webhooks/whatsapp/",
            data=self.PAYLOAD,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
