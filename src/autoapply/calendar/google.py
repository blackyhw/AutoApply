from __future__ import annotations

from datetime import datetime

from autoapply.calendar.base import CalendarProvider
from autoapply.domain.models import MeetingProposal
from autoapply.errors import ConfigurationError


class GoogleCalendar:
    """Stub. Load a service-account or OAuth token from the VM secrets volume."""

    def __init__(self, credentials_file: str | None, calendar_id: str):
        self.credentials_file = credentials_file
        self.calendar_id = calendar_id

    async def list_conflicts(self, starts_at: datetime, ends_at: datetime) -> list[MeetingProposal]:
        raise ConfigurationError("Google Calendar adapter is a stub.")

    async def create(self, proposal: MeetingProposal) -> str:
        raise ConfigurationError("Google Calendar adapter is a stub.")


_: CalendarProvider = GoogleCalendar  # type: ignore[assignment]
