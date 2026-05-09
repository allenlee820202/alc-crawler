"""DistrictSummary: aggregate market stats for one district on one day."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class DistrictSummary:
    snapshot_date: date
    district: str
    listing_count: int
    median_price_amount: float | None
    median_unit_price_per_ping: float | None
    p25_unit_price_per_ping: float | None
    p75_unit_price_per_ping: float | None

    def __post_init__(self) -> None:
        if not self.district.strip():
            raise ValueError("DistrictSummary.district must not be empty")
        if self.listing_count < 0:
            raise ValueError("DistrictSummary.listing_count must be non-negative")
