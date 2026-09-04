"""
Where website events become notification triggers.

Event triggers hook Django's auth signals, so anything that logs a user in —
the API, the Django admin, a future SSO flow — fires the notification without
each call site remembering to. Condition triggers ("not logged in for a week")
have nothing to hook and are handled by ``run_scheduled_triggers`` instead.
"""

import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from notifications.dispatcher import notify

logger = logging.getLogger(__name__)

TRIGGER_LOGIN = "user.login"
TRIGGER_LOGOUT = "user.logout"
TRIGGER_INACTIVE_1D = "user.inactive_1d"
TRIGGER_INACTIVE_1W = "user.inactive_1w"


def _safe_notify(code: str, user, context=None) -> None:
    """A broken notification must never break the action that triggered it."""
    try:
        notify(code, user=user, context=context or {})
    except Exception:  # noqa: BLE001
        logger.exception("dispatching trigger '%s' failed", code)


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    _safe_notify(TRIGGER_LOGIN, user, {"ip": _client_ip(request)})


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user is None:
        return
    _safe_notify(TRIGGER_LOGOUT, user, {"ip": _client_ip(request)})


def _client_ip(request) -> str:
    if request is None:
        return ""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
