"""Tests for the CrawlSearchPage use case using in-memory fakes (no I/O)."""
from __future__ import annotations

from dataclasses import dataclass, field

from alc_crawler.application.ports.fetcher import FetchResult, HttpFetcher
from alc_crawler.application.ports.listing_repository import ListingRepository
from alc_crawler.application.ports.site_parser import SearchPageParser
from alc_crawler.application.use_cases.crawl_search_page import (
    CrawlSearchPage,
    CrawlSearchPageCommand,
)
from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import Address, ListingId, Price

# ---------- Fakes ----------


@dataclass
class FakeHttpFetcher(HttpFetcher):
    responses: dict[str, str]
    calls: list[str] = field(default_factory=list)

    async def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResult:
        self.calls.append(url)
        if url not in self.responses:
            raise AssertionError(f"unexpected url: {url}")
        return FetchResult(url=url, status=200, body=self.responses[url])


@dataclass
class FakeRepo(ListingRepository):
    saved: list[CanonicalListing] = field(default_factory=list)

    async def upsert(self, listing: CanonicalListing) -> None:
        # Replace by id if present, else append (mimics SQL upsert).
        for i, existing in enumerate(self.saved):
            if existing.id == listing.id:
                self.saved[i] = listing
                return
        self.saved.append(listing)

    async def get(self, listing_id: ListingId) -> CanonicalListing | None:
        return next((listing for listing in self.saved if listing.id == listing_id), None)


class StubParser(SearchPageParser):
    def __init__(self, listings: list[CanonicalListing]) -> None:
        self._listings = listings

    def parse(self, html: str, *, source_url: str) -> list[CanonicalListing]:
        return list(self._listings)


def _addr() -> Address:
    return Address(city="台北市", district="大安區", raw="x")


def _listing(ext_id: str) -> CanonicalListing:
    return CanonicalListing(
        id=ListingId("591", ext_id),
        title=f"listing-{ext_id}",
        url=f"https://example.com/{ext_id}",
        price=Price(1_000_000, "TWD"),
        address=_addr(),
    )


# ---------- Tests ----------


async def test_fetch_parse_and_persist_listings() -> None:
    fetcher = FakeHttpFetcher({"https://search/?p=1": "<html/>"})
    repo = FakeRepo()
    parser = StubParser([_listing("1"), _listing("2")])
    use_case = CrawlSearchPage(fetcher=fetcher, repo=repo, parser=parser)

    result = await use_case.execute(CrawlSearchPageCommand(url="https://search/?p=1"))

    assert result.fetched == 2
    assert result.persisted == 2
    assert len(repo.saved) == 2
    assert fetcher.calls == ["https://search/?p=1"]


async def test_observed_at_is_set_on_persisted_listings() -> None:
    fetcher = FakeHttpFetcher({"https://search/?p=1": "<html/>"})
    repo = FakeRepo()
    parser = StubParser([_listing("1")])
    use_case = CrawlSearchPage(fetcher=fetcher, repo=repo, parser=parser)

    await use_case.execute(CrawlSearchPageCommand(url="https://search/?p=1"))

    assert repo.saved[0].observed_at is not None


async def test_re_crawl_updates_existing_listing() -> None:
    fetcher = FakeHttpFetcher({"https://search/?p=1": "<html/>"})
    repo = FakeRepo()
    parser = StubParser([_listing("1")])
    use_case = CrawlSearchPage(fetcher=fetcher, repo=repo, parser=parser)

    await use_case.execute(CrawlSearchPageCommand(url="https://search/?p=1"))
    await use_case.execute(CrawlSearchPageCommand(url="https://search/?p=1"))

    assert len(repo.saved) == 1  # upsert, not duplicated


async def test_empty_parse_result_is_handled_gracefully() -> None:
    fetcher = FakeHttpFetcher({"https://search/?p=1": "<html/>"})
    repo = FakeRepo()
    use_case = CrawlSearchPage(fetcher=fetcher, repo=repo, parser=StubParser([]))

    result = await use_case.execute(CrawlSearchPageCommand(url="https://search/?p=1"))

    assert result.fetched == 0
    assert result.persisted == 0
