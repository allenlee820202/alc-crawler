"""SnapshotRepository port.

Synchronous on purpose: the tracking module runs as a batch job
(daily cron), not a server. DuckDB is a sync library; wrapping it
in async would add ceremony for no benefit.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Protocol

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.crawl_run import CrawlRun
from alc_crawler.tracking.domain.snapshot import ListingSnapshot


class SnapshotRepository(Protocol):
    def initialize(self) -> None:
        """Create schema if absent. Idempotent."""

    def record_snapshots(self, snapshots: Iterable[ListingSnapshot]) -> int:
        """Upsert snapshots; returns number of rows written."""

    def record_run(self, run: CrawlRun) -> None:
        """Persist a crawl run record."""

    def snapshots_for_listing(
        self,
        listing_id: ListingId,
        *,
        since: date | None = None,
    ) -> Sequence[ListingSnapshot]:
        """Return snapshots for one listing, oldest first."""

    def latest_snapshot_date(self, *, site: str) -> date | None:
        """Most recent snapshot_date stored for `site`, or None if empty."""
