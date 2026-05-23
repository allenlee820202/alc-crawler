"""Unit tests for hbhousing raw item parsing."""

from __future__ import annotations

import json

import pytest

from alc_crawler.adapters.sites.site_hbhousing.raw_item import parse_raw_items


def _make_nuxt_html(listings: list[dict[str, object]], total_count: int = 10) -> str:
    """Build a fake HTML page with a __NUXT_DATA__ payload containing the listings."""
    # Build the devalue array.
    data: list[object] = []

    # Reserve indices for listing schemas and values.
    listing_schema_indices: list[int] = []
    for listing in listings:
        schema: dict[str, int] = {}
        for key, value in listing.items():
            value_idx = len(data)
            data.append(value)
            schema[key] = value_idx
        schema_idx = len(data)
        data.append(schema)
        listing_schema_indices.append(schema_idx)

    # Array of listing indices.
    array_idx = len(data)
    data.append(listing_schema_indices)

    # Total count.
    cnts_idx = len(data)
    data.append(total_count)

    # Container dict.
    container_idx = len(data)
    data.append({"buyHouseListDatas": array_idx, "cnts": cnts_idx})

    # Ensure container_idx is used (it's just the last element).
    _ = container_idx

    payload_json = json.dumps(data)
    return (
        "<html><body>"
        '<script type="application/json" data-nuxt-data="nuxt-app" '
        f'id="__NUXT_DATA__">{payload_json}</script>'
        "</body></html>"
    )


class TestParseRawItems:
    def test_parses_valid_listing(self) -> None:
        html = _make_nuxt_html(
            [
                {
                    "sn": "ZS187442",
                    "objName": "近捷運三房美寓",
                    "price": 2580,
                    "room": 3,
                    "hall": 2,
                    "bath": 2,
                    "area": 35.5,
                    "mainArea": 25.0,
                    "style": "大樓",
                    "doorplate": "內湖區康寧路三段",
                    "floor": "5",
                    "floorTotal": "12",
                    "age": 15.3,
                }
            ],
            total_count=42,
        )

        items, total = parse_raw_items(html)
        assert total == 42
        assert len(items) == 1

        item = items[0]
        assert item.sn == "ZS187442"
        assert item.obj_name == "近捷運三房美寓"
        assert item.price == 2580
        assert item.room == 3
        assert item.hall == 2
        assert item.bath == 2
        assert item.area == 35.5
        assert item.main_area == 25.0
        assert item.style == "大樓"
        assert item.doorplate == "內湖區康寧路三段"
        assert item.floor == "5"
        assert item.floor_total == "12"
        assert item.age == 15.3

    def test_drops_missing_sn(self) -> None:
        html = _make_nuxt_html(
            [
                {
                    "objName": "No SN Listing",
                    "price": 1000,
                }
            ]
        )
        items, _ = parse_raw_items(html)
        assert items == []

    def test_drops_missing_price(self) -> None:
        html = _make_nuxt_html(
            [
                {
                    "sn": "ZS001",
                    "objName": "No Price",
                }
            ]
        )
        items, _ = parse_raw_items(html)
        assert items == []

    def test_drops_zero_price(self) -> None:
        html = _make_nuxt_html(
            [
                {
                    "sn": "ZS001",
                    "objName": "Zero Price",
                    "price": 0,
                }
            ]
        )
        items, _ = parse_raw_items(html)
        assert items == []

    def test_drops_missing_obj_name(self) -> None:
        html = _make_nuxt_html(
            [
                {
                    "sn": "ZS001",
                    "price": 1000,
                }
            ]
        )
        items, _ = parse_raw_items(html)
        assert items == []

    def test_multiple_items_with_some_invalid(self) -> None:
        html = _make_nuxt_html(
            [
                {"sn": "ZS001", "objName": "Good", "price": 1000},
                {"sn": "ZS002", "price": 2000},  # Missing objName
                {"sn": "ZS003", "objName": "Also Good", "price": 3000},
            ]
        )
        items, _ = parse_raw_items(html)
        assert len(items) == 2
        assert items[0].sn == "ZS001"
        assert items[1].sn == "ZS003"

    def test_optional_fields_default_to_none(self) -> None:
        html = _make_nuxt_html(
            [
                {
                    "sn": "ZS001",
                    "objName": "Minimal",
                    "price": 500,
                }
            ]
        )
        items, _ = parse_raw_items(html)
        assert len(items) == 1
        item = items[0]
        assert item.room is None
        assert item.hall is None
        assert item.bath is None
        assert item.area is None
        assert item.style is None
        assert item.mrt is None
        assert item.parking is None

    def test_raises_on_invalid_html(self) -> None:
        with pytest.raises(ValueError):
            parse_raw_items("<html><body>no nuxt data</body></html>")

    def test_raw_item_is_frozen(self) -> None:
        html = _make_nuxt_html(
            [
                {
                    "sn": "ZS001",
                    "objName": "Test",
                    "price": 1000,
                }
            ]
        )
        items, _ = parse_raw_items(html)
        with pytest.raises(AttributeError):
            items[0].sn = "changed"  # type: ignore[misc]
