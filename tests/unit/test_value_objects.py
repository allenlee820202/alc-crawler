"""Tests for domain value objects: Price, Address, ListingId."""
import pytest

from alc_crawler.domain.value_objects import Address, ListingId, Price


class TestPrice:
    def test_create_with_amount_and_currency(self) -> None:
        price = Price(amount=15_800_000, currency="TWD")
        assert price.amount == 15_800_000
        assert price.currency == "TWD"

    def test_negative_amount_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Price(amount=-1, currency="TWD")

    def test_unknown_currency_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="currency"):
            Price(amount=100, currency="XYZ")

    def test_is_value_object_equality(self) -> None:
        assert Price(100, "TWD") == Price(100, "TWD")
        assert Price(100, "TWD") != Price(101, "TWD")

    def test_is_immutable(self) -> None:
        from dataclasses import FrozenInstanceError

        price = Price(100, "TWD")
        with pytest.raises(FrozenInstanceError):
            price.amount = 200  # type: ignore[misc]


class TestAddress:
    def test_create_with_city_and_district(self) -> None:
        addr = Address(city="台北市", district="大安區", raw="台北市大安區仁愛路四段")
        assert addr.city == "台北市"
        assert addr.district == "大安區"

    def test_city_is_required(self) -> None:
        with pytest.raises(ValueError, match="city"):
            Address(city="", district="大安區", raw="x")


class TestListingId:
    def test_compose_site_and_external_id(self) -> None:
        lid = ListingId(site="591", external_id="12345")
        assert str(lid) == "591:12345"

    def test_external_id_required(self) -> None:
        with pytest.raises(ValueError):
            ListingId(site="591", external_id="")
