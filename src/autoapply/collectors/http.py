from __future__ import annotations

import asyncio
from typing import Any

import httpx

from autoapply.errors import CollectorError
from autoapply.logging import get_logger

log = get_logger("collectors.http")

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}


class PoliteClient:
    """Shared HTTP client with a delay between requests. No anti-bot bypass."""

    def __init__(self, delay_seconds: float = 1.0, timeout: float = 25.0):
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def get_text(self, url: str, *, headers: dict[str, str] | None = None) -> str:
        await self._throttle()
        merged = {**BROWSER_HEADERS, **(headers or {})}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=merged)
        except httpx.HTTPError as exc:
            raise CollectorError(f"HTTP error fetching {url}: {exc}") from exc
        if response.status_code in {401, 403, 429}:
            raise CollectorError(
                f"{url} returned {response.status_code}. The portal blocked this VM; "
                "retry later or use a stored browser session. No bypass is attempted."
            )
        if response.status_code >= 400:
            raise CollectorError(f"{url} returned {response.status_code}")
        return response.text

    async def _throttle(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            wait = self.delay_seconds - (now - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = loop.time()
