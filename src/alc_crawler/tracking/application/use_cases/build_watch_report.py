"""Use case: build a per-listing report for everything on the watchlist.

Combines the WatchlistRepository (which listings to report on) with
the SnapshotRepository (their history). Pure orchestration — all
arithmetic is in the WatchReportEntry value object or here, no SQL
in the use case.

Lifecycle classification uses the existing tracking thresholds:
ON_SALE within 1 day, STALE within 3 days, OFF_SALE beyond that.
Pass `today` explicitly so reports are reproducible (cron + golden
tests).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from alc_crawler.tracking.application.ports.snapshot_repository import (
    SnapshotRepository,
)
from alc_crawler.tracking.application.ports.watchlist_repository import (
    WatchlistRepository,
)
from alc_crawler.tracking.domain.lifecycle import classify_status
from alc_crawler.tracking.domain.snapshot import ListingSnapshot
from alc_crawler.tracking.domain.watch_report import WatchReportEntry
from alc_crawler.tracking.domain.watchlist import WatchedListing


@dataclass
class BuildWatchReport:
    watchlist_repo: WatchlistRepository
    snapshot_repo: SnapshotRepository

    def execute(
        self,
        *,
        today: date,
        site: str | None = None,
    ) -> Sequence[WatchReportEntry]:
        watched = self.watchlist_repo.list_all(site=site)
        return [self._build_entry(w, today=today) for w in watched]

    def _build_entry(
        self, watch: WatchedListing, *, today: date
    ) -> WatchReportEntry:
        snaps = self.snapshot_repo.snapshots_for_listing(watch.listing_id)
        if not snaps:
            return WatchReportEntry(
                listing_id=watch.listing_id,
                nickname=watch.nickname,
                snapshot_count=0,
                first_seen_date=None,
                last_seen_date=None,
                days_on_market=None,
                first_price=None,
                latest_price=None,
                min_price=None,
                min_price_date=None,
                max_price=None,
                max_price_date=None,
                lifecycle_status=None,
                latest_district=None,
                latest_community=None,
            )
        # snapshots_for_listing returns oldest first.
        first = snaps[0]
        last = snaps[-1]
        min_snap = min(snaps, key=lambda s: s.price_amount)
        max_snap = max(snaps, key=lambda s: s.price_amount)
        return WatchReportEntry(
            listing_id=watch.listing_id,
            nickname=watch.nickname,
            snapshot_count=len(snaps),
            first_seen_date=first.snapshot_date,
            last_seen_date=last.snapshot_date,
            days_on_market=(last.snapshot_date - first.snapshot_date).days,
            first_price=first.price_amount,
            latest_price=last.price_amount,
            min_price=min_snap.price_amount,
            min_price_date=min_snap.snapshot_date,
            max_price=max_snap.price_amount,
            max_price_date=max_snap.snapshot_date,
            lifecycle_status=classify_status(
                last_seen=last.snapshot_date, today=today
            ),
            latest_district=last.address_district,
            latest_community=last.community_name,
        )


# Re-export for convenient typing in tests.
__all__ = ["BuildWatchReport", "ListingSnapshot"]
