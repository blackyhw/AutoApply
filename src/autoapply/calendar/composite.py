from __future__ import annotations

from datetime import datetime

from autoapply.calendar.base import CalendarProvider
from autoapply.calendar.local import LocalCalendar
from autoapply.domain.models import MeetingProposal
from autoapply.logging import get_logger

log = get_logger("calendar.composite")


class CompositeCalendar:
    """Always persist locally; optionally mirror to Google Calendar."""

    def __init__(self, local: LocalCalendar, remote: CalendarProvider | None = None):
        self.local = local
        self.remote = remote

    async def list_conflicts(self, starts_at: datetime, ends_at: datetime) -> list[MeetingProposal]:
        local = await self.local.list_conflicts(starts_at, ends_at)
        if self.remote is None:
            return local
        try:
            remote = await self.remote.list_conflicts(starts_at, ends_at)
        except Exception as exc:
            log.warning("remote_calendar_list_failed", error=str(exc))
            return local
        return local + remote

    async def create(self, proposal: MeetingProposal) -> str:
        local_id = await self.local.create(proposal)
        if self.remote is None:
            return local_id
        try:
            await self.remote.create(proposal)
        except Exception as exc:
            log.warning("remote_calendar_create_failed", error=str(exc))
        return local_id
