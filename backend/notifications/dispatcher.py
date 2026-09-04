"""
The dispatcher: the one place that turns "something happened" into messages.

It knows about triggers, templates and toggles. It does *not* know that
WhatsApp, Brevo or OneSignal exist — every send goes through a ChannelAdapter.
That is the seam that makes a fourth channel a one-file change.

    notify("user.login", user=request.user, context={"ip": ...})
"""

import logging
from datetime import timedelta
from typing import Any, Iterable, Mapping

from django.utils import timezone

from notifications.channels import get_adapter
from notifications.models import (
    DeliveryStatus,
    NotificationLog,
    NotificationTemplate,
    Trigger,
)
from notifications.renderer import build_context

logger = logging.getLogger(__name__)


def notify(
    trigger_code: str,
    user=None,
    context: Mapping[str, Any] | None = None,
    channels: Iterable[str] | None = None,
) -> list[NotificationLog]:
    """
    Fire a trigger for one user.

    Returns one log row per channel that was considered — including the ones
    that were skipped, so the admin can always answer "why didn't I get it?".
    Never raises: a notification failure must not break the action that caused
    it (a user's login should succeed even if WhatsApp is down).
    """
    try:
        trigger = Trigger.objects.get(code=trigger_code)
    except Trigger.DoesNotExist:
        logger.warning("notify() called with unknown trigger '%s'", trigger_code)
        return []

    templates = trigger.templates.select_related("trigger")
    if channels:
        templates = templates.filter(channel__in=list(channels))

    base_ctx = _base_context(trigger, user, context)
    logs: list[NotificationLog] = []

    for template in templates:
        if not trigger.is_active:
            logs.append(_skip(template, user, "trigger is switched off"))
            continue
        if not template.is_enabled:
            logs.append(_skip(template, user, "channel toggle is off"))
            continue
        logs.append(_send_one(template, user, base_ctx))

    return logs


def send_test(
    template: NotificationTemplate, user=None, recipient: str = ""
) -> NotificationLog:
    """
    Admin "Test send": deliver this one cell now, ignoring both toggles.

    Toggles are deliberately bypassed — the whole point of a test send is to
    check a message before switching the cell on.
    """
    base_ctx = _base_context(template.trigger, user, {"is_test": True})
    return _send_one(template, user, base_ctx, is_test=True, recipient_override=recipient)


def already_notified(user, trigger: Trigger, within: timedelta) -> bool:
    """
    Dedupe guard for scheduled triggers.

    Without this, a user who has been away for three days receives the
    "inactive for 1 day" message on each nightly run.
    """
    return (
        NotificationLog.objects.filter(
            user=user,
            trigger=trigger,
            is_test=False,
            status__in=[DeliveryStatus.SENT, DeliveryStatus.DRY_RUN],
            created_at__gte=timezone.now() - within,
        )
        .only("id")
        .exists()
    )


def _base_context(trigger, user, context: Mapping[str, Any] | None) -> dict:
    ctx: dict[str, Any] = {
        "user": user,
        "trigger": trigger,
        "now": timezone.now(),
        "site_name": "Notification System",
    }
    if user is not None:
        ctx["first_name"] = getattr(user, "first_name", "") or getattr(
            user, "username", ""
        )
        ctx["username"] = getattr(user, "username", "")
        ctx["email"] = getattr(user, "email", "")
    ctx.update(dict(context or {}))
    return ctx


def _send_one(
    template: NotificationTemplate,
    user,
    base_ctx: Mapping[str, Any],
    is_test: bool = False,
    recipient_override: str = "",
) -> NotificationLog:
    adapter = get_adapter(template.channel)
    recipient = recipient_override or (adapter.resolve_recipient(user) if user else "")

    ctx = build_context(template.variables, base_ctx)
    message = adapter.build_message(template, ctx, recipient)
    message.recipient = recipient
    result = adapter.send(message)

    if not result.ok:
        logger.warning(
            "notification %s/%s -> %s failed: %s",
            template.trigger.code,
            template.channel,
            recipient or "(no recipient)",
            result.error,
        )

    return NotificationLog.objects.create(
        trigger=template.trigger,
        trigger_code=template.trigger.code,
        template=template,
        channel=template.channel,
        user=user if getattr(user, "pk", None) else None,
        recipient=recipient,
        subject=message.subject,
        body=message.body,
        status=result.status,
        provider=result.provider,
        provider_message_id=result.provider_message_id or "",
        error=result.error or "",
        provider_response=result.response or {},
        is_test=is_test,
    )


def _skip(template: NotificationTemplate, user, reason: str) -> NotificationLog:
    return NotificationLog.objects.create(
        trigger=template.trigger,
        trigger_code=template.trigger.code,
        template=template,
        channel=template.channel,
        user=user if getattr(user, "pk", None) else None,
        status=DeliveryStatus.SKIPPED,
        error=reason,
    )
