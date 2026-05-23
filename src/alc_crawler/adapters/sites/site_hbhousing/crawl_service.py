"""Hbhousing-specific crawl orchestration.

Hbhousing is a Nuxt3 SSR app. Search results are embedded in the HTML page
as inline __NUXT_DATA__ JSON. No encryption, no API tokens needed.
Pagination uses path-based URL segments ({n}-page).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from alc_crawler.adapters.sites.site_hbhousing.api_parser import HbhousingParser
from alc_crawler.adapters.sites.site_hbhousing.search_urls import search_params
from alc_crawler.application.ports.listing_repository import ListingRepository
from alc_crawler.infrastructure.http.httpx_fetcher import HttpxFetcher

_PAGE_SIZE = 10


@dataclass(frozen=True, slots=True)
class HbhousingCrawlResult:
    fetched: int
    persisted: int
    pages: int


class HbhousingCrawlService:
    def __init__(
        self,
        *,
        fetcher: HttpxFetcher,
        repo: ListingRepository,
        parser: HbhousingParser | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._repo = repo
        self._parser = parser or HbhousingParser()

    async def crawl_pages(
        self,
        region: str,
        *,
        max_pages: int = 1,
        districts: list[str] | None = None,
        min_price_wan: int | None = None,
        max_price_wan: int | None = None,
        min_rooms: int | None = None,
        max_rooms: int | None = None,
        styles: list[str] | None = None,
    ) -> HbhousingCrawlResult:
        if max_pages < 1:
            raise ValueError(f"max_pages must be >= 1, got {max_pages}")

        observed_at = datetime.now(UTC)
        total_fetched = 0
        total_persisted = 0
        pages_done = 0
        total_pages_available: int | None = None

        async with self._fetcher.session() as session:
            for page in range(1, max_pages + 1):
                # Stop if we know there are no more pages.
                if total_pages_available is not None and page > total_pages_available:
                    break

                params = search_params(
                    region,
                    page=page,
                    districts=districts,
                    min_price_wan=min_price_wan,
                    max_price_wan=max_price_wan,
                    min_rooms=min_rooms,
                    max_rooms=max_rooms,
                    styles=styles,
                )
                response = await session.get(
                    params.page_url,
                    headers={
                        "Referer": params.referer_url,
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    },
                )

                # Extract pagination on first page.
                if page == 1:
                    total_pages_available = self._parser.total_pages(response.body)

                listings = self._parser.parse(response.body, source_url=params.page_url)
                pages_done += 1
                total_fetched += len(listings)
                for listing in listings:
                    await self._repo.upsert(listing.with_observed_at(observed_at))
                    total_persisted += 1

                # End-of-results: fewer items than page size.
                if len(listings) < _PAGE_SIZE:
                    break

        return HbhousingCrawlResult(
            fetched=total_fetched,
            persisted=total_persisted,
            pages=pages_done,
        )
