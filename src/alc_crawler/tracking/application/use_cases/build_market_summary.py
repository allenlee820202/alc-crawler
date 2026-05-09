"""build_market_summary use case.

Aggregates one day's snapshots into per-district stats: listing count,
median total price, and the 25/50/75 percentile of unit price per ping.

Stats use stdlib `statistics`. Listings without a unit_price_per_ping
are still counted in `listing_count` but excluded from unit-price
percentiles. Districts with no listings are not emitted (the caller
asks for "what's in the data today", not "every possible district").
Snapshots with empty/None district are bucketed under "(unknown)" so
they don't silently disappear from totals.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from alc_crawler.tracking.application.ports.snapshot_repository import (
    SnapshotRepository,
)
from alc_crawler.tracking.domain.district_summary import DistrictSummary
from alc_crawler.tracking.domain.snapshot import ListingSnapshot

_UNKNOWN_DISTRICT = "(unknown)"


@dataclass(frozen=True, slots=True)
class BuildMarketSummary:
    repo: SnapshotRepository

    def execute(
        self,
        snapshot_date: date,
        *,
        site: str | None = None,
    ) -> Sequence[DistrictSummary]:
        snapshots = self.repo.snapshots_on_date(snapshot_date, site=site)
        if not snapshots:
            return []
        buckets: dict[str, list[ListingSnapshot]] = defaultdict(list)
        for s in snapshots:
            key = (s.address_district or "").strip() or _UNKNOWN_DISTRICT
            buckets[key].append(s)
        summaries = [
            self._summarise(snapshot_date, district, items)
            for district, items in buckets.items()
        ]
        # Largest district first; reports tend to lead with the busiest area.
        summaries.sort(key=lambda d: (-d.listing_count, d.district))
        return summaries

    @staticmethod
    def _summarise(
        snapshot_date: date,
        district: str,
        items: list[ListingSnapshot],
    ) -> DistrictSummary:
        prices = [s.price_amount for s in items]
        unit_prices = [
            s.unit_price_per_ping
            for s in items
            if s.unit_price_per_ping is not None
        ]
        median_price = statistics.median(prices) if prices else None
        if unit_prices:
            median_unit = statistics.median(unit_prices)
            p25, p75 = _quartiles(unit_prices)
        else:
            median_unit = None
            p25 = None
            p75 = None
        return DistrictSummary(
            snapshot_date=snapshot_date,
            district=district,
            listing_count=len(items),
            median_price_amount=float(median_price) if median_price is not None else None,
            median_unit_price_per_ping=median_unit,
            p25_unit_price_per_ping=p25,
            p75_unit_price_per_ping=p75,
        )


def _quartiles(values: list[float]) -> tuple[float, float]:
    """Return (p25, p75). Falls back to min/max for n=1, low/high for n=2.

    statistics.quantiles needs n>=2; for tiny samples we degrade gracefully
    instead of raising — daily reports must not crash on a sparse district.
    """
    if len(values) == 1:
        only = values[0]
        return only, only
    if len(values) == 2:
        lo, hi = sorted(values)
        return lo, hi
    qs = statistics.quantiles(values, n=4, method="inclusive")
    return qs[0], qs[2]
