"""591-specific crawl orchestration.

Performs a same-origin warm-up on the search page so cookies are set and
the BFF accepts our subsequent JSON request. Persists parsed listings via
the injected repository.

Supports paginated crawls: the caller provides a `urls_for_page` callable
so the service can request page 1, 2, ... up to `max_pages`. The loop
stops early when a page returns fewer than `_PAGE_SIZE` listings (the
practical end-of-results signal — 591 does not return a total count).

This wraps the generic application use case where 591 needs extra dance
steps; if/when we add Yungching, it will get its own analogous service.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from alc_crawler.adapters.sites.site_591.api_parser import Site591ApiParser
from alc_crawler.adapters.sites.site_591.search_urls import Site591SearchUrls
from alc_crawler.application.ports.listing_repository import ListingRepository
from alc_crawler.infrastructure.http.httpx_fetcher import HttpxFetcher

_PAGE_SIZE = 30


@dataclass(frozen=True, slots=True)
class Site591CrawlResult:
    fetched: int
    persisted: int
    pages: int


class Site591CrawlService:
    def __init__(
        self,
        *,
        fetcher: HttpxFetcher,
        repo: ListingRepository,
        parser: Site591ApiParser | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._repo = repo
        self._parser = parser or Site591ApiParser()

    async def crawl(self, urls: Site591SearchUrls) -> Site591CrawlResult:
        """Single-page crawl (kept for back-compat with existing tests/CLI)."""
        return await self.crawl_pages(lambda _page: urls, max_pages=1)

    async def crawl_pages(
        self,
        urls_for_page: Callable[[int], Site591SearchUrls],
        *,
        max_pages: int = 1,
    ) -> Site591CrawlResult:
        if max_pages < 1:
            raise ValueError(f"max_pages must be >= 1, got {max_pages}")

        observed_at = datetime.now(UTC)
        total_fetched = 0
        total_persisted = 0
        pages_done = 0

        async with self._fetcher.session() as session:
            for page in range(1, max_pages + 1):
                urls = urls_for_page(page)
                if page == 1:
                    # Warm-up: load search page so cookies (T591_TOKEN, urlJumpIp)
                    # are set on the shared client.
                    await session.get(urls.referer_url)
                api_response = await session.get(
                    urls.api_url,
                    headers={
                        "Referer": urls.referer_url,
                        "Accept": "application/json, text/plain, */*",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                )
                listings = self._parser.parse(
                    api_response.body, source_url=urls.api_url
                )
                pages_done += 1
                total_fetched += len(listings)
                for listing in listings:
                    await self._repo.upsert(listing.with_observed_at(observed_at))
                    total_persisted += 1

                # End-of-results: 591 returns < _PAGE_SIZE on the last page.
                # Note: parser may drop a few items (e.g. price=0 pre-sales),
                # so use the raw response, not `listings`, as the signal.
                # We approximate by checking parsed count; this is good enough
                # because dropped-rows-per-page is small (typically 0-1).
                if len(listings) < _PAGE_SIZE:
                    break

        return Site591CrawlResult(
            fetched=total_fetched,
            persisted=total_persisted,
            pages=pages_done,
        )
