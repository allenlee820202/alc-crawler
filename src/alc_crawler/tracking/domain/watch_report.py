"""WatchReportEntry: per-watched-listing summary for the watch report.

Captures everything we want to display in one row of the report so
the renderer doesn't need to know about repositories or use cases.

Fields can be None when a watched listing has no snapshots yet
(e.g. just added before any crawl ran). The renderer treats None
as a placeholder.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.lifecycle import LifecycleStatus


@dataclass(frozen=True, slots=True)
class WatchReportEntry:
    listing_id: ListingId
    nickname: str | None
    snapshot_count: int
    first_seen_date: date | None
    last_seen_date: date | None
    days_on_market: int | None
    first_price: int | None
    latest_price: int | None
    min_price: int | None
    min_price_date: date | None
    max_price: int | None
    max_price_date: date | None
    lifecycle_status: LifecycleStatus | None
    latest_district: str | None
    latest_community: str | None

    @property
    def total_delta(self) -> int | None:
        if self.first_price is None or self.latest_price is None:
            return None
        return self.latest_price - self.first_price

    @property
    def total_delta_pct(self) -> float | None:
        if (
            self.first_price is None
            or self.latest_price is None
            or self.first_price == 0
        ):
            return None
        return (self.latest_price - self.first_price) / self.first_price * 100
