"""WatchlistRepository port.

Manual watchlist of listings the user wants tracked closely.
Saved queries (auto-resolved watchlists) live in a separate port.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.watchlist import WatchedListing


class WatchlistRepository(Protocol):
    def initialize(self) -> None:
        """Create schema if absent. Idempotent."""

    def add(
        self, listing_id: ListingId, *, nickname: str | None = None
    ) -> WatchedListing:
        """Add a listing to the watchlist (or update its nickname).

        Returns the stored WatchedListing (with `added_at` populated).
        Idempotent on (site, external_id): re-adding updates nickname
        but does NOT bump added_at.
        """

    def remove(self, listing_id: ListingId) -> bool:
        """Remove a listing from the watchlist.

        Returns True if a row was removed, False if it wasn't watched.
        """

    def get(self, listing_id: ListingId) -> WatchedListing | None:
        """Return the WatchedListing for `listing_id`, or None if not watched."""

    def list_all(self, *, site: str | None = None) -> Sequence[WatchedListing]:
        """All watched listings, oldest first. Optionally site-filtered."""
