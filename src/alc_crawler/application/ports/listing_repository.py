"""CanonicalListing repository port. Implementations: SQLite (today), Postgres (later)."""
from __future__ import annotations

from typing import Protocol

from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import ListingId


class ListingRepository(Protocol):
    async def upsert(self, listing: CanonicalListing) -> None: ...
    async def get(self, listing_id: ListingId) -> CanonicalListing | None: ...
