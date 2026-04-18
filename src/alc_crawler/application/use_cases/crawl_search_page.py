"""Use case: crawl one search results page, parse it, persist listings.

Pure orchestration. No I/O details, no site knowledge -- those live in
the infrastructure adapters and site parsers.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from alc_crawler.application.ports.fetcher import HttpFetcher
from alc_crawler.application.ports.listing_repository import ListingRepository
from alc_crawler.application.ports.site_parser import SearchPageParser


@dataclass(frozen=True, slots=True)
class CrawlSearchPageCommand:
    url: str


@dataclass(frozen=True, slots=True)
class CrawlSearchPageResult:
    fetched: int
    persisted: int


Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class CrawlSearchPage:
    def __init__(
        self,
        *,
        fetcher: HttpFetcher,
        repo: ListingRepository,
        parser: SearchPageParser,
        clock: Clock = _utc_now,
    ) -> None:
        self._fetcher = fetcher
        self._repo = repo
        self._parser = parser
        self._clock = clock

    async def execute(self, cmd: CrawlSearchPageCommand) -> CrawlSearchPageResult:
        response = await self._fetcher.get(cmd.url)
        listings = self._parser.parse(response.body, source_url=cmd.url)
        observed_at = self._clock()
        for listing in listings:
            await self._repo.upsert(listing.with_observed_at(observed_at))
        return CrawlSearchPageResult(fetched=len(listings), persisted=len(listings))
