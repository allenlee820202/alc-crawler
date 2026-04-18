"""Playwright-backed HttpFetcher for JS-heavy pages.

Use this only when an httpx GET cannot render the data we need. It launches
a headless Chromium per request for simplicity; can be optimized to a
shared browser context later.
"""
from __future__ import annotations

from playwright.async_api import async_playwright

from alc_crawler.application.ports.fetcher import FetchResult

_DEFAULT_UA = "alc-crawler/0.1 (+https://github.com/anomalyco)"


class PlaywrightFetcher:
    def __init__(
        self,
        *,
        timeout_ms: int = 20_000,
        wait_until: str = "networkidle",
        user_agent: str = _DEFAULT_UA,
    ) -> None:
        self._timeout_ms = timeout_ms
        self._wait_until = wait_until
        self._user_agent = user_agent

    async def get(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> FetchResult:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                context = await browser.new_context(
                    user_agent=self._user_agent,
                    extra_http_headers=headers or {},
                )
                page = await context.new_page()
                response = await page.goto(
                    url,
                    timeout=self._timeout_ms,
                    wait_until=self._wait_until,  # type: ignore[arg-type]
                )
                # data: URLs return None response; treat as 200 with the page content.
                status = response.status if response else 200
                body = await page.content()
                return FetchResult(url=url, status=status, body=body)
            finally:
                await browser.close()
