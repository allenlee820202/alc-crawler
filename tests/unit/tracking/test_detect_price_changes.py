"""Tests for DetectPriceChanges use case (fake repo)."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pytest

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.application.use_cases.detect_price_changes import (
    DetectPriceChanges,
)
from alc_crawler.tracking.domain.snapshot import ListingSnapshot


def _snap(
    listing_id: ListingId,
    snapshot_date: date,
    price: int,
) -> ListingSnapshot:
    return ListingSnapshot(
        snapshot_date=snapshot_date,
        listing_id=listing_id,
        price_amount=price,
    )


class FakeRepo:
    """Repo that returns the ROW_NUMBER=1 boundary snapshots in pure Python."""

    def __init__(self, snapshots: list[ListingSnapshot]) -> None:
        self.snapshots = snapshots

    # Methods unused by the use case but required by the protocol.
    def initialize(self) -> None: ...
    def record_snapshots(self, snapshots) -> int:  # type: ignore[no-untyped-def]
        return 0
    def record_run(self, run) -> None: ...  # type: ignore[no-untyped-def]
    def snapshots_for_listing(self, listing_id, *, since=None):  # type: ignore[no-untyped-def]
        return []
    def latest_snapshot_date(self, *, site):  # type: ignore[no-untyped-def]
        return None

    def earliest_snapshot_on_or_after(
        self, anchor_date: date, *, site: str | None = None
    ) -> Sequence[ListingSnapshot]:
        chosen: dict[ListingId, ListingSnapshot] = {}
        for s in self.snapshots:
            if s.snapshot_date < anchor_date:
                continue
            if site is not None and s.listing_id.site != site:
                continue
            existing = chosen.get(s.listing_id)
            if existing is None or s.snapshot_date < existing.snapshot_date:
                chosen[s.listing_id] = s
        return list(chosen.values())

    def latest_snapshot_on_or_before(
        self, target_date: date, *, site: str | None = None
    ) -> Sequence[ListingSnapshot]:
        chosen: dict[ListingId, ListingSnapshot] = {}
        for s in self.snapshots:
            if s.snapshot_date > target_date:
                continue
            if site is not None and s.listing_id.site != site:
                continue
            existing = chosen.get(s.listing_id)
            if existing is None or s.snapshot_date > existing.snapshot_date:
                chosen[s.listing_id] = s
        return list(chosen.values())


L1 = ListingId("591", "1")
L2 = ListingId("591", "2")
L3 = ListingId("591", "3")


class TestExecute:
    def test_returns_empty_when_no_data(self) -> None:
        result = DetectPriceChanges(FakeRepo([])).execute(
            since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert list(result) == []

    def test_detects_price_drop(self) -> None:
        repo = FakeRepo(
            [
                _snap(L1, date(2026, 5, 1), 1_000_000),
                _snap(L1, date(2026, 5, 9), 950_000),
            ]
        )
        result = DetectPriceChanges(repo).execute(
            since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert len(result) == 1
        change = result[0]
        assert change.listing_id == L1
        assert change.from_amount == 1_000_000
        assert change.to_amount == 950_000
        assert change.delta_amount == -50_000
        assert change.is_drop

    def test_detects_price_rise(self) -> None:
        repo = FakeRepo(
            [
                _snap(L1, date(2026, 5, 1), 1_000_000),
                _snap(L1, date(2026, 5, 9), 1_050_000),
            ]
        )
        result = DetectPriceChanges(repo).execute(
            since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert len(result) == 1
        assert result[0].delta_amount == 50_000

    def test_only_drops_filter(self) -> None:
        repo = FakeRepo(
            [
                _snap(L1, date(2026, 5, 1), 1_000_000),
                _snap(L1, date(2026, 5, 9), 950_000),
                _snap(L2, date(2026, 5, 1), 1_000_000),
                _snap(L2, date(2026, 5, 9), 1_050_000),
            ]
        )
        result = DetectPriceChanges(repo).execute(
            since=date(2026, 5, 1), until=date(2026, 5, 9), only_drops=True
        )
        assert [c.listing_id for c in result] == [L1]

    def test_skips_unchanged_price(self) -> None:
        repo = FakeRepo(
            [
                _snap(L1, date(2026, 5, 1), 1_000_000),
                _snap(L1, date(2026, 5, 9), 1_000_000),
            ]
        )
        assert (
            list(
                DetectPriceChanges(repo).execute(
                    since=date(2026, 5, 1), until=date(2026, 5, 9)
                )
            )
            == []
        )

    def test_skips_listing_present_only_one_day(self) -> None:
        # Only one snapshot in the window — no movement to report.
        repo = FakeRepo([_snap(L1, date(2026, 5, 5), 1_000_000)])
        assert (
            list(
                DetectPriceChanges(repo).execute(
                    since=date(2026, 5, 1), until=date(2026, 5, 9)
                )
            )
            == []
        )

    def test_uses_earliest_in_window_as_anchor(self) -> None:
        # Listing existed before the window with a different price; we should
        # only compare snapshots inside the window.
        repo = FakeRepo(
            [
                _snap(L1, date(2026, 4, 1), 2_000_000),  # outside since
                _snap(L1, date(2026, 5, 2), 1_500_000),  # earliest in window
                _snap(L1, date(2026, 5, 8), 1_200_000),  # latest in window
            ]
        )
        result = DetectPriceChanges(repo).execute(
            since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert len(result) == 1
        assert result[0].from_amount == 1_500_000
        assert result[0].to_amount == 1_200_000

    def test_excludes_snapshots_after_until(self) -> None:
        repo = FakeRepo(
            [
                _snap(L1, date(2026, 5, 1), 1_000_000),
                _snap(L1, date(2026, 5, 5), 950_000),
                _snap(L1, date(2026, 5, 15), 800_000),  # after until
            ]
        )
        result = DetectPriceChanges(repo).execute(
            since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert len(result) == 1
        assert result[0].to_amount == 950_000

    def test_sorts_by_largest_absolute_change_first(self) -> None:
        repo = FakeRepo(
            [
                _snap(L1, date(2026, 5, 1), 1_000_000),
                _snap(L1, date(2026, 5, 9), 990_000),  # -10k
                _snap(L2, date(2026, 5, 1), 2_000_000),
                _snap(L2, date(2026, 5, 9), 1_500_000),  # -500k (largest)
                _snap(L3, date(2026, 5, 1), 1_000_000),
                _snap(L3, date(2026, 5, 9), 1_100_000),  # +100k
            ]
        )
        result = DetectPriceChanges(repo).execute(
            since=date(2026, 5, 1), until=date(2026, 5, 9)
        )
        assert [c.listing_id for c in result] == [L2, L3, L1]

    def test_filters_by_site(self) -> None:
        other = ListingId("rakuya", "9")
        repo = FakeRepo(
            [
                _snap(L1, date(2026, 5, 1), 1_000_000),
                _snap(L1, date(2026, 5, 9), 950_000),
                _snap(other, date(2026, 5, 1), 1_000_000),
                _snap(other, date(2026, 5, 9), 950_000),
            ]
        )
        result = DetectPriceChanges(repo).execute(
            since=date(2026, 5, 1), until=date(2026, 5, 9), site="591"
        )
        assert [c.listing_id for c in result] == [L1]

    def test_rejects_inverted_window(self) -> None:
        with pytest.raises(ValueError, match="until must be"):
            DetectPriceChanges(FakeRepo([])).execute(
                since=date(2026, 5, 9), until=date(2026, 5, 1)
            )

    def test_same_day_window_returns_no_changes(self) -> None:
        repo = FakeRepo(
            [
                _snap(L1, date(2026, 5, 5), 1_000_000),
                _snap(L1, date(2026, 5, 5), 1_000_000),
            ]
        )
        assert (
            list(
                DetectPriceChanges(repo).execute(
                    since=date(2026, 5, 5), until=date(2026, 5, 5)
                )
            )
            == []
        )
