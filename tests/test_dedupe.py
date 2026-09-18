from autoapply.collectors.base import fingerprint
from autoapply.collectors.dedupe import Deduper
from autoapply.domain.enums import Portal
from autoapply.domain.models import Vacancy
from autoapply.persistence.repositories import Repository


def _vacancy(external_id: str, title: str = "Python Dev") -> Vacancy:
    return Vacancy(
        portal=Portal.FILE_FEED,
        external_id=external_id,
        title=title,
        company="Acme",
        location="BA",
        url=f"https://example.com/{external_id}",
        description="Python",
    )


def test_fingerprint_is_stable():
    a = _vacancy("abc")
    b = _vacancy("ABC")
    assert fingerprint(a) == fingerprint(b)


def test_deduper_skips_seen_and_duplicates(repo: Repository):
    first = _vacancy("job-1")
    repo.upsert_vacancy(first, fingerprint(first))
    batch = [first, _vacancy("job-1"), _vacancy("job-2")]
    fresh = Deduper(repo).unseen(batch)
    assert [item[0].external_id for item in fresh] == ["job-2"]
