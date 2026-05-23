"""Unit tests for hbhousing Nuxt devalue payload extraction."""

from __future__ import annotations

import json

import pytest

from alc_crawler.adapters.sites.site_hbhousing.nuxt_payload import (
    extract_nuxt_payload,
    resolve_listings,
)


def _make_html(payload: list[object]) -> str:
    """Helper to wrap a JSON payload in a valid __NUXT_DATA__ script tag."""
    return (
        "<html><body>"
        '<script type="application/json" data-nuxt-data="nuxt-app" '
        f'id="__NUXT_DATA__">{json.dumps(payload)}</script>'
        "</body></html>"
    )


class TestExtractNuxtPayload:
    def test_extracts_payload_from_html(self) -> None:
        payload = [1, 2, "hello", {"key": 0}]
        html = _make_html(payload)
        result = extract_nuxt_payload(html)
        assert result == payload

    def test_raises_on_missing_script_tag(self) -> None:
        with pytest.raises(ValueError, match="No __NUXT_DATA__"):
            extract_nuxt_payload("<html><body></body></html>")

    def test_raises_on_invalid_json(self) -> None:
        html = (
            "<html><body>"
            '<script type="application/json" data-nuxt-data="nuxt-app" '
            'id="__NUXT_DATA__">not json</script>'
            "</body></html>"
        )
        with pytest.raises(ValueError, match="Invalid JSON"):
            extract_nuxt_payload(html)

    def test_raises_on_non_array_payload(self) -> None:
        html = (
            "<html><body>"
            '<script type="application/json" data-nuxt-data="nuxt-app" '
            'id="__NUXT_DATA__">{"not": "array"}</script>'
            "</body></html>"
        )
        with pytest.raises(ValueError, match="not a JSON array"):
            extract_nuxt_payload(html)


class TestResolveListings:
    def test_resolves_single_listing(self) -> None:
        # Build a minimal devalue payload:
        # Index 0: "sn"
        # Index 1: "ZS001"
        # Index 2: "objName"
        # Index 3: "Test Listing"
        # Index 4: "price"
        # Index 5: 2000
        # Index 6: listing schema dict {sn: 1, objName: 3, price: 5}
        # Index 7: array of listing indices [6]
        # Index 8: "buyHouseListDatas"
        # Index 9: "cnts"
        # Index 10: 1
        # Index 11: container dict {buyHouseListDatas: 7, cnts: 10}
        data: list[object] = [
            "sn",  # 0
            "ZS001",  # 1
            "objName",  # 2
            "Test Listing",  # 3
            "price",  # 4
            2000,  # 5
            {"sn": 1, "objName": 3, "price": 5},  # 6: listing schema
            [6],  # 7: listing indices array
            "buyHouseListDatas",  # 8
            "cnts",  # 9
            1,  # 10: total count
            {"buyHouseListDatas": 7, "cnts": 10},  # 11: container
        ]

        listings, total_count = resolve_listings(data)
        assert total_count == 1
        assert len(listings) == 1
        assert listings[0]["sn"] == "ZS001"
        assert listings[0]["objName"] == "Test Listing"
        assert listings[0]["price"] == 2000

    def test_resolves_multiple_listings(self) -> None:
        data: list[object] = [
            "ZS001",  # 0
            "Listing A",  # 1
            1000,  # 2
            "ZS002",  # 3
            "Listing B",  # 4
            2000,  # 5
            {"sn": 0, "objName": 1, "price": 2},  # 6: listing 1 schema
            {"sn": 3, "objName": 4, "price": 5},  # 7: listing 2 schema
            [6, 7],  # 8: listing indices array
            25,  # 9: total count
            {"buyHouseListDatas": 8, "cnts": 9},  # 10: container
        ]

        listings, total_count = resolve_listings(data)
        assert total_count == 25
        assert len(listings) == 2
        assert listings[0]["sn"] == "ZS001"
        assert listings[1]["sn"] == "ZS002"

    def test_raises_on_missing_container(self) -> None:
        data: list[object] = ["no", "container", "here"]
        with pytest.raises(ValueError, match="No dict with 'buyHouseListDatas'"):
            resolve_listings(data)

    def test_handles_empty_listings(self) -> None:
        data: list[object] = [
            [],  # 0: empty listing indices
            0,  # 1: total count
            {"buyHouseListDatas": 0, "cnts": 1},  # 2: container
        ]
        listings, total_count = resolve_listings(data)
        assert listings == []
        assert total_count == 0
