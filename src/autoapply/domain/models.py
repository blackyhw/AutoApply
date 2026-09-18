from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from autoapply.domain.enums import ApplicationStatus, MeetingDisposition, Portal


class Profile(BaseModel):
    full_name: str
    headline: str = ""
    location: str = ""
    years_experience: int = 0
    dedicated_email: str
    phone: str = ""
    links: dict[str, str] = Field(default_factory=dict)
    target_roles: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    work_modes: list[str] = Field(default_factory=list)
    seniority: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class Vacancy(BaseModel):
    portal: Portal
    external_id: str
    title: str
    company: str
    location: str = ""
    url: str
    description: str
    posted_at: datetime | None = None
    apply_email: str | None = None
    apply_url: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class MatchDecision(BaseModel):
    score: float = Field(ge=0, le=1)
    should_apply: bool
    reasons: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    selected_block_ids: list[str] = Field(default_factory=list)
    cover_letter_fields: dict[str, str] = Field(default_factory=dict)


class ApplicationPackage(BaseModel):
    cv_text: str
    cover_letter: str
    cover_subject: str
    selected_block_ids: list[str]
    cv_pdf_path: str | None = None
    candidate_email: str = ""
    candidate_name: str = ""


class ApplyOutcome(BaseModel):
    ok: bool
    confirmation_id: str | None = None
    detail: str = ""
    screenshot_path: str | None = None


class MeetingProposal(BaseModel):
    disposition: MeetingDisposition = MeetingDisposition.NONE
    title: str = ""
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = None
    location: str = ""
    meeting_url: str | None = None
    organizer_email: str | None = None
    confidence: float = 0.0
    notes: str = ""


class HeartbeatSnapshot(BaseModel):
    sent_at: datetime
    alive: bool = True
    applies_last_24h: int = 0
    applies_total: int = 0
    last_error: str | None = None
    dry_run: bool = True


class StoredApplication(BaseModel):
    id: int | None = None
    fingerprint: str
    portal: Portal
    external_id: str
    title: str
    company: str
    url: str
    status: ApplicationStatus
    match_score: float | None = None
    applied_at: datetime | None = None
    last_error: str | None = None
