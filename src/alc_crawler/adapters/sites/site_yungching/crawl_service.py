"""Yungching-specific crawl orchestration.

Unlike 591, Yungching does not require a warm-up request. The API endpoint
responds directly with encrypted JSON. Pagination uses the `pg` parameter
and stops when we reach the reported `totalPageCount`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from alc_crawler.adapters.sites.site_yungching.api_parser import YungchingApiParser
from alc_crawler.adapters.sites.site_yungching.raw_item import get_pagination_info
from alc_crawler.adapters.sites.site_yungching.search_urls import (
    search_params,
)
from alc_crawler.application.ports.listing_repository import ListingRepository
from alc_crawler.infrastructure.http.httpx_fetcher import HttpxFetcher

_PAGE_SIZE = 30


@dataclass(frozen=True, slots=True)
class YungchingCrawlResult:
    fetched: int
    persisted: int
    pages: int


class YungchingCrawlService:
    def __init__(
        self,
        *,
        fetcher: HttpxFetcher,
        repo: ListingRepository,
        parser: YungchingApiParser | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._repo = repo
        self._parser = parser or YungchingApiParser()

    async def crawl_pages(
        self,
        region: str,
        *,
        max_pages: int = 1,
        districts: list[str] | None = None,
        min_price_wan: float | None = None,
        max_price_wan: float | None = None,
        min_rooms: int | None = None,
        max_rooms: int | None = None,
        max_age: float | None = None,
    ) -> YungchingCrawlResult:
        if max_pages < 1:
            raise ValueError(f"max_pages must be >= 1, got {max_pages}")

        observed_at = datetime.now(UTC)
        total_fetched = 0
        total_persisted = 0
        pages_done = 0
        total_pages_available: int | None = None

        async with self._fetcher.session() as session:
            for page in range(1, max_pages + 1):
                # Stop if we know there are no more pages
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
                    max_age=max_age,
                )
                response = await session.get(
                    params.api_url,
                    headers={
                        "Referer": params.referer_url,
                        "Accept": "application/json, text/plain, */*",
                    },
                )

                # Extract pagination on first page
                if page == 1:
                    total_pages_available, _ = get_pagination_info(response.body)

                listings = self._parser.parse(response.body, source_url=params.api_url)
                pages_done += 1
                total_fetched += len(listings)
                for listing in listings:
                    await self._repo.upsert(listing.with_observed_at(observed_at))
                    total_persisted += 1

                # End-of-results: fewer items than page size
                if len(listings) < _PAGE_SIZE:
                    break

        return YungchingCrawlResult(
            fetched=total_fetched,
            persisted=total_persisted,
            pages=pages_done,
        )
