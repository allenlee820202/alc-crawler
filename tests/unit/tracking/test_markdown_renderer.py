"""Tests for markdown report renderers."""
from __future__ import annotations

from datetime import date

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.district_summary import DistrictSummary
from alc_crawler.tracking.domain.price_change import PriceChange
from alc_crawler.tracking.interfaces.reports.markdown import (
    render_market_summary,
    render_price_changes,
)


class TestRenderPriceChanges:
    def test_renders_header_with_window(self) -> None:
        out = render_price_changes(
            [], since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert "## Price changes 2026-05-01 → 2026-05-09" in out

    def test_renders_empty_message_for_no_changes(self) -> None:
        out = render_price_changes(
            [], since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert "_No price changes in window._" in out
        assert "|" not in out  # no table

    def test_renders_one_row_per_change(self) -> None:
        changes = [
            PriceChange(
                listing_id=ListingId("591", "1"),
                from_date=date(2026, 5, 1),
                to_date=date(2026, 5, 9),
                from_amount=1_000_000,
                to_amount=950_000,
            ),
            PriceChange(
                listing_id=ListingId("591", "2"),
                from_date=date(2026, 5, 1),
                to_date=date(2026, 5, 9),
                from_amount=2_000_000,
                to_amount=2_100_000,
            ),
        ]
        out = render_price_changes(
            changes, since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert "`591:1`" in out
        assert "`591:2`" in out
        assert "1,000,000" in out
        assert "2,100,000" in out
        # Markdown table separator with right-alignment for numeric cols.
        assert "|---|---:|---:|---:|---:|" in out

    def test_includes_signed_delta_and_percentage(self) -> None:
        change = PriceChange(
            listing_id=ListingId("591", "1"),
            from_date=date(2026, 5, 1),
            to_date=date(2026, 5, 9),
            from_amount=1_000_000,
            to_amount=950_000,
        )
        out = render_price_changes(
            [change], since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert "-50,000" in out  # signed delta
        assert "-5.00%" in out  # signed percentage

    def test_site_suffix_appended_to_header(self) -> None:
        out = render_price_changes(
            [], since=date(2026, 5, 1), until=date(2026, 5, 9), site="591"
        )
        assert "(site=591)" in out

    def test_only_drops_suffix_appended_to_header(self) -> None:
        out = render_price_changes(
            [],
            since=date(2026, 5, 1),
            until=date(2026, 5, 9),
            only_drops=True,
        )
        assert "drops only" in out

    def test_combines_site_and_only_drops_suffixes(self) -> None:
        out = render_price_changes(
            [],
            since=date(2026, 5, 1),
            until=date(2026, 5, 9),
            site="591",
            only_drops=True,
        )
        assert "(site=591, drops only)" in out

    def test_output_ends_with_newline(self) -> None:
        out = render_price_changes(
            [], since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert out.endswith("\n")


class TestRenderMarketSummary:
    def test_renders_header_with_date(self) -> None:
        out = render_market_summary([], snapshot_date=date(2026, 5, 9))
        assert "## Market summary 2026-05-09" in out

    def test_renders_empty_message_for_no_summaries(self) -> None:
        out = render_market_summary([], snapshot_date=date(2026, 5, 9))
        assert "_No snapshots on this date._" in out
        assert "|" not in out

    def test_renders_one_row_per_district(self) -> None:
        summaries = [
            DistrictSummary(
                snapshot_date=date(2026, 5, 9),
                district="大安區",
                listing_count=12,
                median_price_amount=25_000_000.0,
                median_unit_price_per_ping=85.0,
                p25_unit_price_per_ping=75.0,
                p75_unit_price_per_ping=95.0,
            ),
            DistrictSummary(
                snapshot_date=date(2026, 5, 9),
                district="信義區",
                listing_count=8,
                median_price_amount=30_000_000.0,
                median_unit_price_per_ping=100.0,
                p25_unit_price_per_ping=90.0,
                p75_unit_price_per_ping=110.0,
            ),
        ]
        out = render_market_summary(summaries, snapshot_date=date(2026, 5, 9))
        assert "大安區" in out
        assert "信義區" in out
        assert "25,000,000" in out
        assert "85.0" in out
        assert "| District | Listings |" in out

    def test_renders_em_dash_for_none_values(self) -> None:
        summaries = [
            DistrictSummary(
                snapshot_date=date(2026, 5, 9),
                district="(unknown)",
                listing_count=1,
                median_price_amount=None,
                median_unit_price_per_ping=None,
                p25_unit_price_per_ping=None,
                p75_unit_price_per_ping=None,
            )
        ]
        out = render_market_summary(summaries, snapshot_date=date(2026, 5, 9))
        # 4 numeric columns should each render as the em-dash placeholder.
        assert out.count("—") >= 4

    def test_site_suffix(self) -> None:
        out = render_market_summary(
            [], snapshot_date=date(2026, 5, 9), site="591"
        )
        assert "(site=591)" in out
