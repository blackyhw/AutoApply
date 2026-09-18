from __future__ import annotations

from pathlib import Path

from autoapply.errors import CollectorError
from autoapply.logging import get_logger

log = get_logger("collectors.browser")

_WALL_MARKERS = (
    "captcha",
    "verify you are human",
    "cf-challenge",
    "attention required",
    "enable javascript and cookies",
)


def assert_public_html(html: str, url: str) -> None:
    """Stop on a captcha/challenge page. A Sign in button is fine if jobs rendered."""
    if "data-jk" in html or "job_seen_beacon" in html:
        return
    lowered = html.lower()
    if any(marker in lowered for marker in _WALL_MARKERS):
        raise CollectorError(f"Portal showed a captcha/challenge for {url}")
    if "indeed" in lowered and "sign in" in lowered and len(html) < 8000:
        raise CollectorError(f"Indeed showed a login wall for {url}")


class PublicPageFetcher:
    """One Chromium instance for several public search URLs. Not an anti-bot bypass."""

    def __init__(
        self,
        *,
        storage_state: Path | None = None,
        timeout_ms: int = 45000,
    ):
        self.storage_state = storage_state
        self.timeout_ms = timeout_ms
        self._playwright = None
        self._browser = None
        self._context = None

    async def __aenter__(self) -> "PublicPageFetcher":
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise CollectorError("playwright is not installed") from exc
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            kwargs: dict = {
                "locale": "es-AR",
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
            }
            if self.storage_state and self.storage_state.exists():
                kwargs["storage_state"] = str(self.storage_state)
            self._context = await self._browser.new_context(**kwargs)
        except CollectorError:
            await self._close()
            raise
        except Exception as exc:
            await self._close()
            raise _wrap_playwright_error(exc, url="chromium") from exc
        return self

    async def fetch(self, url: str) -> str:
        if self._context is None:
            raise CollectorError("PublicPageFetcher must be used as an async context manager")
        try:
            page = await self._context.new_page()
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                status = response.status if response else 0
                if status in {401, 403, 429}:
                    raise CollectorError(f"Playwright got HTTP {status} for {url}")
                await page.wait_for_timeout(1500)
                html = await page.content()
                title = await page.title()
            finally:
                await page.close()
        except CollectorError:
            raise
        except Exception as exc:
            raise _wrap_playwright_error(exc, url=url) from exc
        assert_public_html(html, url)
        log.info("playwright_fetch_ok", url=url, status=status, title=title, bytes=len(html))
        return html

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._close()

    async def _close(self) -> None:
        for closer in (self._context, self._browser, self._playwright):
            if closer is None:
                continue
            try:
                if hasattr(closer, "close"):
                    await closer.close()
                elif hasattr(closer, "stop"):
                    await closer.stop()
            except Exception:
                pass
        self._context = None
        self._browser = None
        self._playwright = None


async def fetch_html_with_playwright(
    url: str,
    *,
    storage_state: Path | None = None,
    timeout_ms: int = 45000,
) -> str:
    """Fetch a public search page with Chromium when plain HTTP is blocked."""
    async with PublicPageFetcher(storage_state=storage_state, timeout_ms=timeout_ms) as fetcher:
        return await fetcher.fetch(url)


def _wrap_playwright_error(exc: Exception, *, url: str) -> CollectorError:
    message = str(exc)
    if "Executable doesn't exist" in message:
        return CollectorError(
            "Playwright Chromium is missing. On the VM run: playwright install chromium"
        )
    return CollectorError(f"Playwright fetch failed for {url}: {exc}")
