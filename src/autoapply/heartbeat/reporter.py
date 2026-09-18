from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from autoapply.domain.models import HeartbeatSnapshot
from autoapply.notify.composite import CompositeNotifier
from autoapply.persistence.repositories import Repository


class HeartbeatReporter:
    def __init__(self, repo: Repository, notifier: CompositeNotifier, path: Path, dry_run: bool):
        self.repo = repo
        self.notifier = notifier
        self.path = path
        self.dry_run = dry_run

    def snapshot(self, last_error: str | None = None) -> HeartbeatSnapshot:
        now = datetime.now(timezone.utc)
        from datetime import timedelta

        applies_last_24h = self.repo.count_applies_since(now - timedelta(hours=24))
        return HeartbeatSnapshot(
            sent_at=now,
            alive=True,
            applies_last_24h=applies_last_24h,
            applies_total=self.repo.count_applies_total(),
            last_error=last_error,
            dry_run=self.dry_run,
        )

    async def emit(self, last_error: str | None = None) -> HeartbeatSnapshot:
        snap = self.snapshot(last_error)
        payload = snap.model_dump_json()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(payload, encoding="utf-8")
        self.repo.record_heartbeat(
            sent_at=snap.sent_at,
            applies_last_24h=snap.applies_last_24h,
            applies_total=snap.applies_total,
            payload=payload,
            last_error=last_error,
        )
        await self.notifier.send(
            "AutoApply heartbeat",
            (
                f"alive={snap.alive}\n"
                f"applies_last_24h={snap.applies_last_24h}\n"
                f"applies_total={snap.applies_total}\n"
                f"dry_run={snap.dry_run}\n"
                f"last_error={snap.last_error or '-'}"
            ),
        )
        return snap


def read_heartbeat_file(path: Path) -> datetime | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return datetime.fromisoformat(payload["sent_at"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return None
