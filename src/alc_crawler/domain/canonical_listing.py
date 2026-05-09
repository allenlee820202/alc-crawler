"""CanonicalListing aggregate root.

The single, cross-site shape that downstream consumers (SQLite repo,
`query` CLI, future analytics) target. Per-site adapters are responsible
for producing their own site-shaped Raw types and mapping to this
canonical form via an anti-corruption layer (e.g. `Site591Mapper`).

Adding a new site MUST NOT extend this class with site-specific fields;
put those on the site's Raw type, or — if they are genuinely useful
across sites — promote them deliberately here in a separate change.

Invariants enforced: non-empty title, http(s) URL, non-negative numerics.
First-class fields are reserved for data we expect to filter/sort on
in queries (area, price-per-ping, age, posted_at, view_count, etc.).
Softer presentational data lives in `attributes` to avoid an
ever-growing column set.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from alc_crawler.domain.value_objects import Address, ListingId, Price


@dataclass(frozen=True, slots=True)
class CanonicalListing:
    id: ListingId
    title: str
    url: str
    price: Price
    address: Address
    observed_at: datetime | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    # Optional first-class fields, populated when the source provides them.
    area_ping: float | None = None
    main_area_ping: float | None = None
    unit_price_per_ping: float | None = None
    house_age_years: int | None = None
    room_layout: str | None = None
    floor: str | None = None
    community_name: str | None = None
    posted_at: datetime | None = None
    view_count: int | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("CanonicalListing.title must not be blank")
        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ValueError("CanonicalListing.url must be an http(s) url")
        if self.area_ping is not None and self.area_ping < 0:
            raise ValueError("CanonicalListing.area_ping must be non-negative")
        if self.main_area_ping is not None and self.main_area_ping < 0:
            raise ValueError("CanonicalListing.main_area_ping must be non-negative")
        if self.unit_price_per_ping is not None and self.unit_price_per_ping < 0:
            raise ValueError("CanonicalListing.unit_price_per_ping must be non-negative")
        if self.house_age_years is not None and self.house_age_years < 0:
            raise ValueError("CanonicalListing.house_age_years must be non-negative")
        if self.view_count is not None and self.view_count < 0:
            raise ValueError("CanonicalListing.view_count must be non-negative")

    def with_observed_at(self, ts: datetime) -> CanonicalListing:
        """Return a new CanonicalListing with `observed_at` updated (immutability preserved)."""
        return replace(self, observed_at=ts)
