from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from autoapply.apply.engine import ApplyEngine
from autoapply.calendar.composite import CompositeCalendar
from autoapply.calendar.google import GoogleCalendar
from autoapply.calendar.local import LocalCalendar
from autoapply.calendar.scheduler import MeetingScheduler
from autoapply.collectors.dedupe import Deduper
from autoapply.collectors.registry import build_collectors
from autoapply.domain.enums import ApplicationStatus
from autoapply.domain.models import Vacancy
from autoapply.errors import CollectorError, CollectorNotConfigured, DailyApplyLimitReached, KillSwitchActive
from autoapply.generator.blocks import BlockCatalog
from autoapply.generator.compose import compose_application
from autoapply.generator.cover_letter import ApplicationGenerator, CoverLetterRenderer
from autoapply.generator.cv_assembler import CvAssembler
from autoapply.heartbeat.reporter import HeartbeatReporter
from autoapply.inbox.imap_client import ImapInbox
from autoapply.inbox.parser import MeetingParser
from autoapply.llm.router import LlmRouter, build_llm_router
from autoapply.logging import get_logger
from autoapply.matcher.scorer import Matcher
from autoapply.notify.composite import CompositeNotifier, LogNotifier
from autoapply.notify.emailer import EmailNotifier
from autoapply.notify.mailer import send_email, smtp_configured
from autoapply.notify.telegram import TelegramNotifier
from autoapply.persistence.db import make_session_factory
from autoapply.persistence.repositories import Repository
from autoapply.profile.loader import load_profile
from autoapply.settings import Settings, load_settings

log = get_logger("orchestrator")


class Agent:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        Path(self.settings.generated_dir).mkdir(parents=True, exist_ok=True)
        self._session_factory = make_session_factory(str(self.settings.sqlite_path))
        self.profile = load_profile(Path(self.settings.profile_path))
        blocks_path = _existing_or_example(Path(self.settings.cv_blocks_path))
        self.catalog = BlockCatalog.from_yaml(blocks_path)
        template_path = Path(self.settings.cover_letter_template_path)
        self.generator = ApplicationGenerator(
            CvAssembler(self.catalog),
            CoverLetterRenderer.from_path(template_path),
        )
        self.llm: LlmRouter = build_llm_router(
            gemini_key=self.settings.gemini_api_key,
            groq_key=self.settings.groq_api_key,
            gemini_model=self.settings.gemini_model,
            groq_model=self.settings.groq_model,
        )
        self.matcher = Matcher(self.catalog, self.settings.match_threshold)
        self.collectors = build_collectors(self.settings)
        self.apply_engine = ApplyEngine(self.settings)
        self.notifier = CompositeNotifier(
            [
                LogNotifier(),
                TelegramNotifier(self.settings.telegram_bot_token, self.settings.telegram_chat_id),
                EmailNotifier(self.settings),
            ]
        )
        self.inbox = ImapInbox(self.settings)
        self.meeting_parser = MeetingParser(None)

    def _repo(self) -> Repository:
        return Repository(self._session_factory())

    def _heartbeat(self, repo: Repository) -> HeartbeatReporter:
        return HeartbeatReporter(
            repo,
            self.notifier,
            Path(self.settings.heartbeat_path),
            dry_run=self.settings.dry_run,
        )

    def _scheduler(self, repo: Repository) -> MeetingScheduler:
        local = LocalCalendar(repo)
        remote = None
        creds = self.settings.google_calendar_credentials_file
        google = GoogleCalendar(creds, self.settings.google_calendar_id)
        if google.configured():
            remote = google
        calendar = CompositeCalendar(local, remote)
        return MeetingScheduler(
            calendar,
            timezone=self.settings.timezone,
            work_start=self.settings.working_hours_start,
            work_end=self.settings.working_hours_end,
            duration_minutes=self.settings.meeting_duration_minutes,
            auto_reschedule=self.settings.auto_reschedule,
        )

    async def run_forever(self) -> None:
        log.info("agent_started", dry_run=self.settings.dry_run)
        next_heartbeat = datetime.now(timezone.utc)
        while True:
            repo = self._repo()
            try:
                if datetime.now(timezone.utc) >= next_heartbeat:
                    await self._heartbeat(repo).emit()
                    next_heartbeat = datetime.now(timezone.utc) + timedelta(
                        hours=self.settings.heartbeat_interval_hours
                    )
                await self.run_once()
            except Exception as exc:
                log.exception("loop_error")
                await self.notifier.send("AutoApply error", str(exc))
            finally:
                repo.session.close()
            await asyncio.sleep(self.settings.poll_interval_seconds)

    async def run_once(self) -> dict[str, int]:
        if self.settings.kill_switch:
            raise KillSwitchActive("Kill switch is on")
        repo = self._repo()
        stats = {"collected": 0, "new": 0, "applied": 0, "rejected": 0, "failed": 0, "review": 0}
        try:
            vacancies = await self._collect()
            stats["collected"] = len(vacancies)
            fresh = Deduper(repo).unseen(vacancies)
            stats["new"] = len(fresh)
            for vacancy, fingerprint in fresh:
                repo.upsert_vacancy(vacancy, fingerprint)
                try:
                    result = await self._handle_vacancy(repo, vacancy, fingerprint)
                    stats[result] += 1
                except DailyApplyLimitReached:
                    log.info("daily_limit_reached")
                    break
                except Exception as exc:
                    stats["failed"] += 1
                    repo.save_application(
                        vacancy,
                        fingerprint,
                        ApplicationStatus.FAILED,
                        last_error=str(exc),
                    )
                    log.exception("vacancy_failed", title=vacancy.title)
            await self._process_inbox(repo)
        finally:
            repo.session.close()
        log.info("cycle_done", **stats)
        return stats

    async def _collect(self) -> list[Vacancy]:
        vacancies: list[Vacancy] = []
        for collector in self.collectors:
            try:
                batch = await collector.collect(self.profile)
            except (CollectorNotConfigured, CollectorError) as exc:
                log.warning("collector_skipped", collector=collector.name, error=str(exc))
                continue
            log.info("collector_ok", collector=collector.name, count=len(batch))
            vacancies.extend(batch)
        return vacancies

    async def _handle_vacancy(self, repo: Repository, vacancy: Vacancy, fingerprint: str) -> str:
        decision = await self.matcher.score(vacancy, self.profile)
        if not decision.should_apply:
            repo.save_application(
                vacancy,
                fingerprint,
                ApplicationStatus.REJECTED,
                match_score=decision.score,
            )
            return "rejected"

        decision = await compose_application(self.llm, self.catalog, vacancy, self.profile, decision)
        pdf_path = Path(self.settings.generated_dir) / f"{fingerprint[:16]}.pdf"
        package = self.generator.build(decision, self.profile, pdf_path=pdf_path)
        repo.save_application(
            vacancy,
            fingerprint,
            ApplicationStatus.GENERATED,
            match_score=decision.score,
            selected_block_ids=package.selected_block_ids,
            cover_letter=package.cover_letter,
        )

        applied_today = repo.count_applies_since(datetime.now(timezone.utc) - timedelta(hours=24))
        if applied_today >= self.settings.max_applies_per_day:
            raise DailyApplyLimitReached(str(self.settings.max_applies_per_day))

        if self.settings.review_first_n and repo.count_applies_total() < self.settings.review_first_n:
            await self.notifier.send(
                f"Revisar postulación: {vacancy.title}",
                f"{vacancy.company}\n{vacancy.url}\nscore={decision.score:.2f}\npdf={package.cv_pdf_path}",
            )
            return "review"

        repo.save_application(vacancy, fingerprint, ApplicationStatus.APPLYING, match_score=decision.score)
        outcome = await self.apply_engine.apply(vacancy, package)
        status = ApplicationStatus.APPLIED if outcome.ok else ApplicationStatus.FAILED
        repo.save_application(
            vacancy,
            fingerprint,
            status,
            match_score=decision.score,
            selected_block_ids=package.selected_block_ids,
            cover_letter=package.cover_letter,
            confirmation_id=outcome.confirmation_id,
            last_error=None if outcome.ok else outcome.detail,
            applied=outcome.ok,
        )
        await self.notifier.send(
            f"Postulación {'enviada' if outcome.ok else 'fallida'}: {vacancy.title}",
            f"{vacancy.company}\n{vacancy.url}\nscore={decision.score:.2f}\n{outcome.detail}",
        )
        return "applied" if outcome.ok else "failed"

    async def _process_inbox(self, repo: Repository) -> None:
        if not self.inbox.configured():
            return
        scheduler = self._scheduler(repo)
        seen_ids: list[str] = []
        try:
            unseen = self.inbox.fetch_unseen()
        except Exception as exc:
            log.warning("inbox_unavailable", error=str(exc))
            return
        for item in unseen:
            try:
                proposal = await self.meeting_parser.parse(
                    message_id=item.message_id,
                    subject=item.subject,
                    body=item.body,
                    ics_text=item.ics_text,
                )
                if proposal.disposition.value == "none":
                    if item.imap_uid:
                        seen_ids.append(item.imap_uid)
                    continue
                if not proposal.organizer_email and item.from_email:
                    proposal = proposal.model_copy(update={"organizer_email": item.from_email})
                original_start = proposal.starts_at
                placed, rescheduled = await scheduler.place(proposal)
                verb = "reprogramada" if rescheduled else "agendada"
                await self.notifier.send(
                    f"Reunión {verb}",
                    f"{placed.title}\nstart={placed.starts_at}\nurl={placed.meeting_url or '-'}",
                )
                if rescheduled and placed.organizer_email and smtp_configured(self.settings):
                    await self._send_reschedule(placed, original_start)
                if item.imap_uid:
                    seen_ids.append(item.imap_uid)
            except Exception:
                log.exception("inbox_item_failed", message_id=item.message_id)
        self.inbox.mark_seen(seen_ids)

    async def _send_reschedule(self, placed, original_start) -> None:
        template_path = Path(self.settings.config_dir) / "reschedule.template.txt"
        if not template_path.exists():
            template_path = Path(__file__).resolve().parents[2] / "config" / "reschedule.template.txt"
        raw = template_path.read_text(encoding="utf-8") if template_path.exists() else (
            "Asunto: Reprogramación\n\nNuevo horario: {new_start}\n"
        )
        values = {
            "title": placed.title,
            "original_start": str(original_start),
            "new_start": str(placed.starts_at),
            "candidate_name": self.profile.full_name,
            "dedicated_email": self.profile.dedicated_email,
        }
        rendered = Template(raw.replace("{", "${").replace("$${", "${")).safe_substitute(values)
        # The replace above is fragile if already dollar-style; use a simpler fill:
        rendered = raw
        for key, value in values.items():
            rendered = rendered.replace("{" + key + "}", str(value))
        subject, _, body = rendered.partition("\n")
        subject = subject.replace("Asunto:", "", 1).strip()
        send_email(self.settings, to=placed.organizer_email, subject=subject, body=body.strip())

    async def emit_heartbeat(self) -> None:
        repo = self._repo()
        try:
            await self._heartbeat(repo).emit()
        finally:
            repo.session.close()


def _existing_or_example(path: Path) -> Path:
    if path.exists():
        return path
    example = path.with_name(path.stem + ".example.yaml")
    if example.exists():
        return example
    return path
