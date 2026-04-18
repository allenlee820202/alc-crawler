"""Playwright-based HttpFetcher for JS-heavy pages.

Tested behavior here is the *integration* with Playwright. Skipped if
Playwright browsers aren't installed locally (CI can install them).
"""
from __future__ import annotations

import asyncio

import pytest

from alc_crawler.infrastructure.browser.playwright_fetcher import PlaywrightFetcher


def _browsers_installed() -> bool:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return False

    async def _check() -> bool:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                await browser.close()
                return True
        except Exception:
            return False

    return asyncio.run(_check())


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _browsers_installed(),
        reason="playwright browsers not installed (run `uv run playwright install chromium`)",
    ),
]


async def test_fetch_static_data_url() -> None:
    fetcher = PlaywrightFetcher()
    html = "<html><body><h1>hello</h1></body></html>"
    data_url = f"data:text/html;charset=utf-8,{html}"

    result = await fetcher.get(data_url)

    assert result.status == 200
    assert "hello" in result.body
