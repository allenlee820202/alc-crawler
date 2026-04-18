"""SQLite-backed implementation of ListingRepository.

Uses stdlib `sqlite3` wrapped in `asyncio.to_thread` to keep the async port.
This keeps zero extra deps; can be swapped to aiosqlite/Postgres later.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from alc_crawler.domain.listing import Listing
from alc_crawler.domain.value_objects import Address, ListingId, Price

_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    site             TEXT NOT NULL,
    external_id      TEXT NOT NULL,
    title            TEXT NOT NULL,
    url              TEXT NOT NULL,
    price_amount     INTEGER NOT NULL,
    price_currency   TEXT NOT NULL,
    address_city     TEXT NOT NULL,
    address_district TEXT NOT NULL,
    address_raw      TEXT NOT NULL,
    observed_at      TEXT,
    attributes_json  TEXT NOT NULL DEFAULT '{}',
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

    async def upsert(self, listing: Listing) -> None:
        await asyncio.to_thread(self._upsert_sync, listing)

    def _upsert_sync(self, listing: Listing) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO listings (
                    site, external_id, title, url,
                    price_amount, price_currency,
                    address_city, address_district, address_raw,
                    observed_at, attributes_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(site, external_id) DO UPDATE SET
                    title=excluded.title,
                    url=excluded.url,
                    price_amount=excluded.price_amount,
                    price_currency=excluded.price_currency,
                    address_city=excluded.address_city,
                    address_district=excluded.address_district,
                    address_raw=excluded.address_raw,
                    observed_at=excluded.observed_at,
                    attributes_json=excluded.attributes_json
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
                ),
            )

    async def get(self, listing_id: ListingId) -> Listing | None:
        return await asyncio.to_thread(self._get_sync, listing_id)

    def _get_sync(self, listing_id: ListingId) -> Listing | None:
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.execute(
                "SELECT title, url, price_amount, price_currency, "
                "address_city, address_district, address_raw, "
                "observed_at, attributes_json "
                "FROM listings WHERE site=? AND external_id=?",
                (listing_id.site, listing_id.external_id),
            )
            row = cur.fetchone()
        if row is None:
            return None
        (
            title,
            url,
            price_amount,
            price_currency,
            city,
            district,
            raw_addr,
            observed_at,
            attrs_json,
        ) = row
        return Listing(
            id=listing_id,
            title=title,
            url=url,
            price=Price(amount=price_amount, currency=price_currency),
            address=Address(city=city, district=district, raw=raw_addr),
            observed_at=datetime.fromisoformat(observed_at) if observed_at else None,
            attributes=json.loads(attrs_json),
        )
