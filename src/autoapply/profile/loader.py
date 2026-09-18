from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from autoapply.domain.models import Profile
from autoapply.errors import ConfigurationError


def load_profile(path: Path) -> Profile:
    candidate = path if path.exists() else _example_path(path)
    if not candidate.exists():
        raise ConfigurationError(f"Profile file not found: {path}")
    payload: dict[str, Any] = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
    identity = payload.get("identity", {})
    target = payload.get("target", {})
    constraints = payload.get("constraints", {})
    return Profile(
        full_name=identity.get("full_name", ""),
        headline=identity.get("headline", ""),
        location=identity.get("location", ""),
        years_experience=int(identity.get("years_experience") or 0),
        dedicated_email=identity.get("dedicated_email", "jobs-agent@example.com"),
        phone=identity.get("phone", ""),
        links=identity.get("links") or {},
        target_roles=target.get("roles") or [],
        keywords=target.get("keywords") or [],
        locations=target.get("locations") or [],
        work_modes=target.get("work_modes") or [],
        seniority=target.get("seniority") or [],
        exclude_keywords=constraints.get("exclude_keywords") or [],
        languages=target.get("languages") or [],
    )


def _example_path(path: Path) -> Path:
    if path.name.endswith(".yaml"):
        return path.with_name(path.stem + ".example.yaml")
    return path
