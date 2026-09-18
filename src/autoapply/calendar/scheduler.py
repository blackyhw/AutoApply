from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from autoapply.calendar.base import CalendarProvider
from autoapply.domain.enums import MeetingDisposition
from autoapply.domain.models import MeetingProposal


class MeetingScheduler:
    def __init__(
        self,
        calendar: CalendarProvider,
        *,
        timezone: str,
        work_start: str,
        work_end: str,
        duration_minutes: int,
        auto_reschedule: bool,
    ):
        self.calendar = calendar
        self.timezone = ZoneInfo(timezone)
        self.work_start = _parse_hhmm(work_start)
        self.work_end = _parse_hhmm(work_end)
        self.duration = timedelta(minutes=duration_minutes)
        self.auto_reschedule = auto_reschedule

    async def place(self, proposal: MeetingProposal) -> tuple[MeetingProposal, bool]:
        """Return (final_proposal, rescheduled?)."""
        if proposal.starts_at is None:
            return proposal, False
        starts = proposal.starts_at
        ends = proposal.ends_at or (starts + self.duration)
        conflicts = await self.calendar.list_conflicts(starts, ends)
        if not conflicts:
            await self.calendar.create(proposal)
            return proposal, False
        if not self.auto_reschedule:
            return proposal, False
        slot = await self._next_free(starts)
        rescheduled = MeetingProposal(
            disposition=MeetingDisposition.RESCHEDULE_REQUEST
            if proposal.disposition is MeetingDisposition.PROPOSED
            else MeetingDisposition.CONFIRMED,
            title=proposal.title,
            starts_at=slot,
            ends_at=slot + self.duration,
            timezone=str(self.timezone),
            location=proposal.location,
            meeting_url=proposal.meeting_url,
            organizer_email=proposal.organizer_email,
            confidence=proposal.confidence,
            notes="Rescheduled to avoid a conflict.",
        )
        await self.calendar.create(rescheduled)
        return rescheduled, True

    async def _next_free(self, after: datetime) -> datetime:
        cursor = after + timedelta(minutes=30)
        for _ in range(80):
            local = cursor.astimezone(self.timezone) if cursor.tzinfo else cursor.replace(tzinfo=self.timezone)
            start_ok = time(local.hour, local.minute) >= self.work_start
            end_local = (local + self.duration).timetz()
            end_ok = time(end_local.hour, end_local.minute) <= self.work_end
            if local.weekday() < 5 and start_ok and end_ok:
                ends = cursor + self.duration
                if not await self.calendar.list_conflicts(cursor, ends):
                    return cursor
            cursor += timedelta(minutes=30)
        return after + timedelta(days=1)


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))
