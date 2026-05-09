"""591 BFF JSON parser — orchestrator over raw extraction + canonical mapping.

The live 591 site is a Vue/Nuxt SPA; listings are loaded by the browser
via XHR to https://bff-house.591.com.tw/v1/web/sale/list. Parsing is a
two-stage pipeline:

  1. `parse_raw_items` (raw_item.py) — JSON -> typed `Site591RawItem`.
  2. `Site591Mapper.to_canonical` (mapper.py) — raw -> `CanonicalListing`.

This class is a thin orchestrator that chains the two stages and conforms
to the `SearchPageParser` protocol so the crawl service can stay generic.
Catches canonical-invariant violations (e.g. malformed URL, blank title
post-coercion) and skips them so a single bad item does not abort a page.
"""
from __future__ import annotations

from alc_crawler.adapters.sites.site_591.mapper import Site591Mapper
from alc_crawler.adapters.sites.site_591.raw_item import parse_raw_items
from alc_crawler.domain.canonical_listing import CanonicalListing


class Site591ApiParser:
    def __init__(self, mapper: Site591Mapper | None = None) -> None:
        self._mapper = mapper or Site591Mapper()

    def parse(self, body: str, *, source_url: str) -> list[CanonicalListing]:
        del source_url  # unused; kept for SearchPageParser protocol compatibility
        results: list[CanonicalListing] = []
        for raw in parse_raw_items(body):
            try:
                results.append(self._mapper.to_canonical(raw))
            except ValueError:
                # Canonical invariant violation (e.g. invalid URL after
                # construction). Drop the item rather than fail the page.
                continue
        return results
