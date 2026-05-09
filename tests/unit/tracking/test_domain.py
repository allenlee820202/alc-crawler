"""Tests for tracking domain value objects."""
from __future__ import annotations

from datetime import date

import pytest

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.lifecycle import (
    LifecycleStatus,
    classify_status,
)
from alc_crawler.tracking.domain.price_change import PriceChange
from alc_crawler.tracking.domain.snapshot import ListingSnapshot


def _snap(**overrides: object) -> ListingSnapshot:
    base: dict[str, object] = {
        "snapshot_date": date(2026, 5, 9),
        "listing_id": ListingId("591", "20037271"),
        "price_amount": 36_680_000,
        "area_ping": 81.39,
        "unit_price_per_ping": 45.07,
        "house_age_years": 34,
        "view_count": 616,
        "community_name": "正翔翠庭",
        "address_district": "文山區",
        "shape": "電梯大樓",
    }
    base.update(overrides)
    return ListingSnapshot(**base)  # type: ignore[arg-type]


class TestListingSnapshot:
    def test_snapshot_holds_required_fields(self) -> None:
        snap = _snap()
        assert snap.snapshot_date == date(2026, 5, 9)
        assert snap.listing_id.site == "591"
        assert snap.price_amount == 36_680_000

    def test_snapshot_rejects_negative_price(self) -> None:
        with pytest.raises(ValueError, match="price_amount"):
            _snap(price_amount=-1)

    def test_snapshot_rejects_negative_area(self) -> None:
        with pytest.raises(ValueError, match="area_ping"):
            _snap(area_ping=-0.1)

    def test_snapshot_optional_fields_default_none(self) -> None:
        snap = ListingSnapshot(
            snapshot_date=date(2026, 5, 9),
            listing_id=ListingId("591", "1"),
            price_amount=1_000_000,
        )
        assert snap.area_ping is None
        assert snap.community_name is None
        assert snap.shape is None
        assert snap.source_attributes_json is None

    def test_snapshot_is_immutable(self) -> None:
        from dataclasses import FrozenInstanceError

        snap = _snap()
        with pytest.raises(FrozenInstanceError):
            snap.price_amount = 1  # type: ignore[misc]


class TestLifecycleStatus:
    def test_classify_on_sale_when_seen_today(self) -> None:
        today = date(2026, 5, 9)
        assert classify_status(last_seen=today, today=today) == LifecycleStatus.ON_SALE

    def test_classify_on_sale_within_one_day(self) -> None:
        today = date(2026, 5, 9)
        yesterday = date(2026, 5, 8)
        assert (
            classify_status(last_seen=yesterday, today=today) == LifecycleStatus.ON_SALE
        )

    def test_classify_stale_within_three_days(self) -> None:
        today = date(2026, 5, 9)
        for days in (2, 3):
            ls = date(2026, 5, 9 - days)
            assert classify_status(last_seen=ls, today=today) == LifecycleStatus.STALE

    def test_classify_off_sale_after_three_days(self) -> None:
        today = date(2026, 5, 9)
        ls = date(2026, 5, 5)  # 4 days ago
        assert classify_status(last_seen=ls, today=today) == LifecycleStatus.OFF_SALE

    def test_classify_uses_custom_thresholds(self) -> None:
        today = date(2026, 5, 9)
        ls = date(2026, 5, 7)
        # tighter: only "today" counts as on_sale
        assert (
            classify_status(
                last_seen=ls, today=today, on_sale_days=0, stale_days=1
            )
            == LifecycleStatus.OFF_SALE
        )

    def test_classify_rejects_inverted_thresholds(self) -> None:
        with pytest.raises(ValueError, match="thresholds"):
            classify_status(
                last_seen=date(2026, 5, 9),
                today=date(2026, 5, 9),
                on_sale_days=5,
                stale_days=2,
            )


class TestPriceChange:
    def test_price_change_computes_delta_and_pct(self) -> None:
        change = PriceChange(
            listing_id=ListingId("591", "1"),
            from_date=date(2026, 5, 1),
            to_date=date(2026, 5, 9),
            from_amount=4_000_000,
            to_amount=3_800_000,
        )
        assert change.delta_amount == -200_000
        assert change.delta_pct == pytest.approx(-5.0)
        assert change.is_drop is True

    def test_price_change_rise(self) -> None:
        change = PriceChange(
            listing_id=ListingId("591", "1"),
            from_date=date(2026, 5, 1),
            to_date=date(2026, 5, 9),
            from_amount=3_000_000,
            to_amount=3_300_000,
        )
        assert change.delta_pct == pytest.approx(10.0)
        assert change.is_drop is False

    def test_price_change_rejects_zero_from_amount(self) -> None:
        with pytest.raises(ValueError, match="from_amount"):
            PriceChange(
                listing_id=ListingId("591", "1"),
                from_date=date(2026, 5, 1),
                to_date=date(2026, 5, 9),
                from_amount=0,
                to_amount=1,
            )

    def test_price_change_rejects_inverted_dates(self) -> None:
        with pytest.raises(ValueError, match="dates"):
            PriceChange(
                listing_id=ListingId("591", "1"),
                from_date=date(2026, 5, 9),
                to_date=date(2026, 5, 1),
                from_amount=1,
                to_amount=1,
            )
