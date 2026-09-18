from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from autoapply.domain.enums import MeetingDisposition
from autoapply.domain.models import MeetingProposal
from autoapply.errors import ConfigurationError
from autoapply.logging import get_logger

log = get_logger("calendar.google")

EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"


class GoogleCalendar:
    """Google Calendar via a service-account JSON sitting on the VM secrets volume."""

    def __init__(self, credentials_file: Path | str | None, calendar_id: str):
        self.credentials_file = Path(credentials_file) if credentials_file else None
        self.calendar_id = calendar_id

    def configured(self) -> bool:
        return bool(self.credentials_file and self.credentials_file.exists())

    async def list_conflicts(self, starts_at: datetime, ends_at: datetime) -> list[MeetingProposal]:
        token = self._token()
        params = {
            "timeMin": _rfc3339(starts_at),
            "timeMax": _rfc3339(ends_at),
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        url = EVENTS_URL.format(calendar_id=self.calendar_id)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
        if response.status_code >= 400:
            raise ConfigurationError(f"Google Calendar list failed: {response.status_code} {response.text[:200]}")
        items = response.json().get("items") or []
        conflicts: list[MeetingProposal] = []
        for item in items:
            start = _parse_event_time(item.get("start") or {})
            end = _parse_event_time(item.get("end") or {})
            conflicts.append(
                MeetingProposal(
                    disposition=MeetingDisposition.CONFIRMED,
                    title=item.get("summary") or "busy",
                    starts_at=start,
                    ends_at=end,
                    location=item.get("location") or "",
                    meeting_url=(item.get("hangoutLink") or None),
                    confidence=1.0,
                )
            )
        return conflicts

    async def create(self, proposal: MeetingProposal) -> str:
        token = self._token()
        if proposal.starts_at is None:
            raise ValueError("Meeting proposal is missing starts_at")
        ends = proposal.ends_at or (proposal.starts_at + timedelta(minutes=30))
        payload = {
            "summary": proposal.title or "Entrevista",
            "description": proposal.notes,
            "location": proposal.location or proposal.meeting_url or "",
            "start": {"dateTime": _rfc3339(proposal.starts_at)},
            "end": {"dateTime": _rfc3339(ends)},
        }
        url = EVENTS_URL.format(calendar_id=self.calendar_id)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
        if response.status_code >= 400:
            raise ConfigurationError(f"Google Calendar create failed: {response.status_code} {response.text[:200]}")
        return str(response.json().get("id") or "")

    def _token(self) -> str:
        if not self.configured():
            raise ConfigurationError("Google Calendar credentials file is missing")
        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests
        except ImportError as exc:  # pragma: no cover
            raise ConfigurationError("google-auth is not installed") from exc
        creds = service_account.Credentials.from_service_account_file(
            str(self.credentials_file),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token


def _rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _parse_event_time(payload: dict) -> datetime | None:
    raw = payload.get("dateTime") or payload.get("date")
    if not raw:
        return None
    try:
        if len(raw) == 10:
            return datetime.fromisoformat(raw)
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
