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
