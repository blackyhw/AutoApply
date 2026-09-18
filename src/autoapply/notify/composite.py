from __future__ import annotations

from autoapply.logging import get_logger
from autoapply.notify.base import Notifier

log = get_logger("notify")


class CompositeNotifier:
    def __init__(self, channels: list[Notifier]):
        self.channels = channels

    async def send(self, title: str, body: str) -> None:
        for channel in self.channels:
            try:
                await channel.send(title, body)
            except Exception as exc:
                log.warning("notify_channel_failed", channel=type(channel).__name__, error=str(exc))


class LogNotifier:
    async def send(self, title: str, body: str) -> None:
        log.info("notification", title=title, body=body)
