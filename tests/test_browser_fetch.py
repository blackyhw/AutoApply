import pytest

from autoapply.collectors.browser_fetch import assert_public_html
from autoapply.errors import CollectorError


def test_assert_public_html_allows_job_cards_even_with_sign_in():
    html = """<html><body>
    <a href="/signin">Sign in</a>
    <div class="job_seen_beacon" data-jk="abc123xyz">Python</div>
    </body></html>"""
    assert_public_html(html, "https://ar.indeed.com/jobs")


def test_assert_public_html_stops_on_captcha_without_jobs():
    with pytest.raises(CollectorError, match="captcha"):
        assert_public_html("<html>please complete the captcha</html>", "https://ar.indeed.com/jobs")
