"""Tests for the 591 anti-corruption mapper.

This is the second stage of 591's parsing pipeline: typed raw items ->
`CanonicalListing`. The mapper is the only place that knows about both
591's shape and the canonical shape; adding a second site will introduce
a sibling mapper, never a change here.
"""
from __future__ import annotations

import pytest

from alc_crawler.adapters.sites.site_591.mapper import Site591Mapper
from alc_crawler.adapters.sites.site_591.raw_item import Site591RawItem


def _raw(**overrides: object) -> Site591RawItem:
    """Minimal valid raw item; override fields per test."""
    base: dict[str, object] = {
        "house_id": "12345",
        "title": "test listing",
        "region_name": "台北市",
        "section_name": "大安區",
        "address": "復興南路一段",
        "price_wan": 1500.0,
    }
    base.update(overrides)
    return Site591RawItem(**base)  # type: ignore[arg-type]


def test_to_canonical_builds_listing_id_from_site_and_house_id() -> None:
    mapper = Site591Mapper()

    listing = mapper.to_canonical(_raw(house_id="99999"))

    assert listing.id.site == "591"
    assert listing.id.external_id == "99999"


def test_to_canonical_converts_price_wan_to_twd() -> None:
    mapper = Site591Mapper()

    listing = mapper.to_canonical(_raw(price_wan=3668.0))

    assert listing.price.currency == "TWD"
    assert listing.price.amount == 36_680_000


def test_to_canonical_builds_detail_url_from_house_id() -> None:
    mapper = Site591Mapper()

    listing = mapper.to_canonical(_raw(house_id="20037271"))

    assert listing.url == "https://sale.591.com.tw/home/house/detail/2/20037271.html"


def test_to_canonical_packs_address_with_section_fallback_for_raw() -> None:
    mapper = Site591Mapper()

    with_addr = mapper.to_canonical(_raw(address="忠孝東路四段"))
    without_addr = mapper.to_canonical(_raw(address=""))

    assert with_addr.address.raw == "忠孝東路四段"
    assert without_addr.address.raw == "大安區"  # falls back to section
    assert with_addr.address.city == "台北市"
    assert with_addr.address.district == "大安區"


def test_to_canonical_promotes_optional_first_class_fields() -> None:
    mapper = Site591Mapper()

    listing = mapper.to_canonical(
        _raw(
            area=81.39,
            main_area=26.71,
            unit_price=45.07,
            house_age=34,
            room="4房3廳3衛",
            floor="B1~1F/2F",
            community_name="正翔翠庭",
            browsenum=616,
            posttime=1776170184,
        )
    )

    assert listing.area_ping == pytest.approx(81.39)
    assert listing.main_area_ping == pytest.approx(26.71)
    assert listing.unit_price_per_ping == pytest.approx(45.07)
    assert listing.house_age_years == 34
    assert listing.room_layout == "4房3廳3衛"
    assert listing.floor == "B1~1F/2F"
    assert listing.community_name == "正翔翠庭"
    assert listing.view_count == 616
    assert listing.posted_at is not None
    assert listing.posted_at.year == 2026


def test_to_canonical_packs_soft_fields_into_attributes() -> None:
    mapper = Site591Mapper()

    listing = mapper.to_canonical(
        _raw(
            shape_name="電梯大樓",
            kind_name="住宅",
            housetype="3",
            unit_price_label="45.07萬/坪",
            nick_name="仲介葉迎",
            photo_num=17,
            is_video=1,
            condition_ids=(3, 7, 9),
        )
    )

    assert listing.attributes["shape"] == "電梯大樓"
    assert listing.attributes["kind"] == "住宅"
    assert listing.attributes["housetype"] == "3"
    assert listing.attributes["unit_price_label"] == "45.07萬/坪"
    assert listing.attributes["agent_nick_name"] == "仲介葉迎"
    assert listing.attributes["photo_count"] == "17"
    assert listing.attributes["has_video"] == "1"
    assert listing.attributes["condition_ids"] == "3,7,9"


def test_to_canonical_omits_absent_soft_fields_from_attributes() -> None:
    mapper = Site591Mapper()

    listing = mapper.to_canonical(_raw())

    assert listing.attributes == {}


def test_to_canonical_omits_posted_at_when_posttime_missing() -> None:
    mapper = Site591Mapper()

    listing = mapper.to_canonical(_raw(posttime=None))

    assert listing.posted_at is None
