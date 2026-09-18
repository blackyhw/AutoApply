from __future__ import annotations

from dataclasses import dataclass

from autoapply.domain.models import Profile


@dataclass(frozen=True, slots=True)
class SearchQuery:
    keywords: str
    location: str


def search_queries(profile: Profile, *, max_queries: int = 4) -> list[SearchQuery]:
    """Build a small set of search queries from the trusted profile."""
    terms: list[str] = []
    for role in profile.target_roles:
        if role.strip():
            terms.append(role.strip())
    if profile.keywords:
        terms.append(" ".join(profile.keywords[:4]))
    if not terms:
        terms = [profile.headline or "developer"]

    locations = [loc for loc in profile.locations if loc.strip()]
    if profile.location and profile.location not in locations:
        locations.insert(0, profile.location)
    if not locations:
        locations = [""]

    queries: list[SearchQuery] = []
    seen: set[tuple[str, str]] = set()
    for term in terms:
        for location in locations[:2]:
            key = (term.lower(), location.lower())
            if key in seen:
                continue
            seen.add(key)
            queries.append(SearchQuery(keywords=term, location=location))
            if len(queries) >= max_queries:
                return queries
    return queries


def slugify(value: str) -> str:
    allowed = []
    for ch in value.lower().strip():
        if ch.isalnum():
            allowed.append(ch)
        elif ch in {" ", "-", "_"}:
            allowed.append("-")
    slug = "".join(allowed)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "empleo"
