"""Unit tests for Site591CrawlService multi-page behavior."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import pytest

from alc_crawler.adapters.sites.site_591.crawl_service import Site591CrawlService
from alc_crawler.adapters.sites.site_591.search_urls import Site591SearchUrls
from alc_crawler.application.ports.fetcher import FetchResult
from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import ListingId


def _api_body(items: list[dict[str, Any]]) -> str:
    return json.dumps({"status": 1, "data": {"house_list": items}})


def _item(house_id: int) -> dict[str, Any]:
    return {
        "houseid": house_id,
        "title": f"t{house_id}",
        "region_name": "台北市",
        "section_name": "內湖區",
        "address": "x",
        "price": 1000,
    }


class _FakeSession:
    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, Mapping[str, str] | None]] = []

    async def get(self, url: str, *, headers: Mapping[str, str] | None = None) -> FetchResult:
        self.requests.append((url, headers))
        body = self._responses.get(url, "")
        return FetchResult(status=200, body=body, url=url)


class _FakeFetcher:
    def __init__(self, responses: dict[str, str]) -> None:
        self.session_obj = _FakeSession(responses)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[_FakeSession]:
        yield self.session_obj


class _FakeRepo:
    def __init__(self) -> None:
        self.upserts: list[CanonicalListing] = []

    async def upsert(self, listing: CanonicalListing) -> None:
        self.upserts.append(listing)

    async def get(self, listing_id: ListingId) -> CanonicalListing | None:
        for stored in self.upserts:
            if stored.id == listing_id:
                return stored
        return None


def _urls(page: int) -> Site591SearchUrls:
    first_row = (page - 1) * 30
    return Site591SearchUrls(
        referer_url=f"https://sale.591.com.tw/?firstRow={first_row}",
        api_url=f"https://bff-house.591.com.tw/v1/web/sale/list?firstRow={first_row}",
    )


@pytest.mark.asyncio
async def test_crawl_pages_stops_when_page_returns_short() -> None:
    """Two pages: first full (30 items), second short (5 items) -> stop after page 2."""
    page1 = _api_body([_item(i) for i in range(1, 31)])
    page2 = _api_body([_item(i) for i in range(31, 36)])
    page3 = _api_body([])
    fetcher = _FakeFetcher(
        {
            _urls(1).referer_url: "<html/>",
            _urls(1).api_url: page1,
            _urls(2).api_url: page2,
            _urls(3).api_url: page3,
        }
    )
    repo = _FakeRepo()
    service = Site591CrawlService(fetcher=fetcher, repo=repo)

    result = await service.crawl_pages(_urls, max_pages=10)

    assert result.pages == 2
    assert result.fetched == 35
    assert result.persisted == 35


@pytest.mark.asyncio
async def test_crawl_pages_respects_max_pages_cap() -> None:
    """Even if every page is full, max_pages caps the loop."""
    full = _api_body([_item(i) for i in range(1, 31)])
    fetcher = _FakeFetcher(
        {
            _urls(1).referer_url: "<html/>",
            _urls(1).api_url: full,
            _urls(2).api_url: full,
            _urls(3).api_url: full,
        }
    )
    repo = _FakeRepo()
    service = Site591CrawlService(fetcher=fetcher, repo=repo)

    result = await service.crawl_pages(_urls, max_pages=2)

    assert result.pages == 2
    assert result.fetched == 60


@pytest.mark.asyncio
async def test_crawl_pages_warm_up_only_on_first_page() -> None:
    page1 = _api_body([_item(i) for i in range(1, 31)])
    page2 = _api_body([_item(i) for i in range(31, 33)])
    fetcher = _FakeFetcher(
        {
            _urls(1).referer_url: "<html/>",
            _urls(1).api_url: page1,
            _urls(2).api_url: page2,
        }
    )
    repo = _FakeRepo()
    service = Site591CrawlService(fetcher=fetcher, repo=repo)

    await service.crawl_pages(_urls, max_pages=5)

    visited = [url for url, _ in fetcher.session_obj.requests]
    assert visited.count(_urls(1).referer_url) == 1
    assert _urls(2).referer_url not in visited


@pytest.mark.asyncio
async def test_crawl_pages_rejects_zero_max_pages() -> None:
    fetcher = _FakeFetcher({})
    service = Site591CrawlService(fetcher=fetcher, repo=_FakeRepo())
    with pytest.raises(ValueError, match="max_pages"):
        await service.crawl_pages(_urls, max_pages=0)


@pytest.mark.asyncio
async def test_crawl_single_page_back_compat() -> None:
    """The old `crawl(urls)` signature still works, used by the current CLI test."""
    body = _api_body([_item(i) for i in range(1, 4)])
    urls = _urls(1)
    fetcher = _FakeFetcher({urls.referer_url: "<html/>", urls.api_url: body})
    repo = _FakeRepo()
    service = Site591CrawlService(fetcher=fetcher, repo=repo)

    result = await service.crawl(urls)
    assert result.fetched == 3
    assert result.persisted == 3
    assert result.pages == 1
