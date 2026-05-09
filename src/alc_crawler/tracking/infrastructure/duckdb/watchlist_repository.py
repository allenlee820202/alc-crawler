"""DuckDB-backed implementation of WatchlistRepository.

Reuses the same `schema.sql` (and database file) as the snapshot
repository — a single tracking DuckDB owns both tables. Each method
opens its own short-lived connection (DuckDB single-writer model).
"""
from __future__ import annotations

from collections.abc import Sequence
from contextlib import contextmanager
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Any

import duckdb

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.watchlist import WatchedListing

_SCHEMA_RESOURCE = ("alc_crawler.tracking.infrastructure.duckdb", "schema.sql")


class DuckDbWatchlistRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    @contextmanager
    def _connect(self) -> Any:
        conn = duckdb.connect(str(self._db_path))
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        schema_sql = (
            resources.files(_SCHEMA_RESOURCE[0])
            .joinpath(_SCHEMA_RESOURCE[1])
            .read_text(encoding="utf-8")
        )
        with self._connect() as conn:
            conn.execute(schema_sql)

    def add(
        self, listing_id: ListingId, *, nickname: str | None = None
    ) -> WatchedListing:
        # Idempotent: keep original added_at on conflict, only refresh nickname.
        # Using INSERT ... ON CONFLICT DO UPDATE so a single statement covers
        # both "create new" and "update nickname" without a SELECT-then-write
        # race window.
        now = datetime.now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO watched_listings (site, external_id, nickname, added_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (site, external_id) DO UPDATE SET
                    nickname = excluded.nickname
                """,
                [listing_id.site, listing_id.external_id, nickname, now],
            )
        # Re-read to return the canonical stored record (preserves the
        # original added_at if this was an update).
        got = self.get(listing_id)
        assert got is not None  # we just wrote it
        return got

    def remove(self, listing_id: ListingId) -> bool:
        with self._connect() as conn:
            # DuckDB does not support RETURNING on DELETE in all versions,
            # so we check existence first. Safe under our single-writer model.
            existed = conn.execute(
                "SELECT 1 FROM watched_listings WHERE site = ? AND external_id = ?",
                [listing_id.site, listing_id.external_id],
            ).fetchone()
            if existed is None:
                return False
            conn.execute(
                "DELETE FROM watched_listings WHERE site = ? AND external_id = ?",
                [listing_id.site, listing_id.external_id],
            )
            return True

    def get(self, listing_id: ListingId) -> WatchedListing | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT site, external_id, nickname, added_at
                FROM watched_listings
                WHERE site = ? AND external_id = ?
                """,
                [listing_id.site, listing_id.external_id],
            ).fetchone()
        return self._row_to_watch(row) if row else None

    def list_all(self, *, site: str | None = None) -> Sequence[WatchedListing]:
        sql = "SELECT site, external_id, nickname, added_at FROM watched_listings"
        params: list[Any] = []
        if site is not None:
            sql += " WHERE site = ?"
            params.append(site)
        sql += " ORDER BY added_at ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_watch(r) for r in rows]

    @staticmethod
    def _row_to_watch(row: tuple[Any, ...]) -> WatchedListing:
        site, external_id, nickname, added_at = row
        return WatchedListing(
            listing_id=ListingId(site, external_id),
            added_at=added_at,
            nickname=nickname,
        )
