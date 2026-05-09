"""Tests for RecordDailySnapshots use case (uses in-memory fakes)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date

import pytest

from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import Address, ListingId, Price
from alc_crawler.tracking.application.use_cases.record_daily_snapshots import (
    RecordDailySnapshots,
    _to_snapshot,
)
from alc_crawler.tracking.domain.crawl_run import CrawlRun
from alc_crawler.tracking.domain.snapshot import ListingSnapshot


class FakeListingReader:
    def __init__(self, listings: list[CanonicalListing]) -> None:
        self.listings = listings

    async def iter_all(self) -> AsyncIterator[CanonicalListing]:
        for listing in self.listings:
            yield listing

    # ListingRepository protocol demands these too; tracking doesn't use them.
    async def upsert(self, listing: CanonicalListing) -> None:
        raise NotImplementedError

    async def get(self, listing_id: ListingId) -> CanonicalListing | None:
        raise NotImplementedError


class FakeSnapshotRepo:
    def __init__(self) -> None:
        self.initialized = False
        self.record_calls: list[list[ListingSnapshot]] = []
        self.runs: list[CrawlRun] = []

    def initialize(self) -> None:
        self.initialized = True

    def record_snapshots(self, snapshots) -> int:  # type: ignore[no-untyped-def]
        batch = list(snapshots)
        self.record_calls.append(batch)
        return len(batch)

    def record_run(self, run: CrawlRun) -> None:
        self.runs.append(run)

    def snapshots_for_listing(self, listing_id, *, since=None):  # type: ignore[no-untyped-def]
        return []

    def latest_snapshot_date(self, *, site: str):  # type: ignore[no-untyped-def]
        return None


def _listing(
    *,
    external_id: str = "1",
    price: int = 1_000_000,
    attrs: dict[str, str] | None = None,
    district: str = "大安區",
    area_ping: float | None = 30.0,
    community: str | None = "Foo Garden",
) -> CanonicalListing:
    return CanonicalListing(
        id=ListingId("591", external_id),
        title=f"listing {external_id}",
        url="https://sale.591.com.tw/home/house/detail/2/1.html",
        price=Price(amount=price, currency="TWD"),
        address=Address(city="台北市", district=district, raw=f"{district}xxx"),
        area_ping=area_ping,
        unit_price_per_ping=33.3,
        house_age_years=10,
        view_count=100,
        community_name=community,
        attributes=attrs or {},
    )


class TestToSnapshot:
    def test_extracts_canonical_fields(self) -> None:
        listing = _listing()
        snap = _to_snapshot(listing, date(2026, 5, 9))
        assert snap.snapshot_date == date(2026, 5, 9)
        assert snap.listing_id == listing.id
        assert snap.price_amount == 1_000_000
        assert snap.area_ping == 30.0
        assert snap.address_district == "大安區"
        assert snap.community_name == "Foo Garden"

    def test_extracts_shape_from_attributes(self) -> None:
        listing = _listing(attrs={"shape": "電梯大樓", "extra": "foo"})
        snap = _to_snapshot(listing, date(2026, 5, 9))
        assert snap.shape == "電梯大樓"

    def test_shape_is_none_when_attribute_missing(self) -> None:
        snap = _to_snapshot(_listing(attrs={}), date(2026, 5, 9))
        assert snap.shape is None

    def test_serialises_attributes_json_sorted(self) -> None:
        listing = _listing(attrs={"b": "2", "a": "1"})
        snap = _to_snapshot(listing, date(2026, 5, 9))
        assert snap.source_attributes_json == '{"a": "1", "b": "2"}'

    def test_attributes_json_none_when_attributes_empty(self) -> None:
        snap = _to_snapshot(_listing(attrs={}), date(2026, 5, 9))
        assert snap.source_attributes_json is None

    def test_preserves_unicode_in_json(self) -> None:
        listing = _listing(attrs={"shape": "電梯大樓"})
        snap = _to_snapshot(listing, date(2026, 5, 9))
        assert snap.source_attributes_json is not None
        assert "電梯大樓" in snap.source_attributes_json


class TestExecute:
    @pytest.mark.asyncio
    async def test_initializes_repo(self) -> None:
        repo = FakeSnapshotRepo()
        await RecordDailySnapshots(FakeListingReader([]), repo).execute(
            date(2026, 5, 9)
        )
        assert repo.initialized

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_canonical(self) -> None:
        repo = FakeSnapshotRepo()
        result = await RecordDailySnapshots(FakeListingReader([]), repo).execute(
            date(2026, 5, 9)
        )
        assert result.listings_persisted == 0
        assert result.snapshot_date == date(2026, 5, 9)
        assert repo.record_calls == []

    @pytest.mark.asyncio
    async def test_records_one_snapshot_per_listing(self) -> None:
        listings = [_listing(external_id=str(i)) for i in range(5)]
        repo = FakeSnapshotRepo()
        result = await RecordDailySnapshots(
            FakeListingReader(listings), repo
        ).execute(date(2026, 5, 9))
        assert result.listings_persisted == 5
        flat = [s for batch in repo.record_calls for s in batch]
        assert {s.listing_id.external_id for s in flat} == {"0", "1", "2", "3", "4"}
        assert all(s.snapshot_date == date(2026, 5, 9) for s in flat)

    @pytest.mark.asyncio
    async def test_batches_writes_at_batch_size(self) -> None:
        listings = [_listing(external_id=str(i)) for i in range(7)]
        repo = FakeSnapshotRepo()
        result = await RecordDailySnapshots(
            FakeListingReader(listings), repo, batch_size=3
        ).execute(date(2026, 5, 9))
        # 3 + 3 + 1
        assert [len(b) for b in repo.record_calls] == [3, 3, 1]
        assert result.listings_persisted == 7

    @pytest.mark.asyncio
    async def test_single_batch_when_below_size(self) -> None:
        listings = [_listing(external_id=str(i)) for i in range(2)]
        repo = FakeSnapshotRepo()
        await RecordDailySnapshots(
            FakeListingReader(listings), repo, batch_size=10
        ).execute(date(2026, 5, 9))
        assert len(repo.record_calls) == 1
        assert len(repo.record_calls[0]) == 2

    @pytest.mark.asyncio
    async def test_uses_supplied_date(self) -> None:
        repo = FakeSnapshotRepo()
        await RecordDailySnapshots(
            FakeListingReader([_listing()]), repo
        ).execute(date(2025, 12, 31))
        assert repo.record_calls[0][0].snapshot_date == date(2025, 12, 31)
