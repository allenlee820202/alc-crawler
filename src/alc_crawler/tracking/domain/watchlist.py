"""WatchedListing: a manually curated entry in the user's watchlist.

A watched listing is identified by its (site, external_id) pair.
`added_at` is set by the repository when the watch is created.
`nickname` is optional and exists purely to help the human remember
why they added it (e.g. "near 大安國中"); the system does not parse it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from alc_crawler.domain.value_objects import ListingId


@dataclass(frozen=True, slots=True)
class WatchedListing:
    listing_id: ListingId
    added_at: datetime
    nickname: str | None = None
