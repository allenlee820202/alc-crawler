"""Tests for BuildMarketSummary use case."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.application.use_cases.build_market_summary import (
    BuildMarketSummary,
)
from alc_crawler.tracking.domain.snapshot import ListingSnapshot


def _snap(
    *,
    external_id: str = "1",
    snapshot_date: date = date(2026, 5, 9),
    district: str | None = "大安區",
    price: int = 25_000_000,
    unit_price: float | None = 80.0,
    site: str = "591",
) -> ListingSnapshot:
    return ListingSnapshot(
        snapshot_date=snapshot_date,
        listing_id=ListingId(site, external_id),
        price_amount=price,
        unit_price_per_ping=unit_price,
        address_district=district,
    )


class FakeRepo:
    def __init__(self, snapshots: list[ListingSnapshot]) -> None:
        self.snapshots = snapshots

    def initialize(self) -> None: ...
    def record_snapshots(self, snapshots) -> int:  # type: ignore[no-untyped-def]
        return 0
    def record_run(self, run) -> None: ...  # type: ignore[no-untyped-def]
    def snapshots_for_listing(self, listing_id, *, since=None):  # type: ignore[no-untyped-def]
        return []
    def latest_snapshot_date(self, *, site):  # type: ignore[no-untyped-def]
        return None
    def earliest_snapshot_on_or_after(self, anchor_date, *, site=None):  # type: ignore[no-untyped-def]
        return []
    def latest_snapshot_on_or_before(self, target_date, *, site=None):  # type: ignore[no-untyped-def]
        return []

    def snapshots_on_date(
        self, snapshot_date: date, *, site: str | None = None
    ) -> Sequence[ListingSnapshot]:
        return [
            s
            for s in self.snapshots
            if s.snapshot_date == snapshot_date
            and (site is None or s.listing_id.site == site)
        ]


class TestExecute:
    def test_returns_empty_when_no_snapshots_for_date(self) -> None:
        result = BuildMarketSummary(FakeRepo([])).execute(date(2026, 5, 9))
        assert list(result) == []

    def test_groups_by_district(self) -> None:
        snaps = [
            _snap(external_id="1", district="大安區", price=20_000_000),
            _snap(external_id="2", district="大安區", price=30_000_000),
            _snap(external_id="3", district="信義區", price=40_000_000),
        ]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2026, 5, 9))
        by_d = {s.district: s for s in result}
        assert by_d["大安區"].listing_count == 2
        assert by_d["信義區"].listing_count == 1

    def test_median_price_amount(self) -> None:
        # 3 listings -> median is the middle value
        snaps = [
            _snap(external_id="1", price=10_000_000),
            _snap(external_id="2", price=20_000_000),
            _snap(external_id="3", price=30_000_000),
        ]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2026, 5, 9))
        assert result[0].median_price_amount == 20_000_000

    def test_quartiles_for_unit_price(self) -> None:
        # Unit prices: 10, 20, 30, 40, 50
        # median = 30, p25 = 20 (inclusive), p75 = 40 (inclusive)
        snaps = [
            _snap(external_id=str(i), unit_price=float(p))
            for i, p in enumerate([10, 20, 30, 40, 50])
        ]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2026, 5, 9))
        s = result[0]
        assert s.median_unit_price_per_ping == 30.0
        assert s.p25_unit_price_per_ping == 20.0
        assert s.p75_unit_price_per_ping == 40.0

    def test_excludes_listings_without_unit_price_from_quartiles(self) -> None:
        snaps = [
            _snap(external_id="1", unit_price=None),
            _snap(external_id="2", unit_price=80.0),
            _snap(external_id="3", unit_price=80.0),
            _snap(external_id="4", unit_price=80.0),
        ]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2026, 5, 9))
        s = result[0]
        assert s.listing_count == 4  # all counted
        assert s.median_unit_price_per_ping == 80.0  # computed from 3 values

    def test_unit_price_stats_none_when_no_unit_prices(self) -> None:
        snaps = [_snap(external_id="1", unit_price=None)]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2026, 5, 9))
        s = result[0]
        assert s.listing_count == 1
        assert s.median_unit_price_per_ping is None
        assert s.p25_unit_price_per_ping is None
        assert s.p75_unit_price_per_ping is None

    def test_single_listing_district_uses_value_for_quartiles(self) -> None:
        snaps = [_snap(external_id="1", unit_price=80.0)]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2026, 5, 9))
        s = result[0]
        assert s.median_unit_price_per_ping == 80.0
        assert s.p25_unit_price_per_ping == 80.0
        assert s.p75_unit_price_per_ping == 80.0

    def test_two_listings_district_uses_low_high(self) -> None:
        snaps = [
            _snap(external_id="1", unit_price=70.0),
            _snap(external_id="2", unit_price=90.0),
        ]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2026, 5, 9))
        s = result[0]
        assert s.median_unit_price_per_ping == 80.0
        assert s.p25_unit_price_per_ping == 70.0
        assert s.p75_unit_price_per_ping == 90.0

    def test_blank_or_none_district_bucketed_as_unknown(self) -> None:
        snaps = [
            _snap(external_id="1", district=None),
            _snap(external_id="2", district="  "),
            _snap(external_id="3", district="大安區"),
        ]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2026, 5, 9))
        by_d = {s.district: s for s in result}
        assert "(unknown)" in by_d
        assert by_d["(unknown)"].listing_count == 2

    def test_sorted_by_listing_count_desc(self) -> None:
        snaps = (
            [_snap(external_id=f"a{i}", district="A") for i in range(2)]
            + [_snap(external_id=f"b{i}", district="B") for i in range(5)]
            + [_snap(external_id=f"c{i}", district="C") for i in range(3)]
        )
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2026, 5, 9))
        assert [s.district for s in result] == ["B", "C", "A"]

    def test_filters_by_site(self) -> None:
        snaps = [
            _snap(external_id="1", site="591"),
            _snap(external_id="2", site="rakuya"),
        ]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(
            date(2026, 5, 9), site="591"
        )
        assert sum(s.listing_count for s in result) == 1

    def test_snapshot_date_propagated(self) -> None:
        snaps = [_snap(snapshot_date=date(2025, 12, 31))]
        result = BuildMarketSummary(FakeRepo(snaps)).execute(date(2025, 12, 31))
        assert result[0].snapshot_date == date(2025, 12, 31)
