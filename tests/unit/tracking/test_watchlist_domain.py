"""Tests for the WatchedListing domain value object."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.watchlist import WatchedListing


class TestWatchedListing:
    def test_construct_with_minimal_fields(self) -> None:
        w = WatchedListing(
            listing_id=ListingId("591", "1"),
            added_at=datetime(2026, 5, 9, 12, 0, 0),
        )
        assert w.listing_id == ListingId("591", "1")
        assert w.added_at == datetime(2026, 5, 9, 12, 0, 0)
        assert w.nickname is None

    def test_construct_with_nickname(self) -> None:
        w = WatchedListing(
            listing_id=ListingId("591", "1"),
            added_at=datetime(2026, 5, 9, 12, 0, 0),
            nickname="dream home",
        )
        assert w.nickname == "dream home"

    def test_is_frozen(self) -> None:
        w = WatchedListing(
            listing_id=ListingId("591", "1"),
            added_at=datetime(2026, 5, 9),
        )
        with pytest.raises(FrozenInstanceError):
            w.nickname = "x"  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        a = WatchedListing(
            listing_id=ListingId("591", "1"),
            added_at=datetime(2026, 5, 9),
        )
        b = WatchedListing(
            listing_id=ListingId("591", "1"),
            added_at=datetime(2026, 5, 9),
        )
        assert a == b
