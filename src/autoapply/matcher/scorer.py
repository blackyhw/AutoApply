from __future__ import annotations

import re

from autoapply.domain.models import MatchDecision, Profile, Vacancy
from autoapply.generator.blocks import BlockCatalog
from autoapply.llm.schemas import CoverLetterFields

_TOKEN_RE = re.compile(r"[a-záéíóúñü+#.]{2,}", re.IGNORECASE)
_STOP = {
    "the", "and", "for", "with", "de", "del", "la", "el", "en", "los", "las",
    "un", "una", "y", "o", "to", "of", "a", "en", "para", "con", "senior",
    "semi", "junior", "sr", "ssr",
}


class Matcher:
    """Keyword overlap only. Scraping/matching never calls an LLM."""

    def __init__(self, catalog: BlockCatalog, threshold: float):
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

        blob = f"{vacancy.title}\n{vacancy.company}\n{vacancy.location}\n{vacancy.description}"
        wanted = _phrases(profile.keywords + profile.target_roles)
        if not wanted:
            wanted = _phrases([profile.headline] if profile.headline else ["developer"])
        hits = [phrase for phrase in wanted if phrase in blob.lower()]
        token_wanted = _tokens(" ".join(wanted))
        token_hits = _tokens(blob) & token_wanted
        phrase_score = len(hits) / max(len(wanted), 1)
        token_score = len(token_hits) / max(len(token_wanted), 1)
        score = min(1.0, 0.2 + 0.5 * phrase_score + 0.3 * token_score)
        locations = [item.lower() for item in profile.locations + [profile.location] if item]
        if any(loc in blob.lower() for loc in locations):
            score = min(1.0, score + 0.08)
        if any(mode.lower() in blob.lower() for mode in profile.work_modes):
            score = min(1.0, score + 0.04)

        selected = self.catalog.filter_allowed(
            [
                block.id
                for block in self.catalog.blocks()
                if any(tag.lower() in blob.lower() for tag in block.tags)
            ]
        )
        missing = [phrase for phrase in wanted if phrase not in blob.lower()][:6]
        fields = CoverLetterFields(
            role=vacancy.title,
            company=vacancy.company or "la empresa",
            matching_skills_sentence=_skills_sentence(hits or list(token_hits)),
            candidate_name=profile.full_name,
            dedicated_email=profile.dedicated_email,
        )
        should = score >= self.threshold
        reasons = [
            f"phrase_hits={len(hits)}/{len(wanted)}",
            f"token_hits={len(token_hits)}/{len(token_wanted)}",
        ]
        return MatchDecision(
            score=round(score, 3),
            should_apply=should,
            reasons=reasons,
            missing_requirements=missing,
            selected_block_ids=selected,
            cover_letter_fields=fields.model_dump(),
        )


def _phrases(values: list[str]) -> list[str]:
    out = []
    for value in values:
        item = value.strip().lower()
        if item:
            out.append(item)
    return out


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(text) if token.lower() not in _STOP}


def _skills_sentence(hits: list[str]) -> str:
    if not hits:
        return "Mi perfil se alinea con el rol publicado."
    shown = ", ".join(hits[:6])
    return f"Mi perfil cubre {shown}."
