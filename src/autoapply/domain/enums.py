from __future__ import annotations

from enum import StrEnum


class Portal(StrEnum):
    FILE_FEED = "file_feed"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    COMPUTRABAJO = "computrabajo"


class ApplicationStatus(StrEnum):
    SEEN = "seen"
    MATCHED = "matched"
    REJECTED = "rejected"
    GENERATED = "generated"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    RESPONSE_RECEIVED = "response_received"
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_RESCHEDULED = "meeting_rescheduled"


class LlmProviderName(StrEnum):
    GEMINI = "gemini"
    GROQ = "groq"
    MOCK = "mock"


class MeetingDisposition(StrEnum):
    NONE = "none"
    CONFIRMED = "confirmed"
    PROPOSED = "proposed"
    CANCELLED = "cancelled"
    RESCHEDULE_REQUEST = "reschedule_request"
