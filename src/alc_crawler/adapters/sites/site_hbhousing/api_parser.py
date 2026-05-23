"""Hbhousing API parser — orchestrator over Nuxt payload extraction + canonical mapping.

Chains:
  1. `parse_raw_items` (raw_item.py) — HTML -> typed `HbhousingRawItem`.
  2. `HbhousingMapper.to_canonical` (mapper.py) — raw -> `CanonicalListing`.

Conforms to the `SearchPageParser` protocol.
"""

from __future__ import annotations

import math

from alc_crawler.adapters.sites.site_hbhousing.mapper import HbhousingMapper
from alc_crawler.adapters.sites.site_hbhousing.raw_item import parse_raw_items
from alc_crawler.domain.canonical_listing import CanonicalListing

_PAGE_SIZE = 10


class HbhousingParser:
    def __init__(self, mapper: HbhousingMapper | None = None) -> None:
        self._mapper = mapper or HbhousingMapper()

    def parse(self, html: str, *, source_url: str) -> list[CanonicalListing]:
        """Parse an hbhousing HTML page into canonical listings."""
        del source_url  # unused; kept for SearchPageParser protocol compatibility
        items, _ = parse_raw_items(html)
        results: list[CanonicalListing] = []
        for raw in items:
            try:
                results.append(self._mapper.to_canonical(raw))
            except ValueError:
                # Canonical invariant violation. Drop the item rather than
                # fail the page.
                continue
        return results

    def total_pages(self, html: str) -> int:
        """Extract total page count from an hbhousing HTML page."""
        _, total_count = parse_raw_items(html)
        if total_count <= 0:
            return 0
        return math.ceil(total_count / _PAGE_SIZE)
