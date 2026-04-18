"""Tests for the Listing aggregate."""
from datetime import UTC, datetime

import pytest

from alc_crawler.domain.listing import Listing
from alc_crawler.domain.value_objects import Address, ListingId, Price


def _addr() -> Address:
    return Address(city="台北市", district="大安區", raw="台北市大安區仁愛路四段")


class TestListing:
    def test_create_minimal_listing(self) -> None:
        listing = Listing(
            id=ListingId("591", "12345"),
            title="精美兩房",
            url="https://sale.591.com.tw/home/house/detail/2/12345.html",
            price=Price(15_800_000, "TWD"),
            address=_addr(),
        )
        assert listing.id.external_id == "12345"
        assert listing.title == "精美兩房"

    def test_title_required(self) -> None:
        with pytest.raises(ValueError, match="title"):
            Listing(
                id=ListingId("591", "1"),
                title="   ",
                url="https://x",
                price=Price(1, "TWD"),
                address=_addr(),
            )

    def test_url_must_be_http(self) -> None:
        with pytest.raises(ValueError, match="url"):
            Listing(
                id=ListingId("591", "1"),
                title="t",
                url="ftp://x",
                price=Price(1, "TWD"),
                address=_addr(),
            )

    def test_with_observed_at_returns_new_instance(self) -> None:
        original = Listing(
            id=ListingId("591", "1"),
            title="t",
            url="https://x",
            price=Price(1, "TWD"),
            address=_addr(),
        )
        ts = datetime(2026, 4, 18, tzinfo=UTC)
        updated = original.with_observed_at(ts)
        assert original.observed_at is None
        assert updated.observed_at == ts

    def test_optional_first_class_fields_default_to_none(self) -> None:
        listing = Listing(
            id=ListingId("591", "1"),
            title="t",
            url="https://x",
            price=Price(1, "TWD"),
            address=_addr(),
        )
        assert listing.area_ping is None
        assert listing.main_area_ping is None
        assert listing.unit_price_per_ping is None
        assert listing.house_age_years is None
        assert listing.room_layout is None
        assert listing.floor is None
        assert listing.community_name is None
        assert listing.posted_at is None
        assert listing.view_count is None

    def test_first_class_fields_set_on_construction(self) -> None:
        posted = datetime(2025, 11, 18, tzinfo=UTC)
        listing = Listing(
            id=ListingId("591", "20037271"),
            title="樟新街超大空間",
            url="https://sale.591.com.tw/home/house/detail/2/20037271.html",
            price=Price(36_680_000, "TWD"),
            address=_addr(),
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
        assert listing.area_ping == 81.39
        assert listing.main_area_ping == 26.71
        assert listing.unit_price_per_ping == 45.07
        assert listing.house_age_years == 34
        assert listing.room_layout == "4房3廳3衛"
        assert listing.floor == "B1~1F/2F"
        assert listing.community_name == "正翔翠庭"
        assert listing.posted_at == posted
        assert listing.view_count == 616

    def test_negative_view_count_rejected(self) -> None:
        with pytest.raises(ValueError, match="view_count"):
            Listing(
                id=ListingId("591", "1"),
                title="t",
                url="https://x",
                price=Price(1, "TWD"),
                address=_addr(),
                view_count=-1,
            )

    def test_negative_area_rejected(self) -> None:
        with pytest.raises(ValueError, match="area_ping"):
            Listing(
                id=ListingId("591", "1"),
                title="t",
                url="https://x",
                price=Price(1, "TWD"),
                address=_addr(),
                area_ping=-1.0,
            )
