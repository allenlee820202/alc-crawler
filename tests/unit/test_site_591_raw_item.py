"""Tests for the 591 raw-item extractor.

This is the first stage of 591's parsing pipeline: BFF JSON -> typed
`Site591RawItem` records. No domain mapping happens here; only JSON
shape validation and minimal type coercion. Items missing identity
(house_id) or price are dropped to anchor downstream invariants.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from alc_crawler.adapters.sites.site_591.raw_item import (
    Site591RawItem,
    parse_raw_items,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "site_591"


@pytest.fixture
def api_body() -> str:
    return (FIXTURES / "api_search_taipei_page1.json").read_text(encoding="utf-8")


def test_parse_raw_items_returns_typed_records(api_body: str) -> None:
    items = parse_raw_items(api_body)

    assert len(items) > 0
    assert all(isinstance(item, Site591RawItem) for item in items)


def test_parse_raw_items_preserves_known_listing_fields(api_body: str) -> None:
    items = parse_raw_items(api_body)

    target = next(it for it in items if it.house_id == "20037271")
    # Identity & price preserved verbatim
    assert target.title == "住戶首選☎時尚~樟新街~七張站"
    assert target.region_name == "台北市"
    assert target.section_name == "文山區"
    assert target.address == "樟新街56巷"
    assert target.price_wan == pytest.approx(3668.0)
    # Optional first-class fields
    assert target.area == pytest.approx(81.39)
    assert target.main_area == pytest.approx(26.71)
    assert target.unit_price == pytest.approx(45.07)
    assert target.house_age == 34
    assert target.room == "4房3廳3衛"
    assert target.floor == "B1~1F/2F"
    assert target.posttime == 1776170184
    assert target.browsenum == 616
    # Soft fields (preserved as raw strings)
    assert target.shape_name == "電梯大樓"
    assert target.kind_name == "住宅"
    assert target.nick_name == "仲介葉迎"
    assert target.photo_num == 17
    assert target.is_video == 1


def test_parse_raw_items_skips_items_missing_identity() -> None:
    body = (
        '{"status":1,"data":{"house_list":['
        '{"houseid":1},'                                    # missing title/region/section/price
        '{"title":"x","region_name":"a","section_name":"b","price":100},'  # missing houseid
        '{"houseid":2,"title":"ok","region_name":"台北市",'
        '"section_name":"大安區","address":"x","price":100}'
        "]}}"
    )

    items = parse_raw_items(body)

    assert [it.house_id for it in items] == ["2"]


def test_parse_raw_items_skips_zero_or_negative_price() -> None:
    body = (
        '{"status":1,"data":{"house_list":['
        '{"houseid":1,"title":"a","region_name":"r","section_name":"s","address":"x","price":0},'
        '{"houseid":2,"title":"b","region_name":"r","section_name":"s","address":"x","price":-5},'
        '{"houseid":3,"title":"c","region_name":"r","section_name":"s","address":"x","price":100}'
        "]}}"
    )

    items = parse_raw_items(body)

    assert [it.house_id for it in items] == ["3"]


def test_parse_raw_items_coerces_numeric_strings() -> None:
    body = (
        '{"status":1,"data":{"house_list":[{'
        '"houseid":1,"title":"a","region_name":"r","section_name":"s","address":"x",'
        '"price":"100","unitprice":"45.07","houseage":"12","browsenum":"42"'
        "}]}}"
    )

    items = parse_raw_items(body)

    assert items[0].price_wan == pytest.approx(100.0)
    assert items[0].unit_price == pytest.approx(45.07)
    assert items[0].house_age == 12
    assert items[0].browsenum == 42


def test_parse_raw_items_treats_negative_optional_numerics_as_none() -> None:
    body = (
        '{"status":1,"data":{"house_list":[{'
        '"houseid":1,"title":"a","region_name":"r","section_name":"s","address":"x",'
        '"price":100,"area":-1,"houseage":-3,"browsenum":-7'
        "}]}}"
    )

    items = parse_raw_items(body)

    assert items[0].area is None
    assert items[0].house_age is None
    assert items[0].browsenum is None


def test_parse_raw_items_extracts_condition_ids_as_tuple() -> None:
    body = (
        '{"status":1,"data":{"house_list":[{'
        '"houseid":1,"title":"a","region_name":"r","section_name":"s","address":"x",'
        '"price":100,"conditionids":[3,7,9]'
        "}]}}"
    )

    items = parse_raw_items(body)

    assert items[0].condition_ids == (3, 7, 9)


def test_parse_raw_items_invalid_json_raises() -> None:
    with pytest.raises(ValueError, match="JSON"):
        parse_raw_items("not json")


def test_parse_raw_items_non_success_status_raises() -> None:
    with pytest.raises(ValueError, match="status"):
        parse_raw_items('{"status":0,"data":{"house_list":[]}}')


def test_parse_raw_items_empty_house_list_returns_empty() -> None:
    items = parse_raw_items('{"status":1,"data":{"house_list":[]}}')
    assert items == []
