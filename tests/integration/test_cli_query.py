"""Integration tests for the `alc-crawler query` CLI subcommand."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from typer.testing import CliRunner

from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import Address, ListingId, Price
from alc_crawler.infrastructure.persistence.sqlite.listing_repository import (
    SqliteListingRepository,
)
from alc_crawler.interfaces.cli.main import app

pytestmark = pytest.mark.integration


def _seed(db_path: Path) -> None:
    repo = SqliteListingRepository(db_path)
    asyncio.run(repo.initialize())

    listings = [
        # Within budget, age, district -> match for the user's query.
        CanonicalListing(
            id=ListingId("591", "match-1"),
            title="建國南路三房",
            url="https://sale.591.com.tw/home/house/detail/2/match-1.html",
            price=Price(33_000_000, "TWD"),
            address=Address(city="台北市", district="大安區", raw="建國南路123號"),
            attributes={"shape": "電梯大樓"},
            area_ping=32.5,
            unit_price_per_ping=101.5,
            house_age_years=18,
            community_name="建國華廈",
            room_layout="3房2廳2衛",
            floor="5F/12F",
        ),
        CanonicalListing(
            id=ListingId("591", "match-2"),
            title="復興南路老公寓",
            url="https://sale.591.com.tw/home/house/detail/2/match-2.html",
            price=Price(28_000_000, "TWD"),
            address=Address(city="台北市", district="大安區", raw="復興南路二段50號"),
            attributes={"shape": "公寓"},
            area_ping=28.0,
            unit_price_per_ping=100.0,
            house_age_years=30,
            community_name="",
            room_layout="2房2廳1衛",
            floor="3F/4F",
        ),
        # Over budget.
        CanonicalListing(
            id=ListingId("591", "too-expensive"),
            title="豪宅",
            url="https://sale.591.com.tw/home/house/detail/2/too-expensive.html",
            price=Price(50_000_000, "TWD"),
            address=Address(city="台北市", district="大安區", raw="瑞光路100號"),
            attributes={"shape": "電梯大樓"},
            area_ping=80.0,
            house_age_years=5,
        ),
        # Too old.
        CanonicalListing(
            id=ListingId("591", "too-old"),
            title="老老公寓",
            url="https://sale.591.com.tw/home/house/detail/2/too-old.html",
            price=Price(20_000_000, "TWD"),
            address=Address(city="台北市", district="大安區", raw="行善路1號"),
            attributes={"shape": "公寓"},
            area_ping=25.0,
            house_age_years=45,
        ),
        # Wrong district.
        CanonicalListing(
            id=ListingId("591", "wrong-district"),
            title="信義美屋",
            url="https://sale.591.com.tw/home/house/detail/2/wrong-district.html",
            price=Price(30_000_000, "TWD"),
            address=Address(city="台北市", district="信義區", raw="信義路五段1號"),
            attributes={"shape": "電梯大樓"},
            area_ping=30.0,
            house_age_years=10,
        ),
        # Wrong shape (透天厝).
        CanonicalListing(
            id=ListingId("591", "wrong-shape"),
            title="大安透天",
            url="https://sale.591.com.tw/home/house/detail/2/wrong-shape.html",
            price=Price(34_000_000, "TWD"),
            address=Address(city="台北市", district="大安區", raw="文德路200號"),
            attributes={"shape": "透天厝"},
            area_ping=40.0,
            house_age_years=20,
        ),
    ]
    for listing in listings:
        asyncio.run(repo.upsert(listing))


def test_query_filters_by_district_shape_price_age(tmp_path: Path) -> None:
    db = tmp_path / "q.sqlite"
    _seed(db)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "query",
            "--db",
            str(db),
            "--section-name",
            "大安區",
            "--shape-name",
            "公寓",
            "--shape-name",
            "電梯大樓",
            "--max-price-wan",
            "3500",
            "--max-age",
            "32",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "match-1" in result.output
    assert "match-2" in result.output
    assert "too-expensive" not in result.output
    assert "too-old" not in result.output
    assert "wrong-district" not in result.output
    assert "wrong-shape" not in result.output
    assert "matches: 2" in result.output


def test_query_address_contains_filter(tmp_path: Path) -> None:
    db = tmp_path / "q.sqlite"
    _seed(db)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "query",
            "--db",
            str(db),
            "--section-name",
            "大安區",
            "--address-contains",
            "建國",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "match-1" in result.output
    assert "match-2" not in result.output


def test_query_missing_db_errors_helpfully(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app, ["query", "--db", str(tmp_path / "missing.sqlite")]
    )
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_query_filters_by_room_range(tmp_path: Path) -> None:
    db = tmp_path / "q.sqlite"
    _seed(db)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "query",
            "--db",
            str(db),
            "--section-name",
            "大安區",
            "--min-rooms",
            "2",
            "--max-rooms",
            "3",
        ],
    )

    assert result.exit_code == 0, result.output
    # match-1 (3房) and match-2 (2房) qualify; too-expensive/too-old/wrong-shape
    # have no room_layout seeded so should be excluded by the room filter.
    assert "match-1" in result.output
    assert "match-2" in result.output
    assert "too-expensive" not in result.output
    assert "too-old" not in result.output
    assert "wrong-shape" not in result.output


def test_query_no_matches_prints_message(tmp_path: Path) -> None:
    db = tmp_path / "q.sqlite"
    _seed(db)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "query",
            "--db",
            str(db),
            "--section-name",
            "中正區",  # no seeded data there
        ],
    )
    assert result.exit_code == 0
    assert "(no matches)" in result.output
