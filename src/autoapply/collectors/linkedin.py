from __future__ import annotations

from datetime import datetime
from urllib.parse import quote_plus

from autoapply.collectors.http import PoliteClient
from autoapply.collectors.parseutil import extract_apply_email, soup, strip_html, text_of
from autoapply.collectors.queries import SearchQuery, search_queries
from autoapply.domain.enums import Portal
from autoapply.domain.models import Profile, Vacancy
from autoapply.errors import CollectorError
from autoapply.logging import get_logger

log = get_logger("collectors.linkedin")

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"


class LinkedInCollector:
    name = "linkedin"

    def __init__(
        self,
        client: PoliteClient | None = None,
        *,
        max_per_portal: int = 15,
        fetch_details: bool = True,
        pages: int = 2,
    ):
        self.client = client or PoliteClient()
        self.max_per_portal = max_per_portal
        self.fetch_details = fetch_details
        self.pages = pages

    async def collect(self, profile: Profile | None = None) -> list[Vacancy]:
        profile = profile or Profile(full_name="x", dedicated_email="jobs-agent@example.com")
        vacancies: list[Vacancy] = []
        seen: set[str] = set()
        try:
            for query in search_queries(profile):
                for start in range(0, self.pages * 10, 10):
                    html = await self.client.get_text(_search_url(query, start))
                    for vacancy in parse_linkedin_search(html):
                        if vacancy.external_id in seen:
                            continue
                        seen.add(vacancy.external_id)
                        vacancies.append(vacancy)
                        if len(vacancies) >= self.max_per_portal:
                            break
                    if len(vacancies) >= self.max_per_portal:
                        break
                if len(vacancies) >= self.max_per_portal:
                    break
        except CollectorError as exc:
            if vacancies:
                log.warning("linkedin_partial", error=str(exc), count=len(vacancies))
            else:
                raise

        if self.fetch_details:
            detailed: list[Vacancy] = []
            for vacancy in vacancies:
                try:
                    html = await self.client.get_text(DETAIL_URL.format(job_id=vacancy.external_id))
                    detailed.append(merge_linkedin_detail(vacancy, html))
                except CollectorError as exc:
                    log.warning("linkedin_detail_skipped", job_id=vacancy.external_id, error=str(exc))
                    detailed.append(vacancy)
            return detailed
        return vacancies


def _search_url(query: SearchQuery, start: int) -> str:
    location = query.location or "Argentina"
    return (
        f"{SEARCH_URL}?keywords={quote_plus(query.keywords)}"
        f"&location={quote_plus(location)}&start={start}"
    )


def parse_linkedin_search(html: str) -> list[Vacancy]:
    page = soup(html)
    vacancies: list[Vacancy] = []
    for card in page.select("[data-entity-urn*='jobPosting']"):
        urn = card.get("data-entity-urn") or ""
        job_id = urn.rsplit(":", 1)[-1].strip()
        if not job_id.isdigit():
            continue
        title = text_of(card.select_one(".base-search-card__title"))
        company = text_of(card.select_one(".base-search-card__subtitle"))
        location = text_of(card.select_one(".job-search-card__location"))
        link = card.select_one("a.base-card__full-link") or card.select_one("a[href*='/jobs/view/']")
        href = (link.get("href") if link else "") or f"https://www.linkedin.com/jobs/view/{job_id}"
        href = href.split("?")[0]
        posted = None
        time_el = card.select_one("time")
        if time_el and time_el.get("datetime"):
            try:
                posted = datetime.fromisoformat(time_el["datetime"])
            except ValueError:
                posted = None
        vacancies.append(
            Vacancy(
                portal=Portal.LINKEDIN,
                external_id=job_id,
                title=title or f"LinkedIn {job_id}",
                company=company,
                location=location,
                url=href,
                description="",
                posted_at=posted,
            )
        )
    return vacancies


def merge_linkedin_detail(vacancy: Vacancy, html: str) -> Vacancy:
    page = soup(html)
    title = text_of(page.select_one(".top-card-layout__title, h2.topcard__title")) or vacancy.title
    company = text_of(page.select_one(".topcard__org-name-link, .topcard__flavor")) or vacancy.company
    markup = page.select_one(".show-more-less-html__markup")
    description = strip_html(str(markup)) if markup else strip_html(html)
    apply_url = None
    apply_link = page.select_one("a[href*='linkedin.com/jobs/view/']")
    if apply_link and apply_link.get("href"):
        apply_url = apply_link["href"].split("?")[0]
    email = extract_apply_email(description)
    return vacancy.model_copy(
        update={
            "title": title,
            "company": company,
            "description": description,
            "apply_email": email,
            "apply_url": apply_url or vacancy.url,
        }
    )
