"""Unit tests for hbhousing mapper."""

from __future__ import annotations

from alc_crawler.adapters.sites.site_hbhousing.mapper import HbhousingMapper
from alc_crawler.adapters.sites.site_hbhousing.raw_item import HbhousingRawItem


def _make_raw(**overrides: object) -> HbhousingRawItem:
    defaults: dict[str, object] = {
        "sn": "ZS187442",
        "obj_name": "近捷運三房美寓",
        "price": 2580,
        "room": 3,
        "hall": 2,
        "bath": 2,
        "area": 35.5,
        "main_area": 25.0,
        "style": "大樓",
        "doorplate": "內湖區康寧路三段",
        "floor": "5",
        "floor_total": "12",
        "age": 15.3,
        "parking": "私有",
    }
    defaults.update(overrides)
    return HbhousingRawItem(**defaults)  # type: ignore[arg-type]


class TestHbhousingMapper:
    def setup_method(self) -> None:
        self.mapper = HbhousingMapper()

    def test_listing_id(self) -> None:
        result = self.mapper.to_canonical(_make_raw())
        assert result.id.site == "hbhousing"
        assert result.id.external_id == "ZS187442"

    def test_title(self) -> None:
        result = self.mapper.to_canonical(_make_raw(obj_name="Great Place"))
        assert result.title == "Great Place"

    def test_url(self) -> None:
        result = self.mapper.to_canonical(_make_raw(sn="WS76474"))
        assert result.url == "https://www.hbhousing.com.tw/BuyHouse/detail/WS76474"

    def test_price_conversion(self) -> None:
        # price in 萬 -> amount in TWD (price * 10000)
        result = self.mapper.to_canonical(_make_raw(price=2580))
        assert result.price.amount == 25_800_000
        assert result.price.currency == "TWD"

    def test_address_parsing_from_doorplate(self) -> None:
        result = self.mapper.to_canonical(_make_raw(doorplate="內湖區康寧路三段"))
        assert result.address.district == "內湖區"
        assert result.address.raw == "內湖區康寧路三段"

    def test_address_no_city_in_doorplate(self) -> None:
        # hbhousing doorplate doesn't include city; mapper returns "未知"
        result = self.mapper.to_canonical(_make_raw(doorplate="大安區忠孝東路"))
        assert result.address.city == "未知"
        assert result.address.district == "大安區"

    def test_area_ping(self) -> None:
        result = self.mapper.to_canonical(_make_raw(area=35.5))
        assert result.area_ping == 35.5

    def test_main_area_ping(self) -> None:
        result = self.mapper.to_canonical(_make_raw(main_area=25.0))
        assert result.main_area_ping == 25.0

    def test_unit_price(self) -> None:
        result = self.mapper.to_canonical(_make_raw(price=3000, area=30.0))
        assert result.unit_price_per_ping == 100.0

    def test_house_age(self) -> None:
        result = self.mapper.to_canonical(_make_raw(age=15.7))
        assert result.house_age_years == 15

    def test_room_layout_from_structured_fields(self) -> None:
        result = self.mapper.to_canonical(_make_raw(room=3, hall=2, bath=2))
        assert result.room_layout == "3房2廳2衛"

    def test_room_layout_fallback_to_special(self) -> None:
        result = self.mapper.to_canonical(
            _make_raw(room=None, hall=None, bath=None, special="3房(室)2廳2衛")
        )
        assert result.room_layout == "3房(室)2廳2衛"

    def test_room_layout_none_when_no_data(self) -> None:
        result = self.mapper.to_canonical(_make_raw(room=None, hall=None, bath=None, special=None))
        assert result.room_layout is None

    def test_floor(self) -> None:
        result = self.mapper.to_canonical(_make_raw(floor="5", floor_total="12"))
        assert result.floor == "5/12樓"

    def test_floor_without_total(self) -> None:
        result = self.mapper.to_canonical(_make_raw(floor="3", floor_total=None))
        assert result.floor == "3樓"

    def test_floor_none(self) -> None:
        result = self.mapper.to_canonical(_make_raw(floor=None))
        assert result.floor is None

    def test_soft_attributes_style(self) -> None:
        result = self.mapper.to_canonical(_make_raw(style="大樓"))
        assert result.attributes["style"] == "大樓"

    def test_soft_attributes_parking(self) -> None:
        result = self.mapper.to_canonical(_make_raw(parking="私有"))
        assert result.attributes["parking"] == "私有"

    def test_soft_attributes_mrt(self) -> None:
        result = self.mapper.to_canonical(_make_raw(mrt="文湖線內湖站"))
        assert result.attributes["mrt"] == "文湖線內湖站"

    def test_none_area_gives_none_unit_price(self) -> None:
        result = self.mapper.to_canonical(_make_raw(area=None))
        assert result.unit_price_per_ping is None

    def test_zero_area_gives_none_unit_price(self) -> None:
        result = self.mapper.to_canonical(_make_raw(area=0.0))
        assert result.unit_price_per_ping is None

    def test_none_doorplate_gives_unknown_city(self) -> None:
        result = self.mapper.to_canonical(_make_raw(doorplate=None))
        assert result.address.city == "未知"
        assert result.address.district == ""

    def test_original_price_in_attributes(self) -> None:
        result = self.mapper.to_canonical(_make_raw(price=2500, original_price=2800))
        assert result.attributes["original_price_wan"] == "2800"

    def test_original_price_not_in_attributes_when_same(self) -> None:
        result = self.mapper.to_canonical(_make_raw(price=2500, original_price=2500))
        assert "original_price_wan" not in result.attributes
