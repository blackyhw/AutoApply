from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from autoapply.domain.enums import ApplicationStatus, Portal
from autoapply.domain.models import StoredApplication, Vacancy
from autoapply.persistence.db import ApplicationRow, HeartbeatRow, MeetingRow, VacancyRow


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def vacancy_exists(self, fingerprint: str) -> bool:
        stmt = select(VacancyRow.id).where(VacancyRow.fingerprint == fingerprint)
        return self.session.scalar(stmt) is not None

    def upsert_vacancy(self, vacancy: Vacancy, fingerprint: str) -> VacancyRow:
        stmt = select(VacancyRow).where(VacancyRow.fingerprint == fingerprint)
        row = self.session.scalar(stmt)
        now = datetime.now(timezone.utc)
        if row is None:
            row = VacancyRow(
                fingerprint=fingerprint,
                portal=vacancy.portal.value,
                external_id=vacancy.external_id,
                title=vacancy.title,
                company=vacancy.company,
                location=vacancy.location,
                url=str(vacancy.url),
                description=vacancy.description,
                first_seen_at=now,
                last_seen_at=now,
            )
            self.session.add(row)
        else:
            row.last_seen_at = now
        self.session.commit()
        return row

    def get_application(self, fingerprint: str) -> ApplicationRow | None:
        stmt = select(ApplicationRow).where(ApplicationRow.fingerprint == fingerprint)
        return self.session.scalar(stmt)

    def save_application(
        self,
        vacancy: Vacancy,
        fingerprint: str,
        status: ApplicationStatus,
        *,
        match_score: float | None = None,
        selected_block_ids: list[str] | None = None,
        cover_letter: str = "",
        confirmation_id: str | None = None,
        last_error: str | None = None,
        applied: bool = False,
    ) -> ApplicationRow:
        row = self.get_application(fingerprint)
        now = datetime.now(timezone.utc)
        if row is None:
            row = ApplicationRow(
                fingerprint=fingerprint,
                portal=vacancy.portal.value,
                external_id=vacancy.external_id,
                title=vacancy.title,
                company=vacancy.company,
                url=str(vacancy.url),
                status=status.value,
            )
            self.session.add(row)
        row.status = status.value
        row.updated_at = now
        if match_score is not None:
            row.match_score = match_score
        if selected_block_ids is not None:
            row.selected_block_ids = ",".join(selected_block_ids)
        if cover_letter:
            row.cover_letter = cover_letter
        if confirmation_id:
            row.confirmation_id = confirmation_id
        row.last_error = last_error
        if applied:
            row.applied_at = now
        self.session.commit()
        return row

    def count_applies_since(self, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(ApplicationRow)
            .where(
                ApplicationRow.status == ApplicationStatus.APPLIED.value,
                ApplicationRow.applied_at.is_not(None),
                ApplicationRow.applied_at >= since,
            )
        )
        return int(self.session.scalar(stmt) or 0)

    def count_applies_total(self) -> int:
        stmt = (
            select(func.count())
            .select_from(ApplicationRow)
            .where(ApplicationRow.status == ApplicationStatus.APPLIED.value)
        )
        return int(self.session.scalar(stmt) or 0)

    def overlapping_meetings(self, starts_at: datetime, ends_at: datetime) -> list[MeetingRow]:
        stmt = select(MeetingRow).where(
            MeetingRow.status.in_(("scheduled", "rescheduled")),
            MeetingRow.starts_at < ends_at,
            MeetingRow.ends_at > starts_at,
        )
        return list(self.session.scalars(stmt))

    def add_meeting(
        self,
        *,
        title: str,
        starts_at: datetime,
        ends_at: datetime,
        timezone_name: str,
        location: str = "",
        meeting_url: str | None = None,
        organizer_email: str | None = None,
        application_id: int | None = None,
        source_message_id: str | None = None,
        status: str = "scheduled",
    ) -> MeetingRow:
        row = MeetingRow(
            application_id=application_id,
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            timezone=timezone_name,
            location=location,
            meeting_url=meeting_url,
            organizer_email=organizer_email,
            status=status,
            source_message_id=source_message_id,
        )
        self.session.add(row)
        self.session.commit()
        return row

    def record_heartbeat(self, sent_at: datetime, applies_last_24h: int, applies_total: int, payload: str, last_error: str | None) -> HeartbeatRow:
        row = HeartbeatRow(
            sent_at=sent_at,
            applies_last_24h=applies_last_24h,
            applies_total=applies_total,
            last_error=last_error,
            payload=payload,
        )
        self.session.add(row)
        self.session.commit()
        return row

    def latest_heartbeat_at(self) -> datetime | None:
        stmt = select(func.max(HeartbeatRow.sent_at))
        return self.session.scalar(stmt)

    def to_stored(self, row: ApplicationRow) -> StoredApplication:
        return StoredApplication(
            id=row.id,
            fingerprint=row.fingerprint,
            portal=Portal(row.portal),
            external_id=row.external_id,
            title=row.title,
            company=row.company,
            url=row.url,
            status=ApplicationStatus(row.status),
            match_score=row.match_score,
            applied_at=row.applied_at,
            last_error=row.last_error,
        )


def applies_in_last_day(repo: Repository) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return repo.count_applies_since(since)
