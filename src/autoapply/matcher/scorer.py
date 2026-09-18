from __future__ import annotations

import json

from autoapply.domain.models import MatchDecision, Profile, Vacancy
from autoapply.generator.blocks import BlockCatalog
from autoapply.llm.base import LlmRequest
from autoapply.llm.router import LlmRouter
from autoapply.llm.schemas import MatchLlmOutput
from autoapply.matcher.prompts import MATCH_TASK, trusted_match_context
from autoapply.security.prompt_guard import build_messages
from autoapply.security.untrusted import UntrustedText


class Matcher:
    def __init__(self, llm: LlmRouter, catalog: BlockCatalog, threshold: float):
        self.llm = llm
        self.catalog = catalog
        self.threshold = threshold

    def hard_reject(self, vacancy: Vacancy, profile: Profile) -> MatchDecision | None:
        blob = f"{vacancy.title} {vacancy.company} {vacancy.description}".lower()
        for keyword in profile.exclude_keywords:
            if keyword.lower() in blob:
                return MatchDecision(
                    score=0.05,
                    should_apply=False,
                    reasons=[f"Excluded by keyword: {keyword}"],
                    missing_requirements=[],
                    selected_block_ids=[],
                    cover_letter_fields={},
                )
        return None

    async def score(self, vacancy: Vacancy, profile: Profile) -> MatchDecision:
        rejected = self.hard_reject(vacancy, profile)
        if rejected is not None:
            return rejected

        untrusted = UntrustedText(
            source=f"vacancy:{vacancy.portal.value}:{vacancy.external_id}",
            raw=(
                f"title={vacancy.title}\ncompany={vacancy.company}\n"
                f"location={vacancy.location}\nurl={vacancy.url}\n\n"
                f"{vacancy.description}"
            ),
        )
        trusted = trusted_match_context(
            profile.model_dump_json(),
            json.dumps(self.catalog.as_prompt_catalog(), ensure_ascii=False),
            self.threshold,
        )
        messages = build_messages(
            user_task=MATCH_TASK,
            untrusted_data=untrusted.as_delimited_data(),
            trusted_context=trusted,
        )
        response = await self.llm.complete_json(
            LlmRequest(
                messages=messages,
                schema_name="match",
                schema=MatchLlmOutput.model_json_schema(),
            )
        )
        parsed = MatchLlmOutput.model_validate(response.data)
        selected = self.catalog.filter_allowed(parsed.selected_block_ids)
        should = parsed.should_apply and parsed.score >= self.threshold
        return MatchDecision(
            score=parsed.score,
            should_apply=should,
            reasons=parsed.reasons,
            missing_requirements=parsed.missing_requirements,
            selected_block_ids=selected,
            cover_letter_fields=parsed.cover_letter_fields.model_dump(),
        )
