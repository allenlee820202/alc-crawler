"""Site parser ports.

Each target site (591, Yungching) implements these to translate raw HTML
into domain `CanonicalListing` objects. This is the anti-corruption layer that
isolates the domain from site-specific quirks.
"""
from __future__ import annotations

from typing import Protocol

from alc_crawler.domain.canonical_listing import CanonicalListing


class SearchPageParser(Protocol):
    def parse(self, html: str, *, source_url: str) -> list[CanonicalListing]: ...


class DetailPageParser(Protocol):
    def parse(self, html: str, *, source_url: str) -> CanonicalListing: ...
