"""
Browser web push via OneSignal. Web only — no Android, no iOS.

Two OneSignal-specific wrinkles are handled here so they don't bite during a
demo: apps created today target ``include_subscription_ids`` (the old
``include_player_ids`` returns "no subscribers"), and newer REST keys need an
``Authorization: Key ...`` header instead of the legacy ``Basic ...``. We send
the modern form and retry once on an auth rejection.
"""

import requests
from django.conf import settings

from notifications.channels.base import ChannelAdapter, Message, SendResult
from notifications.models import Channel
from notifications.renderer import render_text

API_URL = "https://onesignal.com/api/v1/notifications"


class WebPushAdapter(ChannelAdapter):
    channel = Channel.WEB_PUSH
    provider = "onesignal"

    def is_configured(self) -> bool:
        return bool(settings.ONESIGNAL_APP_ID and settings.ONESIGNAL_REST_API_KEY)

    def resolve_recipient(self, user) -> str:
        profile = getattr(user, "profile", None)
        return (profile.onesignal_player_id or "").strip() if profile else ""

    def build_message(self, template, ctx, recipient: str) -> Message:
        return Message(
            recipient=recipient,
            subject=render_text(template.subject, ctx) or "Notification",
            body=render_text(template.body, ctx),
        )

    def deliver(self, message: Message) -> SendResult:
        payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            settings.ONESIGNAL_TARGET_FIELD: [message.recipient],
            "headings": {"en": message.subject},
            "contents": {"en": message.body},
            "url": settings.FRONTEND_URL,
            "isAnyWeb": True,
            "isAndroid": False,
            "isIos": False,
        }

        response = self._post(payload, scheme="Key")
        if response.status_code in (401, 403):
            response = self._post(payload, scheme="Basic")

        data = _json_or_text(response)
        errors = data.get("errors")
        if response.ok and not errors:
            return SendResult.sent(self.provider, data.get("id", ""), data)

        detail = _first_error(errors) or f"HTTP {response.status_code}"
        if "no subscribers" in detail.lower():
            detail += (
                " (subscription id not recognised — re-subscribe in the browser, "
                "or switch ONESIGNAL_TARGET_FIELD)"
            )
        return SendResult.failed(self.provider, detail, data)

    def _post(self, payload: dict, scheme: str):
        return requests.post(
            API_URL,
            json=payload,
            headers={
                "Authorization": f"{scheme} {settings.ONESIGNAL_REST_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=settings.PROVIDER_TIMEOUT_SECONDS,
        )


def _first_error(errors) -> str:
    if not errors:
        return ""
    if isinstance(errors, dict):
        errors = errors.get("invalid_player_ids") or list(errors.values())
    if isinstance(errors, list) and errors:
        return str(errors[0])
    return str(errors)


def _json_or_text(response) -> dict:
    try:
        data = response.json()
    except ValueError:
        return {"raw": response.text[:500]}
    return data if isinstance(data, dict) else {"data": data}
