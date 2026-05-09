"""Integration tests for the DuckDB-backed SnapshotRepository."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.crawl_run import CrawlRun, RunStatus
from alc_crawler.tracking.domain.snapshot import ListingSnapshot
from alc_crawler.tracking.infrastructure.duckdb.snapshot_repository import (
    DuckDbSnapshotRepository,
)

pytestmark = pytest.mark.integration


def _snap(
    *,
    snapshot_date: date = date(2026, 5, 9),
    external_id: str = "1",
    price_amount: int = 1_000_000,
    **overrides: object,
) -> ListingSnapshot:
    base: dict[str, object] = {
        "snapshot_date": snapshot_date,
        "listing_id": ListingId("591", external_id),
        "price_amount": price_amount,
        "area_ping": 30.0,
        "unit_price_per_ping": 33.3,
        "house_age_years": 10,
        "view_count": 100,
        "community_name": "Foo Garden",
        "address_district": "大安區",
        "shape": "電梯大樓",
    }
    base.update(overrides)
    return ListingSnapshot(**base)  # type: ignore[arg-type]


@pytest.fixture
def repo(tmp_path: Path) -> DuckDbSnapshotRepository:
    r = DuckDbSnapshotRepository(tmp_path / "tracking.duckdb")
    r.initialize()
    return r


class TestInitialize:
    def test_initialize_is_idempotent(self, tmp_path: Path) -> None:
        r = DuckDbSnapshotRepository(tmp_path / "tracking.duckdb")
        r.initialize()
        r.initialize()  # should not raise

    def test_initialize_creates_parent_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "tracking.duckdb"
        r = DuckDbSnapshotRepository(target)
        r.initialize()
        assert target.parent.exists()


class TestRecordSnapshots:
    def test_record_snapshots_returns_count(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        n = repo.record_snapshots([_snap(external_id="1"), _snap(external_id="2")])
        assert n == 2

    def test_record_snapshots_persists(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        repo.record_snapshots([_snap(external_id="42", price_amount=2_500_000)])
        rows = repo.snapshots_for_listing(ListingId("591", "42"))
        assert len(rows) == 1
        assert rows[0].price_amount == 2_500_000

    def test_record_snapshots_same_day_overwrites(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        repo.record_snapshots([_snap(external_id="1", price_amount=1_000_000)])
        repo.record_snapshots([_snap(external_id="1", price_amount=999_000)])
        rows = repo.snapshots_for_listing(ListingId("591", "1"))
        assert len(rows) == 1
        assert rows[0].price_amount == 999_000

    def test_record_snapshots_different_days_both_persist(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        repo.record_snapshots(
            [
                _snap(snapshot_date=date(2026, 5, 8), external_id="1"),
                _snap(snapshot_date=date(2026, 5, 9), external_id="1"),
            ]
        )
        rows = repo.snapshots_for_listing(ListingId("591", "1"))
        assert [r.snapshot_date for r in rows] == [
            date(2026, 5, 8),
            date(2026, 5, 9),
        ]

    def test_record_snapshots_empty_iterable_is_noop(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        assert repo.record_snapshots([]) == 0

    def test_record_snapshots_handles_optional_nulls(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        snap = ListingSnapshot(
            snapshot_date=date(2026, 5, 9),
            listing_id=ListingId("591", "minimal"),
            price_amount=500_000,
        )
        repo.record_snapshots([snap])
        rows = repo.snapshots_for_listing(ListingId("591", "minimal"))
        assert rows[0].area_ping is None
        assert rows[0].community_name is None


class TestSnapshotsForListing:
    def test_returns_oldest_first(self, repo: DuckDbSnapshotRepository) -> None:
        repo.record_snapshots(
            [
                _snap(snapshot_date=date(2026, 5, 9), external_id="1"),
                _snap(snapshot_date=date(2026, 5, 7), external_id="1"),
                _snap(snapshot_date=date(2026, 5, 8), external_id="1"),
            ]
        )
        rows = repo.snapshots_for_listing(ListingId("591", "1"))
        assert [r.snapshot_date for r in rows] == [
            date(2026, 5, 7),
            date(2026, 5, 8),
            date(2026, 5, 9),
        ]

    def test_filters_by_since_inclusive(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        repo.record_snapshots(
            [
                _snap(snapshot_date=date(2026, 5, 1), external_id="1"),
                _snap(snapshot_date=date(2026, 5, 5), external_id="1"),
                _snap(snapshot_date=date(2026, 5, 9), external_id="1"),
            ]
        )
        rows = repo.snapshots_for_listing(
            ListingId("591", "1"), since=date(2026, 5, 5)
        )
        assert [r.snapshot_date for r in rows] == [
            date(2026, 5, 5),
            date(2026, 5, 9),
        ]

    def test_returns_empty_for_unknown_listing(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        assert (
            repo.snapshots_for_listing(ListingId("591", "nope")) == []
        )


class TestRecordRun:
    def test_record_run_persists(self, repo: DuckDbSnapshotRepository) -> None:
        run = CrawlRun(
            run_id="run-abc",
            started_at=datetime(2026, 5, 9, 6, 0, 0),
            completed_at=datetime(2026, 5, 9, 6, 5, 0),
            site="591",
            region="taipei",
            pages_fetched=50,
            listings_seen=1500,
            listings_persisted=1500,
            status=RunStatus.OK,
        )
        repo.record_run(run)
        # round-trip via raw query
        with repo._connect() as conn:
            row = conn.execute(
                "SELECT site, region, status, listings_persisted FROM crawl_runs"
            ).fetchone()
        assert row == ("591", "taipei", "ok", 1500)


class TestLatestSnapshotDate:
    def test_returns_none_when_empty(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        assert repo.latest_snapshot_date(site="591") is None

    def test_returns_max_date_for_site(
        self, repo: DuckDbSnapshotRepository
    ) -> None:
        repo.record_snapshots(
            [
                _snap(snapshot_date=date(2026, 5, 1), external_id="1"),
                _snap(snapshot_date=date(2026, 5, 9), external_id="2"),
                _snap(snapshot_date=date(2026, 5, 5), external_id="3"),
            ]
        )
        assert repo.latest_snapshot_date(site="591") == date(2026, 5, 9)

    def test_isolates_sites(self, repo: DuckDbSnapshotRepository) -> None:
        repo.record_snapshots([_snap(snapshot_date=date(2026, 5, 9), external_id="1")])
        assert repo.latest_snapshot_date(site="rakuya") is None
