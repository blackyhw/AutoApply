from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)
BLOCKED_EMAIL_DOMAINS = (
    "linkedin.com",
    "indeed.com",
    "computrabajo.com",
    "sentry.io",
    "example.com",
    "w3.org",
    "schema.org",
)


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def text_of(node) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def strip_html(html: str) -> str:
    cleaned = soup(html).get_text("\n", strip=True)
    return unescape(re.sub(r"\n{3,}", "\n\n", cleaned)).strip()


def extract_apply_email(text: str) -> str | None:
    for match in EMAIL_RE.findall(text or ""):
        domain = match.split("@", 1)[-1].lower()
        if any(domain == blocked or domain.endswith("." + blocked) for blocked in BLOCKED_EMAIL_DOMAINS):
            continue
        return match
    return None


def absolute_url(base: str, href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href.split("#", 1)[0]
    if href.startswith("//"):
        return "https:" + href.split("#", 1)[0]
    return base.rstrip("/") + "/" + href.lstrip("/").split("#", 1)[0]
