"""Tests for the httpx-backed HttpFetcher adapter."""
from __future__ import annotations

import httpx
import pytest
import respx

from alc_crawler.infrastructure.http.httpx_fetcher import HttpxFetcher

pytestmark = pytest.mark.integration


@respx.mock
async def test_get_returns_status_and_body() -> None:
    respx.get("https://example.com/page").mock(
        return_value=httpx.Response(200, text="<html>hi</html>")
    )
    fetcher = HttpxFetcher(timeout=2.0)

    result = await fetcher.get("https://example.com/page")

    assert result.status == 200
    assert result.body == "<html>hi</html>"
    assert result.url == "https://example.com/page"


@respx.mock
async def test_default_user_agent_is_set() -> None:
    route = respx.get("https://example.com/").mock(return_value=httpx.Response(200, text=""))
    fetcher = HttpxFetcher()

    await fetcher.get("https://example.com/")

    sent = route.calls.last.request
    assert "alc-crawler" in sent.headers["user-agent"].lower()


@respx.mock
async def test_custom_headers_override_defaults() -> None:
    route = respx.get("https://example.com/").mock(return_value=httpx.Response(200, text=""))
    fetcher = HttpxFetcher()

    await fetcher.get("https://example.com/", headers={"User-Agent": "custom"})

    assert route.calls.last.request.headers["user-agent"] == "custom"


@respx.mock
async def test_retries_on_5xx_then_succeeds() -> None:
    route = respx.get("https://example.com/").mock(
        side_effect=[
            httpx.Response(503, text=""),
            httpx.Response(200, text="ok"),
        ]
    )
    fetcher = HttpxFetcher(max_retries=2, retry_backoff=0)

    result = await fetcher.get("https://example.com/")

    assert result.status == 200
    assert result.body == "ok"
    assert route.call_count == 2


@respx.mock
async def test_raises_after_exhausting_retries() -> None:
    respx.get("https://example.com/").mock(return_value=httpx.Response(503, text=""))
    fetcher = HttpxFetcher(max_retries=2, retry_backoff=0)

    with pytest.raises(httpx.HTTPStatusError):
        await fetcher.get("https://example.com/")


def test_verify_defaults_to_true() -> None:
    fetcher = HttpxFetcher()
    assert fetcher.verify is True


def test_verify_can_be_disabled() -> None:
    fetcher = HttpxFetcher(verify=False)
    assert fetcher.verify is False
