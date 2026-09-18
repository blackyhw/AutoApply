from __future__ import annotations

from datetime import datetime
from typing import Protocol

from autoapply.domain.models import MeetingProposal


class CalendarProvider(Protocol):
    async def list_conflicts(self, starts_at: datetime, ends_at: datetime) -> list[MeetingProposal]:
        ...

    async def create(self, proposal: MeetingProposal) -> str:
        """Create the event and return a provider-specific id."""
