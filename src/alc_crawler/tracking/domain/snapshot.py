"""Daily snapshot of a listing's tracked fields.

A snapshot captures the state of one listing at the start of one
crawl day. The (snapshot_date, listing_id) pair is the natural
primary key. Snapshots are append-only — never mutate history.

Only fields useful for time-series analysis are tracked:
- price_amount, area_ping, unit_price_per_ping  (market signals)
- house_age_years, view_count                  (slow-moving + popularity)
- community_name, address_district, shape      (grouping/filtering)

Anything else lives in `source_attributes_json` for forensic re-mapping.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from alc_crawler.domain.value_objects import ListingId


@dataclass(frozen=True, slots=True)
class ListingSnapshot:
    snapshot_date: date
    listing_id: ListingId
    price_amount: int
    area_ping: float | None = None
    unit_price_per_ping: float | None = None
    house_age_years: int | None = None
    view_count: int | None = None
    community_name: str | None = None
    address_district: str | None = None
    shape: str | None = None
    source_attributes_json: str | None = None

    def __post_init__(self) -> None:
        if self.price_amount < 0:
            raise ValueError("ListingSnapshot.price_amount must be non-negative")
        if self.area_ping is not None and self.area_ping < 0:
            raise ValueError("ListingSnapshot.area_ping must be non-negative")
        if self.unit_price_per_ping is not None and self.unit_price_per_ping < 0:
            raise ValueError(
                "ListingSnapshot.unit_price_per_ping must be non-negative"
            )
        if self.house_age_years is not None and self.house_age_years < 0:
            raise ValueError("ListingSnapshot.house_age_years must be non-negative")
        if self.view_count is not None and self.view_count < 0:
            raise ValueError("ListingSnapshot.view_count must be non-negative")
