"""Integration test for the SQLite ListingRepository adapter."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from alc_crawler.domain.listing import Listing
from alc_crawler.domain.value_objects import Address, ListingId, Price
from alc_crawler.infrastructure.persistence.sqlite.listing_repository import (
    SqliteListingRepository,
)

pytestmark = pytest.mark.integration


def _listing(ext_id: str, *, title: str = "t", price: int = 1000) -> Listing:
    return Listing(
        id=ListingId("591", ext_id),
        title=title,
        url=f"https://example.com/{ext_id}",
        price=Price(price, "TWD"),
        address=Address(city="台北市", district="大安區", raw="台北市大安區"),
        observed_at=datetime(2026, 4, 18, tzinfo=UTC),
        attributes={"floor": "5", "size_ping": "28.5"},
    )


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.sqlite"


async def test_upsert_then_get_round_trip(db_path: Path) -> None:
    repo = SqliteListingRepository(db_path)
    await repo.initialize()

    original = _listing("1", title="原標題", price=15_800_000)
    await repo.upsert(original)

    loaded = await repo.get(ListingId("591", "1"))
    assert loaded is not None
    assert loaded == original


async def test_upsert_updates_existing_row(db_path: Path) -> None:
    repo = SqliteListingRepository(db_path)
    await repo.initialize()

    await repo.upsert(_listing("1", title="v1"))
    await repo.upsert(_listing("1", title="v2"))

    loaded = await repo.get(ListingId("591", "1"))
    assert loaded is not None
    assert loaded.title == "v2"


async def test_get_returns_none_when_missing(db_path: Path) -> None:
    repo = SqliteListingRepository(db_path)
    await repo.initialize()

    assert await repo.get(ListingId("591", "missing")) is None


async def test_attributes_round_trip_as_json(db_path: Path) -> None:
    repo = SqliteListingRepository(db_path)
    await repo.initialize()

    listing = _listing("1")
    await repo.upsert(listing)
    loaded = await repo.get(ListingId("591", "1"))

    assert loaded is not None
    assert loaded.attributes == {"floor": "5", "size_ping": "28.5"}
