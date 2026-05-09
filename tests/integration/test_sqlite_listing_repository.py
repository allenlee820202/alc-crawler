"""Integration test for the SQLite ListingRepository adapter."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import Address, ListingId, Price
from alc_crawler.infrastructure.persistence.sqlite.listing_repository import (
    SqliteListingRepository,
)

pytestmark = pytest.mark.integration


def _listing(ext_id: str, *, title: str = "t", price: int = 1000) -> CanonicalListing:
    return CanonicalListing(
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


async def test_first_class_optional_fields_round_trip(db_path: Path) -> None:
    repo = SqliteListingRepository(db_path)
    await repo.initialize()

    posted = datetime(2025, 11, 18, tzinfo=UTC)
    rich = CanonicalListing(
        id=ListingId("591", "rich"),
        title="rich",
        url="https://example.com/rich",
        price=Price(36_680_000, "TWD"),
        address=Address(city="台北市", district="文山區", raw="文山區樟新街"),
        observed_at=datetime(2026, 4, 18, tzinfo=UTC),
        area_ping=81.39,
        main_area_ping=26.71,
        unit_price_per_ping=45.07,
        house_age_years=34,
        room_layout="4房3廳3衛",
        floor="B1~1F/2F",
        community_name="正翔翠庭",
        posted_at=posted,
        view_count=616,
    )
    await repo.upsert(rich)
    loaded = await repo.get(ListingId("591", "rich"))

    assert loaded == rich


async def test_first_class_optional_fields_default_to_none(db_path: Path) -> None:
    """Listings with no optional fields set should round-trip cleanly."""
    repo = SqliteListingRepository(db_path)
    await repo.initialize()

    minimal = CanonicalListing(
        id=ListingId("591", "minimal"),
        title="minimal",
        url="https://example.com/m",
        price=Price(1, "TWD"),
        address=Address(city="台北市", district="大安區", raw="x"),
    )
    await repo.upsert(minimal)
    loaded = await repo.get(ListingId("591", "minimal"))
    assert loaded == minimal
    assert loaded is not None
    assert loaded.area_ping is None
    assert loaded.posted_at is None
