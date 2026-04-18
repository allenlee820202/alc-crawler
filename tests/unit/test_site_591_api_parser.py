"""Tests for the 591 JSON API parser, driven by a real fixture from
the live BFF endpoint (sanitized; no PII concerns).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from alc_crawler.adapters.sites.site_591.api_parser import Site591ApiParser

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "site_591"


@pytest.fixture
def api_body() -> str:
    return (FIXTURES / "api_search_taipei_page1.json").read_text(encoding="utf-8")


def test_parse_returns_listings(api_body: str) -> None:
    parser = Site591ApiParser()

    listings = parser.parse(api_body, source_url="https://bff-house.591.com.tw/v1/web/sale/list")

    assert len(listings) > 0
    assert all(listing.id.site == "591" for listing in listings)


def test_parse_extracts_external_id_as_houseid(api_body: str) -> None:
    parser = Site591ApiParser()

    listings = parser.parse(api_body, source_url="https://x")

    assert all(listing.id.external_id.isdigit() for listing in listings)


def test_parse_builds_canonical_detail_url(api_body: str) -> None:
    parser = Site591ApiParser()

    listings = parser.parse(api_body, source_url="https://x")

    listing = listings[0]
    assert listing.url.startswith("https://sale.591.com.tw/home/house/detail/2/")
    assert listing.url.endswith(f"{listing.id.external_id}.html")


def test_parse_converts_price_in_wan_to_twd(api_body: str) -> None:
    parser = Site591ApiParser()

    listings = parser.parse(api_body, source_url="https://x")

    # API returns price in 萬 (e.g. 3668 means 36,680,000 TWD)
    listing = listings[0]
    assert listing.price.currency == "TWD"
    assert listing.price.amount > 0
    # Sanity: TPE properties are typically >= 1M TWD
    assert listing.price.amount >= 1_000_000


def test_parse_extracts_address(api_body: str) -> None:
    parser = Site591ApiParser()

    listings = parser.parse(api_body, source_url="https://x")

    listing = listings[0]
    assert listing.address.city == "台北市"
    assert listing.address.district  # non-empty


def test_parse_attributes_include_room_floor_area(api_body: str) -> None:
    parser = Site591ApiParser()

    listings = parser.parse(api_body, source_url="https://x")

    listing = listings[0]
    # Most listings have a room layout and floor; allow some tolerance.
    assert listing.attributes.get("room") or listing.attributes.get("floor")


def test_parse_skips_malformed_items() -> None:
    parser = Site591ApiParser()
    body = (
        '{"status":1,"data":{"house_list":['
        '{"houseid":1},'  # missing required fields
        '{"houseid":2,"title":"ok","region_name":"\u53f0\u5317\u5e02",'
        '"section_name":"\u5927\u5b89\u5340","address":"x","price":100}'
        "]}}"
    )

    listings = parser.parse(body, source_url="https://x")

    assert len(listings) == 1
    assert listings[0].id.external_id == "2"


def test_parse_invalid_json_raises_value_error() -> None:
    parser = Site591ApiParser()
    with pytest.raises(ValueError):
        parser.parse("not json", source_url="https://x")


def test_parse_non_success_status_raises() -> None:
    parser = Site591ApiParser()
    with pytest.raises(ValueError, match="status"):
        parser.parse('{"status":0,"data":{"house_list":[]}}', source_url="https://x")
