from __future__ import annotations

from autoapply.collectors.http import PoliteClient
from autoapply.collectors.parseutil import absolute_url, extract_apply_email, soup, strip_html, text_of
from autoapply.collectors.queries import search_queries, slugify
from autoapply.domain.enums import Portal
from autoapply.domain.models import Profile, Vacancy
from autoapply.errors import CollectorError
from autoapply.logging import get_logger

log = get_logger("collectors.computrabajo")

DEFAULT_BASE = "https://www.computrabajo.com.ar"


class ComputrabajoCollector:
    name = "computrabajo"

    def __init__(
        self,
        client: PoliteClient | None = None,
        *,
        base_url: str = DEFAULT_BASE,
        max_per_portal: int = 15,
        fetch_details: bool = True,
        pages: int = 1,
    ):
        self.client = client or PoliteClient()
        self.base_url = base_url.rstrip("/")
        self.max_per_portal = max_per_portal
        self.fetch_details = fetch_details
        self.pages = pages

    async def collect(self, profile: Profile | None = None) -> list[Vacancy]:
        profile = profile or Profile(full_name="x", dedicated_email="jobs-agent@example.com")
        vacancies: list[Vacancy] = []
        seen: set[str] = set()
        queries = search_queries(profile)
        try:
            for query in queries:
                slug = slugify(query.keywords.split()[0] if query.keywords else "python")
                for page_number in range(1, self.pages + 1):
                    url = f"{self.base_url}/trabajo-de-{slug}"
                    if page_number > 1:
                        url += f"?p={page_number}"
                    html = await self.client.get_text(url)
                    for vacancy in parse_computrabajo_search(html, self.base_url):
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
                log.warning("computrabajo_partial", error=str(exc), count=len(vacancies))
            else:
                raise

        if self.fetch_details:
            detailed: list[Vacancy] = []
            for vacancy in vacancies:
                try:
                    html = await self.client.get_text(vacancy.url)
                    detailed.append(merge_computrabajo_detail(vacancy, html))
                except CollectorError as exc:
                    log.warning("computrabajo_detail_skipped", job_id=vacancy.external_id, error=str(exc))
                    detailed.append(vacancy)
            return detailed
        return vacancies


def parse_computrabajo_search(html: str, base_url: str = DEFAULT_BASE) -> list[Vacancy]:
    page = soup(html)
    vacancies: list[Vacancy] = []
    for article in page.select("article.box_offer"):
        job_id = (article.get("data-id") or article.get("id") or "").strip()
        link = article.select_one("a.js-o-link")
        if not job_id or link is None:
            continue
        href = absolute_url(base_url, link.get("href") or "")
        company = text_of(article.select_one("[offer-grid-article-company-url]"))
        location = ""
        for paragraph in article.select("p.fs16"):
            txt = text_of(paragraph)
            if company and company in txt:
                continue
            if txt:
                location = txt
                break
        apply_node = article.select_one("[data-href-offer-apply]")
        apply_url = apply_node.get("data-href-offer-apply") if apply_node else None
        vacancies.append(
            Vacancy(
                portal=Portal.COMPUTRABAJO,
                external_id=job_id,
                title=text_of(link) or f"Computrabajo {job_id}",
                company=company,
                location=location,
                url=href,
                description="",
                apply_url=apply_url,
            )
        )
    return vacancies


def merge_computrabajo_detail(vacancy: Vacancy, html: str) -> Vacancy:
    page = soup(html)
    heading = page.select_one("h1, h2.fs24, .box_offer h1")
    title = text_of(heading) or vacancy.title
    desc_heading = page.find(string=lambda value: value and "Descripción de la oferta" in value)
    description = vacancy.description
    if desc_heading and desc_heading.parent:
        block = desc_heading.find_parent("article") or desc_heading.find_parent("div")
        if block:
            description = strip_html(str(block))
    if not description:
        description = strip_html(html)[:8000]
    return vacancy.model_copy(
        update={
            "title": title,
            "description": description,
            "apply_email": extract_apply_email(description),
        }
    )
