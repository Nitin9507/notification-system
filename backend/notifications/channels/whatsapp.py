"""
WhatsApp Cloud API (Meta sandbox).

The one rule that shapes this adapter: Meta only accepts free-form text within
24 hours of the user's last inbound message. Outside that window the send must
use a pre-approved template. We therefore store both on the cell and pick at
send time, rather than storing text and hoping the window is open.
"""

import requests
from django.conf import settings

from notifications.channels.base import ChannelAdapter, Message, SendResult
from notifications.models import Channel
from notifications.renderer import render_text


class WhatsAppAdapter(ChannelAdapter):
    channel = Channel.WHATSAPP
    provider = "whatsapp_cloud_api"

    def is_configured(self) -> bool:
        return bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)

    def resolve_recipient(self, user) -> str:
        profile = getattr(user, "profile", None)
        return (profile.phone_e164 or "").strip() if profile else ""

    def build_message(self, template, ctx, recipient: str) -> Message:
        user = ctx.get("user")
        profile = getattr(user, "profile", None)
        session_open = bool(profile and profile.whatsapp_session_open)

        body = render_text(template.body, ctx)

        if session_open or not template.wa_template_name:
            return Message(recipient=recipient, body=body, extra={"mode": "text"})

        params = [render_text(str(p), ctx) for p in (template.wa_body_params or [])]
        return Message(
            recipient=recipient,
            body=body,
            extra={
                "mode": "template",
                "template_name": template.wa_template_name,
                "language_code": template.wa_language_code or "en_US",
                "params": params,
            },
        )

    def _payload(self, message: Message) -> dict:
        if message.extra.get("mode") == "template":
            components = []
            if message.extra.get("params"):
                components.append(
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": p}
                            for p in message.extra["params"]
                        ],
                    }
                )
            return {
                "messaging_product": "whatsapp",
                "to": message.recipient,
                "type": "template",
                "template": {
                    "name": message.extra["template_name"],
                    "language": {"code": message.extra["language_code"]},
                    "components": components,
                },
            }
        return {
            "messaging_product": "whatsapp",
            "to": message.recipient,
            "type": "text",
            "text": {"preview_url": False, "body": message.body},
        }

    def deliver(self, message: Message) -> SendResult:
        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
            f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
        response = requests.post(
            url,
            json=self._payload(message),
            headers={
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=settings.PROVIDER_TIMEOUT_SECONDS,
        )
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text[:500]}

        if response.ok:
            message_id = ""
            messages = data.get("messages") or []
            if messages:
                message_id = messages[0].get("id", "")
            return SendResult.sent(self.provider, message_id, data)

        error = data.get("error", {}) if isinstance(data, dict) else {}
        detail = error.get("message") or f"HTTP {response.status_code}"
        if error.get("code") == 190:
            detail += " (access token expired — regenerate it in Meta API Setup)"
        elif error.get("code") == 131047:
            detail += " (24h session closed — an approved template is required)"
        return SendResult.failed(self.provider, detail, data)
