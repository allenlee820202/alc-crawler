"""Tests for BuildWatchReport use case."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

import pytest

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.application.use_cases.build_watch_report import (
    BuildWatchReport,
)
from alc_crawler.tracking.domain.lifecycle import LifecycleStatus
from alc_crawler.tracking.domain.snapshot import ListingSnapshot
from alc_crawler.tracking.domain.watchlist import WatchedListing

# --- minimal in-memory fakes -------------------------------------------------


class FakeWatchlist:
    def __init__(self, items: list[WatchedListing]) -> None:
        self._items = items

    def initialize(self) -> None:
        pass

    def add(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError

    def remove(self, *args: object, **kwargs: object) -> bool:
        raise NotImplementedError

    def get(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError

    def list_all(
        self, *, site: str | None = None
    ) -> Sequence[WatchedListing]:
        if site is None:
            return self._items
        return [w for w in self._items if w.listing_id.site == site]


class FakeSnapshots:
    def __init__(self, by_id: dict[ListingId, list[ListingSnapshot]]) -> None:
        self._by_id = by_id

    def snapshots_for_listing(
        self,
        listing_id: ListingId,
        *,
        since: date | None = None,
    ) -> Sequence[ListingSnapshot]:
        out = self._by_id.get(listing_id, [])
        if since is not None:
            out = [s for s in out if s.snapshot_date >= since]
        return list(out)

    # Stubs for unused port methods.
    def initialize(self) -> None:
        pass

    def record_snapshots(self, *args: object, **kwargs: object) -> int:
        raise NotImplementedError

    def record_run(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError

    def latest_snapshot_date(self, **kwargs: object) -> date | None:
        return None

    def earliest_snapshot_on_or_after(
        self, *args: object, **kwargs: object
    ) -> Sequence[ListingSnapshot]:
        return []

    def latest_snapshot_on_or_before(
        self, *args: object, **kwargs: object
    ) -> Sequence[ListingSnapshot]:
        return []

    def snapshots_on_date(
        self, *args: object, **kwargs: object
    ) -> Sequence[ListingSnapshot]:
        return []


def _snap(
    d: date,
    listing_id: ListingId,
    price: int,
    *,
    district: str = "大安區",
    community: str | None = "Block A",
) -> ListingSnapshot:
    return ListingSnapshot(
        snapshot_date=d,
        listing_id=listing_id,
        price_amount=price,
        address_district=district,
        community_name=community,
    )


class TestBuildWatchReport:
    def test_returns_empty_when_no_watches(self) -> None:
        uc = BuildWatchReport(FakeWatchlist([]), FakeSnapshots({}))
        assert list(uc.execute(today=date(2026, 5, 9))) == []

    def test_entry_for_watch_with_no_snapshots(self) -> None:
        listing_id = ListingId("591", "1")
        uc = BuildWatchReport(
            FakeWatchlist(
                [WatchedListing(listing_id, datetime(2026, 5, 1), nickname="x")]
            ),
            FakeSnapshots({}),
        )
        out = list(uc.execute(today=date(2026, 5, 9)))
        assert len(out) == 1
        e = out[0]
        assert e.listing_id == listing_id
        assert e.nickname == "x"
        assert e.snapshot_count == 0
        assert e.first_seen_date is None
        assert e.last_seen_date is None
        assert e.lifecycle_status is None
        assert e.total_delta is None
        assert e.total_delta_pct is None

    def test_aggregates_min_max_first_last(self) -> None:
        listing_id = ListingId("591", "1")
        snaps = [
            _snap(date(2026, 5, 1), listing_id, 1_000_000),
            _snap(date(2026, 5, 3), listing_id, 1_100_000),
            _snap(date(2026, 5, 5), listing_id, 900_000),
            _snap(date(2026, 5, 9), listing_id, 950_000),
        ]
        uc = BuildWatchReport(
            FakeWatchlist(
                [WatchedListing(listing_id, datetime(2026, 5, 1))]
            ),
            FakeSnapshots({listing_id: snaps}),
        )
        e = uc.execute(today=date(2026, 5, 9))[0]
        assert e.snapshot_count == 4
        assert e.first_seen_date == date(2026, 5, 1)
        assert e.last_seen_date == date(2026, 5, 9)
        assert e.days_on_market == 8
        assert e.first_price == 1_000_000
        assert e.latest_price == 950_000
        assert e.min_price == 900_000
        assert e.min_price_date == date(2026, 5, 5)
        assert e.max_price == 1_100_000
        assert e.max_price_date == date(2026, 5, 3)
        assert e.total_delta == -50_000
        assert e.total_delta_pct == pytest.approx(-5.0)

    def test_lifecycle_uses_today_minus_last_seen(self) -> None:
        listing_id = ListingId("591", "1")
        # last seen 2 days ago: STALE.
        snaps = [_snap(date(2026, 5, 7), listing_id, 1_000_000)]
        uc = BuildWatchReport(
            FakeWatchlist(
                [WatchedListing(listing_id, datetime(2026, 5, 1))]
            ),
            FakeSnapshots({listing_id: snaps}),
        )
        e = uc.execute(today=date(2026, 5, 9))[0]
        assert e.lifecycle_status == LifecycleStatus.STALE

    def test_lifecycle_off_sale_when_old(self) -> None:
        listing_id = ListingId("591", "1")
        snaps = [_snap(date(2026, 4, 1), listing_id, 1_000_000)]
        uc = BuildWatchReport(
            FakeWatchlist(
                [WatchedListing(listing_id, datetime(2026, 5, 1))]
            ),
            FakeSnapshots({listing_id: snaps}),
        )
        e = uc.execute(today=date(2026, 5, 9))[0]
        assert e.lifecycle_status == LifecycleStatus.OFF_SALE

    def test_passes_site_filter_to_watchlist(self) -> None:
        watches = [
            WatchedListing(ListingId("591", "1"), datetime(2026, 5, 1)),
            WatchedListing(ListingId("yungching", "9"), datetime(2026, 5, 1)),
        ]
        uc = BuildWatchReport(FakeWatchlist(watches), FakeSnapshots({}))
        out = list(uc.execute(today=date(2026, 5, 9), site="591"))
        assert len(out) == 1
        assert out[0].listing_id.site == "591"

    def test_district_and_community_come_from_latest_snapshot(self) -> None:
        listing_id = ListingId("591", "1")
        snaps = [
            _snap(
                date(2026, 5, 1),
                listing_id,
                1_000_000,
                district="老地址",
                community="老社區",
            ),
            _snap(
                date(2026, 5, 9),
                listing_id,
                1_000_000,
                district="新地址",
                community="新社區",
            ),
        ]
        uc = BuildWatchReport(
            FakeWatchlist(
                [WatchedListing(listing_id, datetime(2026, 5, 1))]
            ),
            FakeSnapshots({listing_id: snaps}),
        )
        e = uc.execute(today=date(2026, 5, 9))[0]
        assert e.latest_district == "新地址"
        assert e.latest_community == "新社區"
