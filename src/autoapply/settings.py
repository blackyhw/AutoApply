from __future__ import annotations

from pathlib import Path

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings. Environment variables override defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    agent_email: EmailStr = "jobs-agent@example.com"
    agent_email_imap_host: str = ""
    agent_email_imap_port: int = 993
    agent_email_imap_username: str = ""
    agent_email_imap_password: str = ""
    agent_email_smtp_host: str = ""
    agent_email_smtp_port: int = 587
    agent_email_smtp_username: str = ""
    agent_email_smtp_password: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.2
    llm_max_output_tokens: int = 1024

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    alert_email: str = ""

    google_calendar_id: str = "primary"
    google_calendar_credentials_file: Path | None = None

    dry_run: bool = Field(default=True, validation_alias="AUTOAPPLY_DRY_RUN")
    kill_switch: bool = Field(default=False, validation_alias="AUTOAPPLY_KILL_SWITCH")
    timezone: str = Field(
        default="America/Argentina/Buenos_Aires",
        validation_alias="AUTOAPPLY_TIMEZONE",
    )
    match_threshold: float = 0.72
    max_applies_per_day: int = 10
    poll_interval_seconds: int = 900
    sqlite_path: Path = Path("data/autoapply.db")
    heartbeat_path: Path = Path("data/heartbeat.json")
    heartbeat_interval_hours: int = 24
    heartbeat_stale_after_hours: int = 26

    config_dir: Path = Path("config")
    default_config_path: Path = Path("config/default.yaml")
    profile_path: Path = Path("config/profile.yaml")
    cv_blocks_path: Path = Path("config/cv_blocks.yaml")
    cover_letter_template_path: Path = Path("config/cover_letter.template.txt")
    file_feed_path: Path = Path("data/samples/vacancies.json")
    enabled_collectors: list[str] = Field(
        default_factory=lambda: ["file_feed", "linkedin", "computrabajo", "indeed"]
    )
    collector_max_per_portal: int = 12
    collector_delay_seconds: float = 1.2
    fetch_job_details: bool = True
    indeed_host: str = "ar.indeed.com"
    computrabajo_base_url: str = "https://www.computrabajo.com.ar"
    generated_dir: Path = Path("data/generated")
    playwright_state_dir: Path = Path("secrets/playwright")
    review_first_n: int = 0

    working_hours_start: str = "09:00"
    working_hours_end: str = "18:00"
    meeting_duration_minutes: int = 30
    auto_reschedule: bool = False


    @field_validator("enabled_collectors", mode="before")
    @classmethod
    def _split_collectors(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def resolve(self) -> "Settings":
        """Resolve relative paths against the repository root when needed."""
        root = _repo_root()
        values = self.model_dump()
        for field_name, value in values.items():
            if isinstance(value, Path) and not value.is_absolute():
                candidate = Path(value)
                if not candidate.exists():
                    candidate = root / value
                values[field_name] = candidate
        return Settings.model_construct(**values)


def load_settings() -> Settings:
    return Settings().resolve()
