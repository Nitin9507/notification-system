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
from notifications.models import Channel, DeliveryStatus
from notifications.renderer import render_text

RE_ENGAGEMENT_ERRORS = {131047, 131051, 470}


class WhatsAppAdapter(ChannelAdapter):
    channel = Channel.WHATSAPP
    provider = "whatsapp_cloud_api"

    def is_configured(self) -> bool:
        return bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)

    def resolve_recipient(self, user) -> str:
        profile = getattr(user, "profile", None)
        return (profile.phone_e164 or "").strip() if profile else ""

    def build_message(self, template, ctx, recipient: str) -> Message:
        """
        Carry both forms of the message.

        Free-form text is what the admin actually wrote, so it is always
        preferred. The approved template rides along as a fallback for when
        Meta refuses free text because the 24-hour window has closed.
        """
        body = render_text(template.body, ctx)

        fallback = None
        if template.wa_template_name:
            fallback = {
                "template_name": template.wa_template_name,
                "language_code": template.wa_language_code or "en_US",
                "params": [
                    render_text(str(value), ctx)
                    for value in (template.wa_body_params or [])
                ],
            }

        return Message(
            recipient=recipient,
            body=body,
            extra={"mode": "text" if body else "template", "fallback": fallback},
        )

    def _text_payload(self, message: Message) -> dict:
        return {
            "messaging_product": "whatsapp",
            "to": message.recipient,
            "type": "text",
            "text": {"preview_url": False, "body": message.body},
        }

    def _template_payload(self, message: Message, fallback: dict) -> dict:
        components = []
        if fallback.get("params"):
            components.append(
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": value}
                        for value in fallback["params"]
                    ],
                }
            )
        return {
            "messaging_product": "whatsapp",
            "to": message.recipient,
            "type": "template",
            "template": {
                "name": fallback["template_name"],
                "language": {"code": fallback["language_code"]},
                "components": components,
            },
        }

    def deliver(self, message: Message) -> SendResult:
        fallback = message.extra.get("fallback")

        if message.extra.get("mode") == "template":
            if not fallback:
                return SendResult.failed(
                    self.provider, "No message text and no approved template to send."
                )
            return self._post(self._template_payload(message, fallback))

        result = self._post(self._text_payload(message))

        # Meta refuses free-form text outside the 24-hour window. Rather than
        # tracking that window ourselves, we let Meta tell us and retry with the
        # approved template — so the admin's own wording is used whenever it can be.
        if result.status == DeliveryStatus.FAILED and fallback:
            code = (result.response.get("error") or {}).get("code")
            if code in RE_ENGAGEMENT_ERRORS:
                retried = self._post(self._template_payload(message, fallback))
                if retried.ok:
                    return retried
        return result

    def _post(self, payload: dict) -> SendResult:
        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
            f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
        response = requests.post(
            url,
            json=payload,
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
            messages = data.get("messages") or []
            return SendResult.sent(
                self.provider, messages[0].get("id", "") if messages else "", data
            )

        error = data.get("error", {}) if isinstance(data, dict) else {}
        detail = error.get("message") or f"HTTP {response.status_code}"
        if error.get("code") == 190:
            detail += " (access token expired — regenerate it in Meta API Setup)"
        elif error.get("code") in RE_ENGAGEMENT_ERRORS:
            detail += " (24h window closed and no approved template is set)"
        return SendResult.failed(self.provider, detail, data)
