"""Listing aggregate root.

Represents a property listing observed on a source site. The aggregate
enforces invariants (non-empty title, valid URL) and exposes pure
domain operations like `with_observed_at`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from alc_crawler.domain.value_objects import Address, ListingId, Price


@dataclass(frozen=True, slots=True)
class Listing:
    id: ListingId
    title: str
    url: str
    price: Price
    address: Address
    observed_at: datetime | None = None
    attributes: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Listing.title must not be blank")
        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ValueError("Listing.url must be an http(s) url")

    def with_observed_at(self, ts: datetime) -> Listing:
        """Return a new Listing with `observed_at` updated (immutability preserved)."""
        return replace(self, observed_at=ts)
