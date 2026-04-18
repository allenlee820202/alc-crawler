"""Unit tests for 591 parsing helpers (price, address, attributes)."""
from __future__ import annotations

import pytest

from alc_crawler.adapters.sites.site_591.parsing_helpers import (
    parse_attribute_tokens,
    parse_chinese_price,
    parse_taiwan_address,
)


class TestParseChinesePrice:
    @pytest.mark.parametrize(
        ("num", "unit", "expected"),
        [
            ("1,580", "萬", 15_800_000),
            ("1580", "萬", 15_800_000),
            ("8,800", "萬", 88_000_000),
            ("1.2", "億", 120_000_000),
            ("100", "", 100),  # no unit -> raw integer
        ],
    )
    def test_known_units(self, num: str, unit: str, expected: int) -> None:
        assert parse_chinese_price(num, unit) == expected

    def test_invalid_input_returns_none(self) -> None:
        assert parse_chinese_price("價格議定", "") is None
        assert parse_chinese_price("", "萬") is None


class TestParseTaiwanAddress:
    @pytest.mark.parametrize(
        ("raw", "city", "district"),
        [
            ("台北市大安區仁愛路四段", "台北市", "大安區"),
            ("新北市板橋區文化路一段", "新北市", "板橋區"),
            ("高雄市左營區博愛二路", "高雄市", "左營區"),
        ],
    )
    def test_extracts_city_and_district(self, raw: str, city: str, district: str) -> None:
        addr = parse_taiwan_address(raw)
        assert addr is not None
        assert addr.city == city
        assert addr.district == district
        assert addr.raw == raw

    def test_unparseable_returns_none(self) -> None:
        assert parse_taiwan_address("地址保密") is None


class TestParseAttributeTokens:
    def test_extracts_layout_size_floor(self) -> None:
        attrs = parse_attribute_tokens(["3房2廳", "28.5坪", "5/12樓"])
        assert attrs == {"layout": "3房2廳", "size_ping": "28.5", "floor": "5/12"}

    def test_unknown_tokens_ignored(self) -> None:
        attrs = parse_attribute_tokens(["3房2廳", "電梯大樓"])
        assert attrs == {"layout": "3房2廳"}
