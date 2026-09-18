from __future__ import annotations

from datetime import datetime, timedelta

from autoapply.calendar.base import CalendarProvider
from autoapply.domain.enums import MeetingDisposition
from autoapply.domain.models import MeetingProposal
from autoapply.persistence.repositories import Repository


class LocalCalendar:
    """SQLite-backed calendar used until Google Calendar is wired."""

    def __init__(self, repo: Repository):
        self.repo = repo

    async def list_conflicts(self, starts_at: datetime, ends_at: datetime) -> list[MeetingProposal]:
        rows = self.repo.overlapping_meetings(starts_at, ends_at)
        return [
            MeetingProposal(
                disposition=MeetingDisposition.CONFIRMED,
                title=row.title,
                starts_at=row.starts_at,
                ends_at=row.ends_at,
                timezone=row.timezone,
                location=row.location,
                meeting_url=row.meeting_url,
                organizer_email=row.organizer_email,
                confidence=1.0,
            )
            for row in rows
        ]

    async def create(self, proposal: MeetingProposal) -> str:
        if proposal.starts_at is None:
            raise ValueError("Meeting proposal is missing starts_at")
        ends = proposal.ends_at or (proposal.starts_at + timedelta(minutes=30))
        row = self.repo.add_meeting(
            title=proposal.title or "Entrevista",
            starts_at=proposal.starts_at,
            ends_at=ends,
            timezone_name=proposal.timezone or "UTC",
            location=proposal.location,
            meeting_url=proposal.meeting_url,
            organizer_email=proposal.organizer_email,
        )
        return str(row.id)


_: CalendarProvider = LocalCalendar  # type: ignore[assignment]
