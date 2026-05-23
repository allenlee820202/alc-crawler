"""Yungching API parser — orchestrator over decryption + raw extraction + canonical mapping.

Chains:
  1. `parse_raw_items` (raw_item.py) — decrypt + JSON -> typed `YungchingRawItem`.
  2. `YungchingMapper.to_canonical` (mapper.py) — raw -> `CanonicalListing`.

Conforms to the `SearchPageParser` protocol.
"""
from __future__ import annotations

from alc_crawler.adapters.sites.site_yungching.mapper import YungchingMapper
from alc_crawler.adapters.sites.site_yungching.raw_item import parse_raw_items
from alc_crawler.domain.canonical_listing import CanonicalListing


class YungchingApiParser:
    def __init__(self, mapper: YungchingMapper | None = None) -> None:
        self._mapper = mapper or YungchingMapper()

    def parse(self, body: str, *, source_url: str) -> list[CanonicalListing]:
        del source_url  # unused; kept for SearchPageParser protocol compatibility
        results: list[CanonicalListing] = []
        for raw in parse_raw_items(body):
            try:
                results.append(self._mapper.to_canonical(raw))
            except ValueError:
                # Canonical invariant violation. Drop the item rather than
                # fail the page.
                continue
        return results
