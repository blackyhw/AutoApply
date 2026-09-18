from datetime import datetime, timedelta, timezone
import json

import pytest

from autoapply.heartbeat.reporter import HeartbeatReporter
from autoapply.heartbeat.watchdog import HeartbeatWatchdog
from autoapply.notify.composite import CompositeNotifier, LogNotifier
from autoapply.persistence.repositories import Repository


class CaptureNotifier:
    def __init__(self):
        self.titles: list[str] = []

    async def send(self, title: str, body: str) -> None:
        self.titles.append(title)


@pytest.mark.asyncio
async def test_heartbeat_roundtrip(repo: Repository, tmp_path, settings):
    path = tmp_path / "heartbeat.json"
    reporter = HeartbeatReporter(repo, CompositeNotifier([LogNotifier()]), path, dry_run=True)
    snap = await reporter.emit()
    assert path.exists()
    assert snap.alive is True
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "applies_last_24h" in payload


@pytest.mark.asyncio
async def test_watchdog_alerts_when_stale(tmp_path):
    path = tmp_path / "heartbeat.json"
    stale = (datetime.now(timezone.utc) - timedelta(hours=40)).isoformat()
    path.write_text(json.dumps({"sent_at": stale}), encoding="utf-8")
    capture = CaptureNotifier()
    ok = await HeartbeatWatchdog(path, capture, stale_after_hours=26).check()
    assert ok is False
    assert any("VENCIDO" in title for title in capture.titles)
