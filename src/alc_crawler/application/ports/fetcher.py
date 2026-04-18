"""HTTP fetcher port (interface).

Adapters: httpx (default), Playwright (for JS-heavy pages).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    status: int
    body: str


class HttpFetcher(Protocol):
    async def get(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> FetchResult: ...
