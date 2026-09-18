from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from autoapply.apply.engine import ApplyEngine
from autoapply.calendar.local import LocalCalendar
from autoapply.calendar.scheduler import MeetingScheduler
from autoapply.collectors.dedupe import Deduper
from autoapply.collectors.registry import build_collectors
from autoapply.domain.enums import ApplicationStatus
from autoapply.domain.models import Vacancy
from autoapply.errors import CollectorNotConfigured, DailyApplyLimitReached, KillSwitchActive
from autoapply.generator.blocks import BlockCatalog
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
        self.matcher = Matcher(self.llm, self.catalog, self.settings.match_threshold)
        self.collectors = build_collectors(self.settings)
        self.apply_engine = ApplyEngine(dry_run=self.settings.dry_run)
        self.notifier = CompositeNotifier(
            [
                LogNotifier(),
                TelegramNotifier(self.settings.telegram_bot_token, self.settings.telegram_chat_id),
                EmailNotifier(self.settings),
            ]
        )
        self.inbox = ImapInbox(self.settings)
        self.meeting_parser = MeetingParser(self.llm)

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
        return MeetingScheduler(
            LocalCalendar(repo),
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
                    next_heartbeat = datetime.now(timezone.utc).replace(microsecond=0)
                    from datetime import timedelta

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
        stats = {"collected": 0, "new": 0, "applied": 0, "rejected": 0, "failed": 0}
        try:
            vacancies = await self._collect()
            stats["collected"] = len(vacancies)
            fresh = Deduper(repo).unseen(vacancies)
            stats["new"] = len(fresh)
            for vacancy, fingerprint in fresh:
                repo.upsert_vacancy(vacancy, fingerprint)
                try:
                    applied = await self._handle_vacancy(repo, vacancy, fingerprint)
                    if applied:
                        stats["applied"] += 1
                    else:
                        stats["rejected"] += 1
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
                batch = await collector.collect()
            except CollectorNotConfigured as exc:
                log.warning("collector_skipped", collector=collector.name, error=str(exc))
                continue
            vacancies.extend(batch)
        return vacancies

    async def _handle_vacancy(self, repo: Repository, vacancy: Vacancy, fingerprint: str) -> bool:
        decision = await self.matcher.score(vacancy, self.profile)
        if not decision.should_apply:
            repo.save_application(
                vacancy,
                fingerprint,
                ApplicationStatus.REJECTED,
                match_score=decision.score,
            )
            return False

        package = self.generator.build(decision, self.profile)
        repo.save_application(
            vacancy,
            fingerprint,
            ApplicationStatus.GENERATED,
            match_score=decision.score,
            selected_block_ids=package.selected_block_ids,
            cover_letter=package.cover_letter,
        )
        from datetime import timedelta

        applied_today = repo.count_applies_since(datetime.now(timezone.utc) - timedelta(hours=24))
        if applied_today >= self.settings.max_applies_per_day:
            raise DailyApplyLimitReached(str(self.settings.max_applies_per_day))

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
        return outcome.ok

    async def _process_inbox(self, repo: Repository) -> None:
        if not self.inbox.configured():
            return
        scheduler = self._scheduler(repo)
        for item in self.inbox.fetch_unseen():
            proposal = await self.meeting_parser.parse(
                message_id=item.message_id,
                subject=item.subject,
                body=item.body,
                ics_text=item.ics_text,
            )
            if proposal.disposition.value == "none":
                continue
            placed, rescheduled = await scheduler.place(proposal)
            verb = "reprogramada" if rescheduled else "agendada"
            await self.notifier.send(
                f"Reunión {verb}",
                f"{placed.title}\nstart={placed.starts_at}\nurl={placed.meeting_url or '-'}",
            )

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
