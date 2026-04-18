"""Tests for the 591 search-page parser, driven by a representative fixture."""
from __future__ import annotations

from pathlib import Path

import pytest

from alc_crawler.adapters.sites.site_591.search_parser import Site591SearchParser

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "site_591"


@pytest.fixture
def search_html() -> str:
    return (FIXTURES / "search_taipei_page1.html").read_text(encoding="utf-8")


def test_parse_extracts_well_formed_listings(search_html: str) -> None:
    parser = Site591SearchParser()

    listings = parser.parse(
        search_html,
        source_url="https://sale.591.com.tw/?regionid=1",
    )

    assert len(listings) == 2  # malformed entry skipped
    ids = {listing.id.external_id for listing in listings}
    assert ids == {"12345", "67890"}


def test_parse_resolves_relative_urls(search_html: str) -> None:
    parser = Site591SearchParser()

    listings = parser.parse(
        search_html,
        source_url="https://sale.591.com.tw/?regionid=1",
    )

    listing = next(listing for listing in listings if listing.id.external_id == "12345")
    assert listing.url == "https://sale.591.com.tw/home/house/detail/2/12345.html"


def test_parse_converts_chinese_price_unit_to_twd(search_html: str) -> None:
    parser = Site591SearchParser()

    listings = parser.parse(search_html, source_url="https://sale.591.com.tw/")

    listing = next(listing for listing in listings if listing.id.external_id == "12345")
    # 1,580 萬 == 15_800_000 TWD
    assert listing.price.amount == 15_800_000
    assert listing.price.currency == "TWD"


def test_parse_extracts_address_city_and_district(search_html: str) -> None:
    parser = Site591SearchParser()

    listings = parser.parse(search_html, source_url="https://sale.591.com.tw/")

    listing = next(listing for listing in listings if listing.id.external_id == "67890")
    assert listing.address.city == "台北市"
    assert listing.address.district == "信義區"
    assert "松仁路" in listing.address.raw


def test_parse_captures_attributes(search_html: str) -> None:
    parser = Site591SearchParser()

    listings = parser.parse(search_html, source_url="https://sale.591.com.tw/")

    listing = next(listing for listing in listings if listing.id.external_id == "12345")
    assert listing.attributes.get("layout") == "3房2廳"
    assert listing.attributes.get("size_ping") == "28.5"
    assert listing.attributes.get("floor") == "5/12"


def test_empty_html_returns_empty_list() -> None:
    parser = Site591SearchParser()

    assert parser.parse("<html></html>", source_url="https://sale.591.com.tw/") == []
