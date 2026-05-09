"""detect_price_changes use case.

Compares each listing's earliest snapshot at-or-after `since` with its
latest snapshot at-or-before `until`. Returns one PriceChange per
listing whose price actually moved between those two boundary days.

Window semantics chosen for the daily-cron use case:
- 'since' is the *anchor* — first observed price within the window.
- 'until' is the *tip*   — last observed price within the window.
A listing that was added mid-window will compare its first day vs
last day (no false "price change" on its day-0 snapshot).
A listing that disappeared mid-window will use its last seen day
as the tip; the change reflects the last known movement.

Pure Python on top of two repository queries — no aggregation logic
in infrastructure beyond "give me the boundary snapshots".
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from alc_crawler.tracking.application.ports.snapshot_repository import (
    SnapshotRepository,
)
from alc_crawler.tracking.domain.price_change import PriceChange


@dataclass(frozen=True, slots=True)
class DetectPriceChanges:
    repo: SnapshotRepository

    def execute(
        self,
        *,
        since: date,
        until: date,
        site: str | None = None,
        only_drops: bool = False,
    ) -> Sequence[PriceChange]:
        if until < since:
            raise ValueError("until must be >= since")
        anchors = {
            s.listing_id: s
            for s in self.repo.earliest_snapshot_on_or_after(since, site=site)
        }
        tips = {
            s.listing_id: s
            for s in self.repo.latest_snapshot_on_or_before(until, site=site)
        }
        changes: list[PriceChange] = []
        for lid in anchors.keys() & tips.keys():
            anchor, tip = anchors[lid], tips[lid]
            if anchor.snapshot_date == tip.snapshot_date:
                continue  # only one snapshot inside the window — no movement to report
            if anchor.price_amount == tip.price_amount:
                continue  # listed but price unchanged
            change = PriceChange(
                listing_id=lid,
                from_date=anchor.snapshot_date,
                to_date=tip.snapshot_date,
                from_amount=anchor.price_amount,
                to_amount=tip.price_amount,
            )
            if only_drops and not change.is_drop:
                continue
            changes.append(change)
        # Stable ordering: largest absolute drop first, then by listing_id.
        changes.sort(key=lambda c: (-abs(c.delta_amount), str(c.listing_id)))
        return changes
