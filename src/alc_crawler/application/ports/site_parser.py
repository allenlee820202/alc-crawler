"""Site parser ports.

Each target site (591, Yungching) implements these to translate raw HTML
into domain `Listing` objects. This is the anti-corruption layer that
isolates the domain from site-specific quirks.
"""
from __future__ import annotations

from typing import Protocol

from alc_crawler.domain.listing import Listing


class SearchPageParser(Protocol):
    def parse(self, html: str, *, source_url: str) -> list[Listing]: ...


class DetailPageParser(Protocol):
    def parse(self, html: str, *, source_url: str) -> Listing: ...
