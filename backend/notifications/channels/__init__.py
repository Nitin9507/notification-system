"""Channel adapter registry — the only place channels are wired to code."""

from notifications.channels.base import ChannelAdapter, Message, SendResult
from notifications.channels.email import EmailAdapter
from notifications.channels.webpush import WebPushAdapter
from notifications.channels.whatsapp import WhatsAppAdapter
from notifications.models import Channel

ADAPTERS: dict[str, ChannelAdapter] = {
    Channel.WHATSAPP: WhatsAppAdapter(),
    Channel.EMAIL: EmailAdapter(),
    Channel.WEB_PUSH: WebPushAdapter(),
}


def get_adapter(channel: str) -> ChannelAdapter:
    try:
        return ADAPTERS[channel]
    except KeyError as exc:
        raise ValueError(f"No adapter registered for channel '{channel}'") from exc


__all__ = [
    "ADAPTERS",
    "ChannelAdapter",
    "Message",
    "SendResult",
    "get_adapter",
]
