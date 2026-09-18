from __future__ import annotations

from urllib.parse import quote_plus
from xml.etree import ElementTree

from autoapply.collectors.http import PoliteClient
from autoapply.collectors.parseutil import extract_apply_email, soup, text_of
from autoapply.collectors.queries import search_queries
from autoapply.domain.enums import Portal
from autoapply.domain.models import Profile, Vacancy
from autoapply.errors import CollectorError
from autoapply.logging import get_logger

log = get_logger("collectors.indeed")


class IndeedCollector:
    name = "indeed"

    def __init__(
        self,
        client: PoliteClient | None = None,
        *,
        country_host: str = "ar.indeed.com",
        max_per_portal: int = 15,
    ):
        self.client = client or PoliteClient()
        self.country_host = country_host
        self.max_per_portal = max_per_portal

    async def collect(self, profile: Profile | None = None) -> list[Vacancy]:
        profile = profile or Profile(full_name="x", dedicated_email="jobs-agent@example.com")
        vacancies: list[Vacancy] = []
        seen: set[str] = set()
        last_error: CollectorError | None = None
        for query in search_queries(profile):
            location = query.location or "Argentina"
            rss = (
                f"https://{self.country_host}/rss?q={quote_plus(query.keywords)}"
                f"&l={quote_plus(location)}"
            )
            html_url = (
                f"https://{self.country_host}/jobs?q={quote_plus(query.keywords)}"
                f"&l={quote_plus(location)}&sort=date"
            )
            batch: list[Vacancy] = []
            try:
                payload = await self.client.get_text(rss)
                batch = parse_indeed_rss(payload)
            except CollectorError as exc:
                last_error = exc
                log.info("indeed_rss_unavailable", error=str(exc))
                try:
                    payload = await self.client.get_text(html_url)
                    batch = parse_indeed_search(payload, base=f"https://{self.country_host}")
                except CollectorError as exc2:
                    last_error = exc2
            for vacancy in batch:
                if vacancy.external_id in seen:
                    continue
                seen.add(vacancy.external_id)
                vacancies.append(vacancy)
                if len(vacancies) >= self.max_per_portal:
                    return vacancies
        if not vacancies and last_error:
            raise last_error
        return vacancies


def parse_indeed_search(html: str, base: str = "https://ar.indeed.com") -> list[Vacancy]:
    page = soup(html)
    vacancies: list[Vacancy] = []
    cards = page.select(".job_seen_beacon") or page.select("[data-jk]")
    for card in cards:
        job_id = card.get("data-jk")
        link = card.select_one("a[data-jk], a[href*='jk=']") if card.name != "a" else card
        if not job_id and link is not None:
            job_id = link.get("data-jk")
        if not job_id:
            continue
        title_node = card.select_one("h2, .jobTitle") or link
        company = text_of(card.select_one("[data-testid='company-name'], .companyName"))
        location = text_of(card.select_one("[data-testid='text-location'], .companyLocation"))
        href = f"{base}/viewjob?jk={job_id}"
        if link is not None and link.get("href"):
            href = link["href"]
            if href.startswith("/"):
                href = base.rstrip("/") + href
        vacancies.append(
            Vacancy(
                portal=Portal.INDEED,
                external_id=job_id,
                title=text_of(title_node) or f"Indeed {job_id}",
                company=company,
                location=location,
                url=href.split("&", 1)[0],
                description=text_of(card),
                apply_email=extract_apply_email(text_of(card)),
            )
        )
    return vacancies


def parse_indeed_rss(payload: str) -> list[Vacancy]:
    if "<rss" not in payload[:400].lower() and "<rss" not in payload.lower():
        raise CollectorError("Indeed RSS payload is not XML")
    root = ElementTree.fromstring(payload)
    items = root.findall(".//item")
    vacancies: list[Vacancy] = []
    for item in items:
        link = (item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        job_id = ""
        if "jk=" in link:
            job_id = link.split("jk=", 1)[-1].split("&", 1)[0]
        if not job_id:
            continue
        company = ""
        if " - " in title:
            title, company = title.rsplit(" - ", 1)
        vacancies.append(
            Vacancy(
                portal=Portal.INDEED,
                external_id=job_id,
                title=title,
                company=company,
                url=link,
                description=description,
                apply_email=extract_apply_email(description),
            )
        )
    return vacancies
