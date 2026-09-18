from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from autoapply.heartbeat.reporter import read_heartbeat_file
from autoapply.logging import get_logger
from autoapply.notify.composite import CompositeNotifier

log = get_logger("heartbeat.watchdog")


class HeartbeatWatchdog:
    def __init__(self, path: Path, notifier: CompositeNotifier, stale_after_hours: int):
        self.path = path
        self.notifier = notifier
        self.stale_after = timedelta(hours=stale_after_hours)

    async def check(self) -> bool:
        sent_at = read_heartbeat_file(self.path)
        now = datetime.now(timezone.utc)
        if sent_at is None:
            await self.notifier.send(
                "AutoApply heartbeat AUSENTE",
                f"No hay heartbeat en {self.path}. El agente puede estar caído.",
            )
            return False
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        age = now - sent_at
        if age > self.stale_after:
            await self.notifier.send(
                "AutoApply heartbeat VENCIDO",
                f"Último heartbeat: {sent_at.isoformat()}\nEdad: {age}\nUmbral: {self.stale_after}",
            )
            return False
        log.info("heartbeat_ok", sent_at=sent_at.isoformat(), age_seconds=int(age.total_seconds()))
        return True

    async def loop(self, interval_seconds: int = 3600) -> None:
        while True:
            await self.check()
            await asyncio.sleep(interval_seconds)
