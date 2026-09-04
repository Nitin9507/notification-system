"""
Condition triggers — "not logged in for 1 day / 1 week".

These are the awkward ones: nothing *happens* when a user fails to log in, so
there is no signal to hook. Instead a scheduler calls in periodically and we
scan for users matching each active scheduled trigger's inactivity window.

Idempotency matters more than it looks. A user away for three days matches the
1-day trigger on every run, so without a dedupe check they receive the same
"we miss you" message every night.
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from notifications.dispatcher import already_notified, notify
from notifications.models import Trigger, TriggerKind

logger = logging.getLogger(__name__)


def users_inactive_for(days: int):
    """Active users whose last login is older than ``days`` (never-logged-in counts)."""
    cutoff = timezone.now() - timedelta(days=days)
    User = get_user_model()
    return User.objects.filter(is_active=True).filter(
        Q(last_login__lt=cutoff) | Q(last_login__isnull=True, date_joined__lt=cutoff)
    )


def run_scheduled_triggers(dry_run: bool = False) -> dict:
    """
    Evaluate every active scheduled trigger. Safe to run as often as you like.

    Returns a per-trigger summary so the cron caller (and the walkthrough video)
    can see exactly what happened.
    """
    results = []

    triggers = Trigger.objects.filter(
        kind=TriggerKind.SCHEDULED, is_active=True, inactivity_days__isnull=False
    )
    for trigger in triggers:
        window = timedelta(days=trigger.inactivity_days)
        candidates = users_inactive_for(trigger.inactivity_days)

        matched = notified = deduped = 0
        for user in candidates.select_related("profile").iterator():
            matched += 1
            if already_notified(user, trigger, within=window):
                deduped += 1
                continue
            if dry_run:
                continue
            logs = notify(trigger.code, user=user)
            if logs:
                notified += 1

        logger.info(
            "scheduled trigger %s: matched=%s notified=%s deduped=%s",
            trigger.code,
            matched,
            notified,
            deduped,
        )
        results.append(
            {
                "trigger": trigger.code,
                "inactivity_days": trigger.inactivity_days,
                "matched": matched,
                "notified": notified,
                "skipped_recently_notified": deduped,
            }
        )

    return {"ran_at": timezone.now().isoformat(), "dry_run": dry_run, "results": results}
