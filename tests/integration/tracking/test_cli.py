"""Integration tests for the alc-tracker CLI."""
from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import Address, ListingId, Price
from alc_crawler.infrastructure.persistence.sqlite.listing_repository import (
    SqliteListingRepository,
)
from alc_crawler.tracking.infrastructure.duckdb.snapshot_repository import (
    DuckDbSnapshotRepository,
)
from alc_crawler.tracking.interfaces.cli.main import app

pytestmark = pytest.mark.integration

runner = CliRunner()


def _listing(
    ext_id: str,
    *,
    price: int = 1_000_000,
    district: str = "大安區",
    unit_price: float | None = 80.0,
) -> CanonicalListing:
    return CanonicalListing(
        id=ListingId("591", ext_id),
        title=f"t-{ext_id}",
        url=f"https://sale.591.com.tw/home/house/detail/2/{ext_id}.html",
        price=Price(price, "TWD"),
        address=Address(city="台北市", district=district, raw=f"{district}xxx"),
        observed_at=datetime(2026, 5, 9, tzinfo=UTC),
        attributes={"shape": "電梯大樓"},
        unit_price_per_ping=unit_price,
    )


@pytest.fixture
def canonical_db(tmp_path: Path) -> Path:
    """Pre-populated canonical SQLite for snapshot tests."""
    import asyncio

    path = tmp_path / "canonical.sqlite"
    repo = SqliteListingRepository(path)

    async def _seed() -> None:
        await repo.initialize()
        for i in range(3):
            await repo.upsert(_listing(str(i + 1), price=1_000_000 + i * 100_000))

    asyncio.run(_seed())
    return path


class TestSnapshot:
    def test_snapshot_records_canonical_listings(
        self, canonical_db: Path, tmp_path: Path
    ) -> None:
        tracking_db = tmp_path / "tracking.duckdb"
        result = runner.invoke(
            app,
            [
                "snapshot",
                "--canonical-db",
                str(canonical_db),
                "--tracking-db",
                str(tracking_db),
                "--date",
                "2026-05-09",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Snapshotted 3 listings for 2026-05-09" in result.output

        # Verify DuckDB actually has the rows.
        repo = DuckDbSnapshotRepository(tracking_db)
        repo.initialize()
        snaps = repo.snapshots_on_date(date(2026, 5, 9))
        assert len(snaps) == 3

    def test_snapshot_defaults_to_today(
        self, canonical_db: Path, tmp_path: Path
    ) -> None:
        tracking_db = tmp_path / "tracking.duckdb"
        result = runner.invoke(
            app,
            [
                "snapshot",
                "--canonical-db",
                str(canonical_db),
                "--tracking-db",
                str(tracking_db),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Snapshotted 3 listings" in result.output

    def test_snapshot_rejects_invalid_date(
        self, canonical_db: Path, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            app,
            [
                "snapshot",
                "--canonical-db",
                str(canonical_db),
                "--tracking-db",
                str(tmp_path / "t.duckdb"),
                "--date",
                "not-a-date",
            ],
        )
        assert result.exit_code != 0
        assert "ISO format" in result.output


@pytest.fixture
def populated_tracking_db(tmp_path: Path) -> Path:
    """Tracking DuckDB pre-seeded with two listings across two dates."""
    path = tmp_path / "tracking.duckdb"
    repo = DuckDbSnapshotRepository(path)
    repo.initialize()
    from alc_crawler.tracking.domain.snapshot import ListingSnapshot

    repo.record_snapshots(
        [
            ListingSnapshot(
                snapshot_date=date(2026, 5, 1),
                listing_id=ListingId("591", "1"),
                price_amount=1_000_000,
                unit_price_per_ping=80.0,
                address_district="大安區",
            ),
            ListingSnapshot(
                snapshot_date=date(2026, 5, 9),
                listing_id=ListingId("591", "1"),
                price_amount=950_000,
                unit_price_per_ping=76.0,
                address_district="大安區",
            ),
            ListingSnapshot(
                snapshot_date=date(2026, 5, 1),
                listing_id=ListingId("591", "2"),
                price_amount=2_000_000,
                unit_price_per_ping=100.0,
                address_district="信義區",
            ),
            ListingSnapshot(
                snapshot_date=date(2026, 5, 9),
                listing_id=ListingId("591", "2"),
                price_amount=2_000_000,
                unit_price_per_ping=100.0,
                address_district="信義區",
            ),
        ]
    )
    return path


class TestPriceChanges:
    def test_lists_price_changes_in_window(
        self, populated_tracking_db: Path
    ) -> None:
        result = runner.invoke(
            app,
            [
                "price-changes",
                "--tracking-db",
                str(populated_tracking_db),
                "--since",
                "2026-05-01",
                "--until",
                "2026-05-09",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "591:1" in result.output
        assert "1,000,000" in result.output
        assert "950,000" in result.output
        # Listing 2 was unchanged — should not appear
        assert "591:2" not in result.output

    def test_only_drops_filter(self, populated_tracking_db: Path) -> None:
        result = runner.invoke(
            app,
            [
                "price-changes",
                "--tracking-db",
                str(populated_tracking_db),
                "--since",
                "2026-05-01",
                "--until",
                "2026-05-09",
                "--only-drops",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "591:1" in result.output
        assert "drops only" in result.output

    def test_empty_message_when_no_changes(
        self, populated_tracking_db: Path
    ) -> None:
        result = runner.invoke(
            app,
            [
                "price-changes",
                "--tracking-db",
                str(populated_tracking_db),
                "--since",
                "2030-01-01",
                "--until",
                "2030-01-09",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "No price changes" in result.output

    def test_plain_format_uses_legacy_table(
        self, populated_tracking_db: Path
    ) -> None:
        result = runner.invoke(
            app,
            [
                "price-changes",
                "--tracking-db",
                str(populated_tracking_db),
                "--since",
                "2026-05-01",
                "--until",
                "2026-05-09",
                "--format",
                "plain",
            ],
        )
        assert result.exit_code == 0, result.output
        # Plain text uses 'listing' header (no markdown pipes/backticks).
        assert "listing" in result.output
        assert "|" not in result.output

    def test_invalid_format_rejected(
        self, populated_tracking_db: Path
    ) -> None:
        result = runner.invoke(
            app,
            [
                "price-changes",
                "--tracking-db",
                str(populated_tracking_db),
                "--since",
                "2026-05-01",
                "--format",
                "yaml",
            ],
        )
        assert result.exit_code != 0
        assert "must be 'markdown' or 'plain'" in result.output


class TestMarketSummary:
    def test_prints_per_district_stats(self, populated_tracking_db: Path) -> None:
        result = runner.invoke(
            app,
            [
                "market-summary",
                "--tracking-db",
                str(populated_tracking_db),
                "--date",
                "2026-05-09",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "大安區" in result.output
        assert "信義區" in result.output
        assert "Market summary 2026-05-09" in result.output

    def test_empty_message_when_no_snapshots(
        self, populated_tracking_db: Path
    ) -> None:
        result = runner.invoke(
            app,
            [
                "market-summary",
                "--tracking-db",
                str(populated_tracking_db),
                "--date",
                "2030-01-01",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "No snapshots" in result.output


class TestHelp:
    def test_root_help_lists_all_subcommands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in ("snapshot", "price-changes", "market-summary", "watch"):
            assert cmd in result.output


class TestWatchCommands:
    @pytest.fixture
    def tracking_db(self, tmp_path: Path) -> Path:
        return tmp_path / "tracking.duckdb"

    def test_add_then_list_round_trips(self, tracking_db: Path) -> None:
        result = runner.invoke(
            app,
            [
                "watch",
                "add",
                "591",
                "1",
                "--tracking-db",
                str(tracking_db),
                "--nickname",
                "near 大安國中",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Added" in result.output
        assert "591:1" in result.output

        result = runner.invoke(
            app, ["watch", "list", "--tracking-db", str(tracking_db)]
        )
        assert result.exit_code == 0, result.output
        assert "591:1" in result.output
        assert "near 大安國中" in result.output

    def test_list_empty(self, tracking_db: Path) -> None:
        result = runner.invoke(
            app, ["watch", "list", "--tracking-db", str(tracking_db)]
        )
        assert result.exit_code == 0, result.output
        assert "No watched listings" in result.output

    def test_remove_existing_returns_success(self, tracking_db: Path) -> None:
        runner.invoke(
            app,
            ["watch", "add", "591", "1", "--tracking-db", str(tracking_db)],
        )
        result = runner.invoke(
            app,
            ["watch", "remove", "591", "1", "--tracking-db", str(tracking_db)],
        )
        assert result.exit_code == 0, result.output
        assert "Removed" in result.output
        # Verify it's gone.
        result = runner.invoke(
            app, ["watch", "list", "--tracking-db", str(tracking_db)]
        )
        assert "No watched listings" in result.output

    def test_remove_missing_exits_nonzero(self, tracking_db: Path) -> None:
        # Initialize an empty DB so the file exists.
        runner.invoke(
            app,
            ["watch", "list", "--tracking-db", str(tracking_db)],
        )
        result = runner.invoke(
            app,
            [
                "watch",
                "remove",
                "591",
                "999",
                "--tracking-db",
                str(tracking_db),
            ],
        )
        assert result.exit_code != 0
        assert "not watched" in result.output.lower()

    def test_list_filters_by_site(self, tracking_db: Path) -> None:
        runner.invoke(
            app,
            ["watch", "add", "591", "1", "--tracking-db", str(tracking_db)],
        )
        runner.invoke(
            app,
            [
                "watch",
                "add",
                "yungching",
                "9",
                "--tracking-db",
                str(tracking_db),
            ],
        )
        result = runner.invoke(
            app,
            [
                "watch",
                "list",
                "--tracking-db",
                str(tracking_db),
                "--site",
                "591",
            ],
        )
        assert result.exit_code == 0
        assert "591:1" in result.output
        assert "yungching:9" not in result.output

    def test_re_add_updates_nickname(self, tracking_db: Path) -> None:
        runner.invoke(
            app,
            [
                "watch",
                "add",
                "591",
                "1",
                "--tracking-db",
                str(tracking_db),
                "--nickname",
                "old",
            ],
        )
        result = runner.invoke(
            app,
            [
                "watch",
                "add",
                "591",
                "1",
                "--tracking-db",
                str(tracking_db),
                "--nickname",
                "new",
            ],
        )
        assert result.exit_code == 0, result.output
        listed = runner.invoke(
            app, ["watch", "list", "--tracking-db", str(tracking_db)]
        )
        assert "new" in listed.output
        assert "old" not in listed.output
