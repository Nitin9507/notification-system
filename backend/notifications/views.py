"""
HTTP surface.

  /api/admin/*      staff-only CRUD over the matrix (the admin panel talks here)
  /api/events/*     authenticated users firing event triggers from the site
  /api/internal/*   the scheduler, authenticated by a shared secret
  /api/webhooks/*   inbound provider callbacks
"""

import hashlib
import hmac
import logging
from hmac import compare_digest

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile

from .channels import get_adapter

from .dispatcher import notify, send_test
from .models import (
    Channel,
    NotificationLog,
    NotificationTemplate,
    Trigger,
    TriggerKind,
)
from .serializers import (
    MatrixRowSerializer,
    NotificationLogSerializer,
    NotificationTemplateSerializer,
    TestSendSerializer,
    TriggerSerializer,
)

logger = logging.getLogger(__name__)


class MatrixView(APIView):
    """
    GET /api/admin/matrix/

    The whole admin screen in one payload: channel columns plus a row per
    trigger with its three cells. The frontend stays a dumb renderer.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        triggers = Trigger.objects.prefetch_related("templates").all()
        return Response(
            {
                "channels": [
                    {
                        "value": value,
                        "label": label,
                        "configured": get_adapter(value).is_configured(),
                    }
                    for value, label in Channel.choices
                ],
                "triggers": MatrixRowSerializer(triggers, many=True).data,
            }
        )


class TriggerViewSet(viewsets.ModelViewSet):
    """Rows of the admin table."""

    queryset = Trigger.objects.prefetch_related("templates").all()
    serializer_class = TriggerSerializer
    permission_classes = [IsAdminUser]
    lookup_field = "pk"

    @action(detail=True, methods=["patch"], url_path="toggle")
    def toggle(self, request, pk=None):
        """Master switch for an entire row."""
        trigger = self.get_object()
        trigger.is_active = bool(request.data.get("is_active", not trigger.is_active))
        trigger.save(update_fields=["is_active", "updated_at"])
        return Response(TriggerSerializer(trigger).data)


class TemplateCellView(APIView):
    """
    One cell of the matrix, addressed the way the admin thinks about it:
    PUT/PATCH/DELETE /api/admin/triggers/<trigger_id>/templates/<channel>/

    PUT upserts, so the frontend does not need to know whether the cell exists.
    """

    permission_classes = [IsAdminUser]

    def _trigger(self, trigger_id) -> Trigger:
        return Trigger.objects.get(pk=trigger_id)

    def _validate_channel(self, channel: str) -> bool:
        return channel in Channel.values

    def get(self, request, trigger_id, channel):
        template = NotificationTemplate.objects.filter(
            trigger_id=trigger_id, channel=channel
        ).first()
        if not template:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(NotificationTemplateSerializer(template).data)

    def put(self, request, trigger_id, channel):
        if not self._validate_channel(channel):
            return Response(
                {"detail": f"Unknown channel '{channel}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            trigger = self._trigger(trigger_id)
        except Trigger.DoesNotExist:
            return Response(
                {"detail": "Trigger not found."}, status=status.HTTP_404_NOT_FOUND
            )

        template = NotificationTemplate.objects.filter(
            trigger=trigger, channel=channel
        ).first()
        serializer = NotificationTemplateSerializer(
            template,
            data=request.data,
            partial=bool(template),
            context={"channel": channel, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        created = template is None
        template = serializer.save(trigger=trigger, channel=channel)
        return Response(
            NotificationTemplateSerializer(template).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def patch(self, request, trigger_id, channel):
        return self.put(request, trigger_id, channel)

    def delete(self, request, trigger_id, channel):
        deleted, _ = NotificationTemplate.objects.filter(
            trigger_id=trigger_id, channel=channel
        ).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TemplateToggleView(APIView):
    """PATCH .../templates/<channel>/toggle/ — the per-cell on/off switch."""

    permission_classes = [IsAdminUser]

    def patch(self, request, trigger_id, channel):
        template = NotificationTemplate.objects.filter(
            trigger_id=trigger_id, channel=channel
        ).first()
        if not template:
            return Response(
                {"detail": "No template in this cell yet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        template.is_enabled = bool(
            request.data.get("is_enabled", not template.is_enabled)
        )
        template.save(update_fields=["is_enabled", "updated_at"])
        return Response(NotificationTemplateSerializer(template).data)


class TemplateTestSendView(APIView):
    """
    POST .../templates/<channel>/test-send/

    Sends this one cell right now, bypassing both toggles, and returns the
    provider's own verdict so the admin sees the real error rather than a
    generic failure.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, trigger_id, channel):
        template = NotificationTemplate.objects.filter(
            trigger_id=trigger_id, channel=channel
        ).first()
        if not template:
            return Response(
                {"detail": "No template in this cell yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TestSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        log = send_test(
            template,
            user=request.user,
            recipient=serializer.validated_data.get("recipient", ""),
        )
        return Response(NotificationLogSerializer(log).data)


class NotificationLogListView(APIView):
    """GET /api/admin/logs/ — the delivery audit trail, newest first."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        logs = NotificationLog.objects.select_related("user").all()
        for field in ("channel", "status", "trigger_code"):
            value = request.query_params.get(field)
            if value:
                logs = logs.filter(**{field: value})
        try:
            limit = int(request.query_params.get("limit", 50))
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 200))
        return Response(NotificationLogSerializer(logs[:limit], many=True).data)


class EventTriggerListView(APIView):
    """
    GET /api/events/

    The event triggers a signed-in user is allowed to fire from the website,
    so the page can offer them by name instead of asking for a code.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        triggers = Trigger.objects.filter(kind=TriggerKind.EVENT, is_active=True)
        return Response(
            [
                {"code": t.code, "name": t.name, "description": t.description}
                for t in triggers
            ]
        )


class FireEventView(APIView):
    """
    POST /api/events/<code>/fire/

    Lets the website fire any event trigger for the signed-in user — the demo
    hook for triggers that aren't login/logout (order placed, and so on).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, code):
        trigger = Trigger.objects.filter(code=code, kind=TriggerKind.EVENT).first()
        if not trigger:
            return Response(
                {"detail": f"No event trigger with code '{code}'."},
                status=status.HTTP_404_NOT_FOUND,
            )
        logs = notify(code, user=request.user, context=request.data.get("context") or {})
        return Response(
            {"trigger": code, "results": NotificationLogSerializer(logs, many=True).data}
        )


class RunScheduledTriggersView(APIView):
    """
    POST /api/internal/run-scheduled-triggers/

    Called by an external scheduler (GitHub Actions cron, cron-job.org) because
    Render's own cron jobs are a paid feature. Guarded by a shared secret in the
    X-Cron-Secret header.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        secret = request.headers.get("X-Cron-Secret", "")
        if not secret or not compare_digest(secret, settings.INTERNAL_CRON_SECRET):
            return Response(
                {"detail": "Invalid cron secret."}, status=status.HTTP_403_FORBIDDEN
            )

        from .services.scheduled import run_scheduled_triggers

        summary = run_scheduled_triggers()
        return Response(summary)


class WhatsAppWebhookView(APIView):
    """
    Meta's webhook. GET verifies the subscription; POST records inbound
    messages, which is what opens the 24h free-form window for that user.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge", "")
        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse("forbidden", status=403)

    def post(self, request):
        if not self._signature_ok(request):
            logger.warning("rejected a WhatsApp webhook with a bad signature")
            return Response(
                {"detail": "Invalid signature."}, status=status.HTTP_403_FORBIDDEN
            )

        for phone in _inbound_phone_numbers(request.data):
            updated = UserProfile.objects.filter(phone_e164=phone).update(
                last_whatsapp_inbound_at=timezone.now()
            )
            if not updated:
                logger.info("inbound WhatsApp from unknown number %s", phone)
        return Response({"status": "ok"})


    def _signature_ok(self, request) -> bool:
        """
        Verify Meta's X-Hub-Signature-256 over the raw body.

        Without this, anyone could POST a fabricated inbound message and open a
        user's 24-hour free-form window. Verification is enforced whenever
        WHATSAPP_APP_SECRET is set; if it is not, we accept and warn loudly,
        so a missing secret is visible rather than silent.
        """
        secret = settings.WHATSAPP_APP_SECRET
        if not secret:
            logger.warning(
                "WHATSAPP_APP_SECRET is not set — webhook payloads are unverified"
            )
            return True

        header = request.headers.get("X-Hub-Signature-256", "")
        if not header.startswith("sha256="):
            return False

        expected = hmac.new(
            secret.encode(), request.body, hashlib.sha256
        ).hexdigest()
        return compare_digest(header.removeprefix("sha256="), expected)


def _inbound_phone_numbers(payload) -> list[str]:
    """Pull sender numbers out of Meta's deeply nested webhook envelope."""
    numbers: list[str] = []
    if not isinstance(payload, dict):
        return numbers
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            for message in (change.get("value") or {}).get("messages", []) or []:
                sender = message.get("from")
                if sender:
                    numbers.append(str(sender))
    return numbers
