"""591-specific crawl orchestration.

Performs a same-origin warm-up on the search page so cookies are set and
the BFF accepts our subsequent JSON request. Persists parsed listings via
the injected repository.

This wraps the generic application use case where 591 needs extra dance
steps; if/when we add Yungching, it will get its own analogous service or
plug straight into `CrawlSearchPage` if it doesn't need warm-up.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from alc_crawler.adapters.sites.site_591.api_parser import Site591ApiParser
from alc_crawler.adapters.sites.site_591.search_urls import Site591SearchUrls
from alc_crawler.application.ports.listing_repository import ListingRepository
from alc_crawler.infrastructure.http.httpx_fetcher import HttpxFetcher


@dataclass(frozen=True, slots=True)
class Site591CrawlResult:
    fetched: int
    persisted: int


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
        async with self._fetcher.session() as session:
            # Warm-up: load the search page so cookies (T591_TOKEN, urlJumpIp)
            # are set on the shared client.
            await session.get(urls.referer_url)
            # Real request: BFF requires same-origin Referer + Accept JSON.
            api_response = await session.get(
                urls.api_url,
                headers={
                    "Referer": urls.referer_url,
                    "Accept": "application/json, text/plain, */*",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )

        listings = self._parser.parse(api_response.body, source_url=urls.api_url)
        observed_at = datetime.now(UTC)
        for listing in listings:
            await self._repo.upsert(listing.with_observed_at(observed_at))
        return Site591CrawlResult(fetched=len(listings), persisted=len(listings))
