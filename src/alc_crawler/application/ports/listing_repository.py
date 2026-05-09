"""CanonicalListing repository port. Implementations: SQLite (today), Postgres (later)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import ListingId


class ListingRepository(Protocol):
    async def upsert(self, listing: CanonicalListing) -> None: ...
    async def get(self, listing_id: ListingId) -> CanonicalListing | None: ...
    def iter_all(self) -> AsyncIterator[CanonicalListing]:
        """Yield every persisted CanonicalListing.

        Returned as an async iterator so implementations can stream
        rows without buffering the entire table; callers (notably the
        tracking snapshot use case) are expected to consume in one
        pass within a `async for`.
        """
        ...
