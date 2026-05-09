"""CrawlRun: provenance record for one crawl invocation.

Recorded by the snapshot use case so downstream reports can flag
incomplete or failed runs ("today's price-change report excludes 大安區
because that crawl errored").
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RunStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CrawlRun:
    run_id: str
    started_at: datetime
    completed_at: datetime | None
    site: str
    region: str
    pages_fetched: int
    listings_seen: int
    listings_persisted: int
    status: RunStatus
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("CrawlRun.run_id must not be empty")
        if not self.site.strip():
            raise ValueError("CrawlRun.site must not be empty")
        if not self.region.strip():
            raise ValueError("CrawlRun.region must not be empty")
        if self.pages_fetched < 0:
            raise ValueError("CrawlRun.pages_fetched must be non-negative")
        if self.listings_seen < 0:
            raise ValueError("CrawlRun.listings_seen must be non-negative")
        if self.listings_persisted < 0:
            raise ValueError("CrawlRun.listings_persisted must be non-negative")
        if (
            self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("CrawlRun.completed_at must be >= started_at")
