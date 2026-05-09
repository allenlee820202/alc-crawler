"""record_daily_snapshots use case.

Reads every CanonicalListing currently in the canonical store and
writes one ListingSnapshot per listing dated `today` into the tracking
store. Called once per day (cron) immediately after a successful crawl.

Idempotency: the SnapshotRepository uses ON CONFLICT DO UPDATE keyed on
(snapshot_date, site, external_id), so re-running on the same day is
safe and overwrites.

Boundary: this use case depends only on the ListingRepository port
(read side, async iter_all) and the SnapshotRepository port. It knows
nothing about SQLite or DuckDB.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from alc_crawler.application.ports.listing_repository import ListingRepository
from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.tracking.application.ports.snapshot_repository import (
    SnapshotRepository,
)
from alc_crawler.tracking.domain.snapshot import ListingSnapshot


@dataclass(frozen=True, slots=True)
class SnapshotResult:
    snapshot_date: date
    listings_persisted: int


class RecordDailySnapshots:
    """Use case: snapshot today's canonical state into the tracking store."""

    def __init__(
        self,
        reader: ListingRepository,
        repo: SnapshotRepository,
        *,
        batch_size: int = 500,
    ) -> None:
        self._reader = reader
        self._repo = repo
        self._batch_size = batch_size

    async def execute(self, today: date) -> SnapshotResult:
        self._repo.initialize()
        total = 0
        batch: list[ListingSnapshot] = []
        async for listing in self._reader.iter_all():
            batch.append(_to_snapshot(listing, today))
            if len(batch) >= self._batch_size:
                total += self._repo.record_snapshots(batch)
                batch.clear()
        if batch:
            total += self._repo.record_snapshots(batch)
        return SnapshotResult(snapshot_date=today, listings_persisted=total)


def _to_snapshot(listing: CanonicalListing, snapshot_date: date) -> ListingSnapshot:
    """Map a CanonicalListing to a ListingSnapshot for `snapshot_date`."""
    return ListingSnapshot(
        snapshot_date=snapshot_date,
        listing_id=listing.id,
        price_amount=listing.price.amount,
        area_ping=listing.area_ping,
        unit_price_per_ping=listing.unit_price_per_ping,
        house_age_years=listing.house_age_years,
        view_count=listing.view_count,
        community_name=listing.community_name,
        address_district=listing.address.district,
        shape=listing.attributes.get("shape"),
        source_attributes_json=(
            json.dumps(listing.attributes, ensure_ascii=False, sort_keys=True)
            if listing.attributes
            else None
        ),
    )
