"""SQLite-backed implementation of ListingRepository.

Uses stdlib `sqlite3` wrapped in `asyncio.to_thread` to keep the async port.
This keeps zero extra deps; can be swapped to aiosqlite/Postgres later.

Schema versioning: there is no migration system yet. The current strategy
is "drop and recreate" during early development. Add proper migrations
before any deployment that needs to retain prior data.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import Address, ListingId, Price

_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    site                 TEXT NOT NULL,
    external_id          TEXT NOT NULL,
    title                TEXT NOT NULL,
    url                  TEXT NOT NULL,
    price_amount         INTEGER NOT NULL,
    price_currency       TEXT NOT NULL,
    address_city         TEXT NOT NULL,
    address_district     TEXT NOT NULL,
    address_raw          TEXT NOT NULL,
    observed_at          TEXT,
    attributes_json      TEXT NOT NULL DEFAULT '{}',
    area_ping            REAL,
    main_area_ping       REAL,
    unit_price_per_ping  REAL,
    house_age_years      INTEGER,
    room_layout          TEXT,
    floor                TEXT,
    community_name       TEXT,
    posted_at            TEXT,
    view_count           INTEGER,
    PRIMARY KEY (site, external_id)
);
"""


class SqliteListingRepository:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)

    async def initialize(self) -> None:
        await asyncio.to_thread(self._init_sync)

    def _init_sync(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_SCHEMA)

    async def upsert(self, listing: CanonicalListing) -> None:
        await asyncio.to_thread(self._upsert_sync, listing)

    def _upsert_sync(self, listing: CanonicalListing) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO listings (
                    site, external_id, title, url,
                    price_amount, price_currency,
                    address_city, address_district, address_raw,
                    observed_at, attributes_json,
                    area_ping, main_area_ping, unit_price_per_ping,
                    house_age_years, room_layout, floor,
                    community_name, posted_at, view_count
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(site, external_id) DO UPDATE SET
                    title=excluded.title,
                    url=excluded.url,
                    price_amount=excluded.price_amount,
                    price_currency=excluded.price_currency,
                    address_city=excluded.address_city,
                    address_district=excluded.address_district,
                    address_raw=excluded.address_raw,
                    observed_at=excluded.observed_at,
                    attributes_json=excluded.attributes_json,
                    area_ping=excluded.area_ping,
                    main_area_ping=excluded.main_area_ping,
                    unit_price_per_ping=excluded.unit_price_per_ping,
                    house_age_years=excluded.house_age_years,
                    room_layout=excluded.room_layout,
                    floor=excluded.floor,
                    community_name=excluded.community_name,
                    posted_at=excluded.posted_at,
                    view_count=excluded.view_count
                """,
                (
                    listing.id.site,
                    listing.id.external_id,
                    listing.title,
                    listing.url,
                    listing.price.amount,
                    listing.price.currency,
                    listing.address.city,
                    listing.address.district,
                    listing.address.raw,
                    listing.observed_at.isoformat() if listing.observed_at else None,
                    json.dumps(listing.attributes, ensure_ascii=False, sort_keys=True),
                    listing.area_ping,
                    listing.main_area_ping,
                    listing.unit_price_per_ping,
                    listing.house_age_years,
                    listing.room_layout,
                    listing.floor,
                    listing.community_name,
                    listing.posted_at.isoformat() if listing.posted_at else None,
                    listing.view_count,
                ),
            )

    async def get(self, listing_id: ListingId) -> CanonicalListing | None:
        return await asyncio.to_thread(self._get_sync, listing_id)

    def _get_sync(self, listing_id: ListingId) -> CanonicalListing | None:
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.execute(
                "SELECT site, external_id, title, url, price_amount, price_currency, "
                "address_city, address_district, address_raw, "
                "observed_at, attributes_json, "
                "area_ping, main_area_ping, unit_price_per_ping, "
                "house_age_years, room_layout, floor, "
                "community_name, posted_at, view_count "
                "FROM listings WHERE site=? AND external_id=?",
                (listing_id.site, listing_id.external_id),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_listing(row)

    async def iter_all(self, *, batch_size: int = 500) -> AsyncIterator[CanonicalListing]:
        """Stream every listing.

        Fetches in `batch_size` chunks via `asyncio.to_thread` so we
        never load the full table into memory and never block the loop
        for more than one batch. The cursor lives in a worker thread
        for the duration of the iteration.
        """

        def _fetch_batch(cur: sqlite3.Cursor) -> list[tuple[Any, ...]]:
            return cur.fetchmany(batch_size)

        def _open_cursor() -> tuple[sqlite3.Connection, sqlite3.Cursor]:
            conn = sqlite3.connect(self._db_path)
            cur = conn.execute(
                "SELECT site, external_id, title, url, "
                "price_amount, price_currency, "
                "address_city, address_district, address_raw, "
                "observed_at, attributes_json, "
                "area_ping, main_area_ping, unit_price_per_ping, "
                "house_age_years, room_layout, floor, "
                "community_name, posted_at, view_count "
                "FROM listings ORDER BY site, external_id"
            )
            return conn, cur

        conn, cur = await asyncio.to_thread(_open_cursor)
        try:
            while True:
                rows = await asyncio.to_thread(_fetch_batch, cur)
                if not rows:
                    return
                for row in rows:
                    yield self._row_to_listing(row)
        finally:
            await asyncio.to_thread(conn.close)

    @staticmethod
    def _row_to_listing(row: tuple[Any, ...]) -> CanonicalListing:
        (
            site,
            external_id,
            title,
            url,
            price_amount,
            price_currency,
            city,
            district,
            raw_addr,
            observed_at,
            attrs_json,
            area_ping,
            main_area_ping,
            unit_price_per_ping,
            house_age_years,
            room_layout,
            floor,
            community_name,
            posted_at,
            view_count,
        ) = row
        return CanonicalListing(
            id=ListingId(site, external_id),
            title=title,
            url=url,
            price=Price(amount=price_amount, currency=price_currency),
            address=Address(city=city, district=district, raw=raw_addr),
            observed_at=datetime.fromisoformat(observed_at) if observed_at else None,
            attributes=json.loads(attrs_json),
            area_ping=area_ping,
            main_area_ping=main_area_ping,
            unit_price_per_ping=unit_price_per_ping,
            house_age_years=house_age_years,
            room_layout=room_layout,
            floor=floor,
            community_name=community_name,
            posted_at=datetime.fromisoformat(posted_at) if posted_at else None,
            view_count=view_count,
        )
