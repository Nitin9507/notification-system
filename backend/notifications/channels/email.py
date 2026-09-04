"""
Transactional email.

Two vendors behind one adapter, selected by ``EMAIL_PROVIDER``. Brevo is the
default: 300 emails/day free versus Postmark's ~100/month, which matters when
you are re-testing templates. The integration shape (verified sender + API key)
is identical, so switching is a .env change.
"""

import requests
from django.conf import settings

from notifications.channels.base import ChannelAdapter, Message, SendResult
from notifications.models import Channel
from notifications.renderer import render_text


class EmailAdapter(ChannelAdapter):
    channel = Channel.EMAIL

    @property
    def provider(self) -> str:
        return settings.EMAIL_PROVIDER or "brevo"

    def _api_key(self) -> str:
        if self.provider == "postmark":
            return settings.POSTMARK_TOKEN
        return settings.BREVO_API_KEY

    def is_configured(self) -> bool:
        return bool(self._api_key() and settings.DEFAULT_FROM_EMAIL)

    def resolve_recipient(self, user) -> str:
        return (getattr(user, "email", "") or "").strip()

    def build_message(self, template, ctx, recipient: str) -> Message:
        return Message(
            recipient=recipient,
            subject=render_text(template.subject, ctx) or "Notification",
            body=render_text(template.body, ctx),
        )

    def deliver(self, message: Message) -> SendResult:
        if self.provider == "postmark":
            return self._deliver_postmark(message)
        return self._deliver_brevo(message)

    def _deliver_brevo(self, message: Message) -> SendResult:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json={
                "sender": {
                    "email": settings.DEFAULT_FROM_EMAIL,
                    "name": settings.DEFAULT_FROM_NAME,
                },
                "to": [{"email": message.recipient}],
                "subject": message.subject,
                "textContent": message.body,
                "htmlContent": _as_html(message.body),
            },
            headers={
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
                "accept": "application/json",
            },
            timeout=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        data = _json_or_text(response)
        if response.ok:
            return SendResult.sent(self.provider, data.get("messageId", ""), data)
        return SendResult.failed(
            self.provider,
            data.get("message") or f"HTTP {response.status_code}",
            data,
        )

    def _deliver_postmark(self, message: Message) -> SendResult:
        response = requests.post(
            "https://api.postmarkapp.com/email",
            json={
                "From": settings.DEFAULT_FROM_EMAIL,
                "To": message.recipient,
                "Subject": message.subject,
                "TextBody": message.body,
                "HtmlBody": _as_html(message.body),
                "MessageStream": "outbound",
            },
            headers={
                "X-Postmark-Server-Token": settings.POSTMARK_TOKEN,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        data = _json_or_text(response)
        if response.ok:
            return SendResult.sent(self.provider, data.get("MessageID", ""), data)
        return SendResult.failed(
            self.provider,
            data.get("Message") or f"HTTP {response.status_code}",
            data,
        )


def _as_html(text: str) -> str:
    from django.utils.html import escape

    return "<p>" + escape(text).replace("\n", "<br>") + "</p>"


def _json_or_text(response) -> dict:
    try:
        data = response.json()
    except ValueError:
        return {"raw": response.text[:500]}
    return data if isinstance(data, dict) else {"data": data}
