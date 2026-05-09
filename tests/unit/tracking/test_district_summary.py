"""Tests for DistrictSummary value object."""
from __future__ import annotations

from datetime import date

import pytest

from alc_crawler.tracking.domain.district_summary import DistrictSummary


def _summary(**overrides: object) -> DistrictSummary:
    base: dict[str, object] = {
        "snapshot_date": date(2026, 5, 9),
        "district": "大安區",
        "listing_count": 5,
        "median_price_amount": 25_000_000.0,
        "median_unit_price_per_ping": 80.0,
        "p25_unit_price_per_ping": 70.0,
        "p75_unit_price_per_ping": 90.0,
    }
    base.update(overrides)
    return DistrictSummary(**base)  # type: ignore[arg-type]


def test_district_summary_holds_fields() -> None:
    s = _summary()
    assert s.listing_count == 5
    assert s.district == "大安區"


def test_district_summary_rejects_blank_district() -> None:
    with pytest.raises(ValueError, match="district"):
        _summary(district="  ")


def test_district_summary_rejects_negative_count() -> None:
    with pytest.raises(ValueError, match="listing_count"):
        _summary(listing_count=-1)


def test_district_summary_allows_none_stats() -> None:
    s = _summary(
        median_price_amount=None,
        median_unit_price_per_ping=None,
        p25_unit_price_per_ping=None,
        p75_unit_price_per_ping=None,
    )
    assert s.median_unit_price_per_ping is None


def test_district_summary_zero_count_allowed() -> None:
    """Defensive: zero-count summaries are technically valid even if the use
    case doesn't emit them."""
    s = _summary(listing_count=0)
    assert s.listing_count == 0
