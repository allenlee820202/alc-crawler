"""Tests for matplotlib chart renderers.

We don't assert on visual correctness — that's brittle. We assert
that the file is written, looks like a PNG (magic bytes), and
non-zero size. Edge cases (empty input) are validated explicitly.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.district_summary import DistrictSummary
from alc_crawler.tracking.domain.snapshot import ListingSnapshot
from alc_crawler.tracking.interfaces.reports.charts import (
    render_price_history_chart,
    render_unit_price_distribution_chart,
)

pytestmark = pytest.mark.integration

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _snap(snapshot_date: date, price: int) -> ListingSnapshot:
    return ListingSnapshot(
        snapshot_date=snapshot_date,
        listing_id=ListingId("591", "1"),
        price_amount=price,
    )


class TestPriceHistoryChart:
    def test_writes_a_valid_png(self, tmp_path: Path) -> None:
        out = tmp_path / "history.png"
        snaps = [
            _snap(date(2026, 5, 1), 1_000_000),
            _snap(date(2026, 5, 5), 980_000),
            _snap(date(2026, 5, 9), 950_000),
        ]
        result = render_price_history_chart(snaps, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        assert out.read_bytes()[:8] == PNG_MAGIC

    def test_raises_on_empty_input(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="empty"):
            render_price_history_chart([], tmp_path / "x.png")

    def test_uses_supplied_title(self, tmp_path: Path) -> None:
        # We can't easily inspect the rendered text without parsing the PNG,
        # but we can at least exercise the title path so it doesn't crash.
        out = tmp_path / "titled.png"
        render_price_history_chart(
            [_snap(date(2026, 5, 1), 1_000_000)],
            out,
            title="Custom title",
        )
        assert out.stat().st_size > 0

    def test_handles_single_snapshot(self, tmp_path: Path) -> None:
        out = tmp_path / "single.png"
        render_price_history_chart([_snap(date(2026, 5, 1), 1_000_000)], out)
        assert out.exists()


def _summary(
    *,
    district: str,
    median: float | None,
    p25: float | None = None,
    p75: float | None = None,
    count: int = 5,
) -> DistrictSummary:
    return DistrictSummary(
        snapshot_date=date(2026, 5, 9),
        district=district,
        listing_count=count,
        median_price_amount=25_000_000.0,
        median_unit_price_per_ping=median,
        p25_unit_price_per_ping=p25,
        p75_unit_price_per_ping=p75,
    )


class TestUnitPriceDistributionChart:
    def test_writes_a_valid_png(self, tmp_path: Path) -> None:
        out = tmp_path / "dist.png"
        summaries = [
            _summary(district="大安區", median=85.0, p25=75.0, p75=95.0),
            _summary(district="信義區", median=100.0, p25=90.0, p75=110.0),
        ]
        result = render_unit_price_distribution_chart(
            summaries, out, snapshot_date=date(2026, 5, 9)
        )
        assert result == out
        assert out.exists()
        assert out.read_bytes()[:8] == PNG_MAGIC

    def test_drops_districts_without_unit_price(self, tmp_path: Path) -> None:
        out = tmp_path / "filtered.png"
        summaries = [
            _summary(district="A", median=80.0, p25=70.0, p75=90.0),
            _summary(district="B", median=None),  # no unit price
        ]
        # Should not raise; "B" is filtered out silently.
        render_unit_price_distribution_chart(
            summaries, out, snapshot_date=date(2026, 5, 9)
        )
        assert out.exists()

    def test_raises_when_no_district_has_unit_price(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="no districts"):
            render_unit_price_distribution_chart(
                [_summary(district="A", median=None)],
                tmp_path / "empty.png",
                snapshot_date=date(2026, 5, 9),
            )

    def test_raises_on_empty_input(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            render_unit_price_distribution_chart(
                [], tmp_path / "empty.png", snapshot_date=date(2026, 5, 9)
            )

    def test_handles_single_district(self, tmp_path: Path) -> None:
        out = tmp_path / "one.png"
        render_unit_price_distribution_chart(
            [_summary(district="A", median=80.0, p25=70.0, p75=90.0)],
            out,
            snapshot_date=date(2026, 5, 9),
        )
        assert out.exists()
