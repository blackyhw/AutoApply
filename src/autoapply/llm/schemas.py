from __future__ import annotations

from pydantic import BaseModel, Field


class CoverLetterFields(BaseModel):
    recruiter_name: str = "equipo de reclutamiento"
    role: str
    company: str
    matching_skills_sentence: str
    availability_window: str = "días hábiles, 9 a 18 hs"
    candidate_name: str
    dedicated_email: str


class MatchLlmOutput(BaseModel):
    score: float = Field(ge=0, le=1)
    should_apply: bool
    reasons: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    selected_block_ids: list[str] = Field(default_factory=list)
    cover_letter_fields: CoverLetterFields


class MeetingLlmOutput(BaseModel):
    is_meeting_related: bool
    disposition: str = "none"
    title: str = ""
    starts_at_iso: str | None = None
    ends_at_iso: str | None = None
    timezone: str | None = None
    location: str = ""
    meeting_url: str | None = None
    organizer_email: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    notes: str = ""
