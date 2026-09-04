"""
The single seam every provider sits behind.

The dispatcher only ever sees ``ChannelAdapter.send(...) -> SendResult``.
Adding a fourth channel (SMS, Slack, ...) means writing one subclass and adding
one value to ``Channel`` — no dispatcher change.
"""

from dataclasses import dataclass, field
from typing import Any

from notifications.models import DeliveryStatus


@dataclass
class Message:
    """A fully rendered message, ready to hand to a provider."""

    recipient: str
    subject: str = ""
    body: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SendResult:
    status: str
    provider: str = ""
    provider_message_id: str = ""
    error: str = ""
    response: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in (DeliveryStatus.SENT, DeliveryStatus.DRY_RUN)

    @classmethod
    def sent(cls, provider: str, message_id: str = "", response: dict | None = None):
        return cls(
            status=DeliveryStatus.SENT,
            provider=provider,
            provider_message_id=message_id,
            response=response or {},
        )

    @classmethod
    def failed(cls, provider: str, error: str, response: dict | None = None):
        return cls(
            status=DeliveryStatus.FAILED,
            provider=provider,
            error=error,
            response=response or {},
        )

    @classmethod
    def dry_run(cls, provider: str, reason: str):
        return cls(status=DeliveryStatus.DRY_RUN, provider=provider, error=reason)

    @classmethod
    def skipped(cls, provider: str, reason: str):
        return cls(status=DeliveryStatus.SKIPPED, provider=provider, error=reason)


class ChannelAdapter:
    """Base class for every channel implementation."""

    channel: str = ""
    provider: str = ""

    def is_configured(self) -> bool:
        """False when credentials are missing; the adapter then dry-runs."""
        raise NotImplementedError

    def resolve_recipient(self, user) -> str:
        """The user's address on this channel, or '' when unreachable."""
        raise NotImplementedError

    def build_message(self, template, ctx, recipient: str) -> Message:
        """Render the stored template into a provider-agnostic message."""
        raise NotImplementedError

    def deliver(self, message: Message) -> SendResult:
        """Actually call the vendor. Only invoked when ``is_configured()``."""
        raise NotImplementedError

    def send(self, message: Message) -> SendResult:
        if not message.recipient:
            return SendResult.skipped(self.provider, "no recipient on file")
        if not self.is_configured():
            return SendResult.dry_run(
                self.provider, "provider credentials not configured"
            )
        try:
            return self.deliver(message)
        except Exception as exc:  # noqa: BLE001 - a provider must never 500 the site
            return SendResult.failed(self.provider, f"{type(exc).__name__}: {exc}")
