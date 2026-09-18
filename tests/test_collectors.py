from pathlib import Path

import pytest

from autoapply.collectors.computrabajo import parse_computrabajo_search, merge_computrabajo_detail
from autoapply.collectors.indeed import IndeedCollector, parse_indeed_search
from autoapply.collectors.linkedin import parse_linkedin_search, merge_linkedin_detail
from autoapply.collectors.parseutil import extract_apply_email
from autoapply.collectors.queries import search_queries, slugify
from autoapply.domain.enums import Portal
from autoapply.domain.models import Profile
from autoapply.errors import CollectorError
from autoapply.profile.loader import load_profile

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def test_search_queries_from_profile():
    profile = load_profile(ROOT / "config" / "profile.example.yaml")
    queries = search_queries(profile)
    assert queries
    assert any("python" in q.keywords.lower() or "backend" in q.keywords.lower() for q in queries)
    assert slugify("Python Developer") == "python-developer"


def test_extract_apply_email_ignores_portal_domains():
    text = "Apply at recruiter@acme.com or privacy@linkedin.com"
    assert extract_apply_email(text) == "recruiter@acme.com"


def test_parse_linkedin_search_fixture():
    html = (FIXTURES / "linkedin_search.html").read_text(encoding="utf-8")
    jobs = parse_linkedin_search(html)
    assert len(jobs) >= 2
    assert jobs[0].portal is Portal.LINKEDIN
    assert jobs[0].external_id.isdigit()
    assert jobs[0].title
    assert "linkedin.com/jobs/view/" in jobs[0].url


def test_parse_linkedin_detail_fixture():
    search_html = (FIXTURES / "linkedin_search.html").read_text(encoding="utf-8")
    detail_html = (FIXTURES / "linkedin_detail.html").read_text(encoding="utf-8")
    vacancy = parse_linkedin_search(search_html)[0]
    merged = merge_linkedin_detail(vacancy, detail_html)
    assert "Satellogic" in merged.description or "Python" in merged.description
    assert merged.apply_email is None or "@" in merged.apply_email


def test_parse_computrabajo_search_fixture():
    html = (FIXTURES / "computrabajo_search.html").read_text(encoding="utf-8")
    jobs = parse_computrabajo_search(html)
    assert len(jobs) >= 1
    assert jobs[0].portal is Portal.COMPUTRABAJO
    assert jobs[0].external_id
    assert "ofertas-de-trabajo" in jobs[0].url
    assert jobs[0].company


def test_parse_computrabajo_detail_fixture():
    html = (FIXTURES / "computrabajo_search.html").read_text(encoding="utf-8")
    detail = (FIXTURES / "computrabajo_detail.html").read_text(encoding="utf-8")
    vacancy = parse_computrabajo_search(html)[0]
    merged = merge_computrabajo_detail(vacancy, detail)
    assert "Python" in merged.description or "python" in merged.description.lower()


def test_parse_indeed_search_fixture():
    html = (FIXTURES / "indeed_search.html").read_text(encoding="utf-8")
    jobs = parse_indeed_search(html)
    assert [job.external_id for job in jobs] == ["abc123xyz", "def456uvw"]
    assert jobs[0].company == "Acme Salud"


class _BlockedClient:
    async def get_text(self, url: str) -> str:
        raise CollectorError("403")


@pytest.mark.asyncio
async def test_indeed_falls_back_to_browser_when_http_blocked():
    html = (FIXTURES / "indeed_search.html").read_text(encoding="utf-8")
    calls: list[str] = []

    async def fake_browser(url: str) -> str:
        calls.append(url)
        return html

    profile = Profile(
        full_name="Ada",
        dedicated_email="jobs-agent@example.com",
        target_roles=["Python Developer"],
        keywords=["python"],
        locations=["Buenos Aires"],
    )
    collector = IndeedCollector(
        client=_BlockedClient(),
        max_per_portal=5,
        browser_fetch=fake_browser,
    )
    jobs = await collector.collect(profile)
    assert calls
    assert all("ar.indeed.com/jobs" in url for url in calls)
    assert [job.external_id for job in jobs] == ["abc123xyz", "def456uvw"]
    assert jobs[0].company == "Acme Salud"
