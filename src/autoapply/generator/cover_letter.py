from __future__ import annotations

import re
from pathlib import Path
from string import Template

from autoapply.domain.models import ApplicationPackage, MatchDecision, Profile
from autoapply.errors import TemplateError
from autoapply.generator.cv_assembler import CvAssembler

ALLOWED_PLACEHOLDERS = {
    "recruiter_name",
    "role",
    "company",
    "matching_skills_sentence",
    "availability_window",
    "candidate_name",
    "dedicated_email",
}

_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")


class CoverLetterRenderer:
    def __init__(self, template_text: str):
        self.template_text = template_text
        self.required = set(_PLACEHOLDER_RE.findall(template_text))
        unknown = self.required - ALLOWED_PLACEHOLDERS
        if unknown:
            raise TemplateError(f"Cover letter template has unknown placeholders: {sorted(unknown)}")

    @classmethod
    def from_path(cls, path: Path) -> "CoverLetterRenderer":
        return cls(path.read_text(encoding="utf-8"))

    def render(self, fields: dict[str, str], profile: Profile) -> tuple[str, str]:
        values = {
            "recruiter_name": "equipo de reclutamiento",
            "availability_window": "días hábiles, 9 a 18 hs",
            "candidate_name": profile.full_name,
            "dedicated_email": profile.dedicated_email,
        }
        for key, value in fields.items():
            if key in ALLOWED_PLACEHOLDERS and isinstance(value, str) and value.strip():
                values[key] = value.strip()
        missing = self.required - values.keys()
        if missing:
            raise TemplateError(f"Missing cover letter fields: {sorted(missing)}")
        # Use safe_substitute so a model cannot inject new $-style templates.
        rendered = Template(self._to_dollar_template(self.template_text)).safe_substitute(values)
        subject, _, body = rendered.partition("\n")
        subject = subject.replace("Asunto:", "", 1).strip()
        return subject, body.strip() + "\n"

    @staticmethod
    def _to_dollar_template(text: str) -> str:
        return _PLACEHOLDER_RE.sub(r"${\1}", text)


class ApplicationGenerator:
    def __init__(self, assembler: CvAssembler, renderer: CoverLetterRenderer):
        self.assembler = assembler
        self.renderer = renderer

    def build(self, decision: MatchDecision, profile: Profile) -> ApplicationPackage:
        cv_text = self.assembler.assemble(decision.selected_block_ids)
        subject, letter = self.renderer.render(decision.cover_letter_fields, profile)
        return ApplicationPackage(
            cv_text=cv_text,
            cover_letter=letter,
            cover_subject=subject,
            selected_block_ids=decision.selected_block_ids,
        )
