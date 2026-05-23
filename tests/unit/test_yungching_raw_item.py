"""Unit tests for Yungching raw item parsing."""
from __future__ import annotations

from pathlib import Path

import pytest

from alc_crawler.adapters.sites.site_yungching.raw_item import (
    get_pagination_info,
    parse_raw_items,
)

_FIXTURE = Path(__file__).parents[1] / "fixtures" / "site_yungching" / "api_list_taipei_page1.json"


def _load_fixture() -> str:
    return _FIXTURE.read_text()


class TestParseRawItems:
    def test_parses_valid_items(self) -> None:
        items = parse_raw_items(_load_fixture())
        # 4 items in fixture, 2 valid (empty caseSId and zero price dropped)
        assert len(items) == 2

    def test_first_item_identity(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].case_id == "12345678"
        assert items[0].case_name == "大安區精美三房電梯華廈"

    def test_first_item_price(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].price_wan == 2580.0

    def test_first_item_address(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].address == "台北市大安區忠孝東路四段100號"

    def test_first_item_pin_info(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].pin_info.reg_area == 35.2
        assert items[0].pin_info.main_area == 28.5
        assert items[0].pin_info.porch_area == 3.8

    def test_first_item_floor_info(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].floor_info.from_floor == 5
        assert items[0].floor_info.up_floor == 12

    def test_first_item_pattern_info(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].pattern_info.room == 3
        assert items[0].pattern_info.living_room == 2
        assert items[0].pattern_info.bath_room == 2

    def test_first_item_build_age(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].build_age == 15.3

    def test_first_item_community(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].community_name == "忠孝大廈"

    def test_first_item_tags(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].tags == ("近捷運", "低總價")

    def test_first_item_mrt(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].mrt_infos == ("忠孝敦化站", "忠孝復興站")

    def test_first_item_discount(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[0].is_discount is True
        assert items[0].down_ratio == 3.7
        assert items[0].last_price == 2680.0

    def test_second_item_identity(self) -> None:
        items = parse_raw_items(_load_fixture())
        assert items[1].case_id == "87654321"
        assert items[1].case_name == "信義區豪華四房景觀宅"

    def test_drops_item_without_case_id(self) -> None:
        items = parse_raw_items(_load_fixture())
        ids = [item.case_id for item in items]
        assert "" not in ids

    def test_drops_item_with_zero_price(self) -> None:
        items = parse_raw_items(_load_fixture())
        ids = [item.case_id for item in items]
        assert "99999999" not in ids

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_raw_items("not json at all")

    def test_non_success_status_raises(self) -> None:
        import json

        body = json.dumps({"status": "Error", "data": ""})
        with pytest.raises(ValueError, match="non-success status"):
            parse_raw_items(body)


class TestGetPaginationInfo:
    def test_returns_pagination(self) -> None:
        total_pages, total_items = get_pagination_info(_load_fixture())
        assert total_pages == 5
        assert total_items == 142
