"""Unit tests for Yungching mapper."""
from __future__ import annotations

from alc_crawler.adapters.sites.site_yungching.mapper import YungchingMapper
from alc_crawler.adapters.sites.site_yungching.raw_item import (
    FloorInfo,
    PatternInfo,
    PinInfo,
    YungchingRawItem,
)


def _make_raw(**overrides: object) -> YungchingRawItem:
    defaults: dict[str, object] = {
        "case_id": "12345",
        "case_name": "Test Listing",
        "address": "台北市大安區忠孝東路100號",
        "price_wan": 2000.0,
        "pin_info": PinInfo(reg_area=30.0, main_area=25.0, porch_area=3.0),
        "floor_info": FloorInfo(from_floor=3, to_floor=3, up_floor=10),
        "pattern_info": PatternInfo(room=3, living_room=2, bath_room=1),
        "build_age": 20.0,
        "community_name": "Test Community",
        "case_type_name": "電梯大樓",
        "purpose_name": "住宅",
    }
    defaults.update(overrides)
    return YungchingRawItem(**defaults)  # type: ignore[arg-type]


class TestYungchingMapper:
    def setup_method(self) -> None:
        self.mapper = YungchingMapper()

    def test_listing_id(self) -> None:
        result = self.mapper.to_canonical(_make_raw())
        assert result.id.site == "yungching"
        assert result.id.external_id == "12345"

    def test_title(self) -> None:
        result = self.mapper.to_canonical(_make_raw(case_name="Great Place"))
        assert result.title == "Great Place"

    def test_url(self) -> None:
        result = self.mapper.to_canonical(_make_raw(case_id="99999"))
        assert result.url == "https://buy.yungching.com.tw/house/99999"

    def test_price(self) -> None:
        result = self.mapper.to_canonical(_make_raw(price_wan=2500.0))
        assert result.price.amount == 25_000_000
        assert result.price.currency == "TWD"

    def test_address_parsing(self) -> None:
        result = self.mapper.to_canonical(_make_raw(address="台北市大安區忠孝東路100號"))
        assert result.address.city == "台北市"
        assert result.address.district == "大安區"
        assert result.address.raw == "台北市大安區忠孝東路100號"

    def test_address_parsing_new_taipei(self) -> None:
        result = self.mapper.to_canonical(_make_raw(address="新北市板橋區中山路"))
        assert result.address.city == "新北市"
        assert result.address.district == "板橋區"

    def test_area_ping(self) -> None:
        result = self.mapper.to_canonical(
            _make_raw(pin_info=PinInfo(reg_area=35.2, main_area=28.0, porch_area=3.0))
        )
        assert result.area_ping == 35.2

    def test_main_area_includes_porch(self) -> None:
        result = self.mapper.to_canonical(
            _make_raw(pin_info=PinInfo(reg_area=35.0, main_area=28.0, porch_area=3.5))
        )
        assert result.main_area_ping == 31.5  # 28.0 + 3.5

    def test_unit_price(self) -> None:
        result = self.mapper.to_canonical(
            _make_raw(price_wan=3000.0, pin_info=PinInfo(reg_area=30.0))
        )
        assert result.unit_price_per_ping == 100.0

    def test_house_age(self) -> None:
        result = self.mapper.to_canonical(_make_raw(build_age=15.7))
        assert result.house_age_years == 15

    def test_room_layout(self) -> None:
        result = self.mapper.to_canonical(
            _make_raw(pattern_info=PatternInfo(room=3, living_room=2, bath_room=2))
        )
        assert result.room_layout == "3房2廳2衛"

    def test_floor(self) -> None:
        result = self.mapper.to_canonical(
            _make_raw(floor_info=FloorInfo(from_floor=5, up_floor=12))
        )
        assert result.floor == "5/12樓"

    def test_community_name(self) -> None:
        result = self.mapper.to_canonical(_make_raw(community_name="忠孝大廈"))
        assert result.community_name == "忠孝大廈"

    def test_soft_attributes(self) -> None:
        result = self.mapper.to_canonical(
            _make_raw(
                case_type_name="電梯大樓",
                purpose_name="住宅",
                brand="永慶房屋",
                tags=("近捷運", "低總價"),
                mrt_infos=("忠孝敦化站",),
            )
        )
        assert result.attributes["case_type"] == "電梯大樓"
        assert result.attributes["purpose"] == "住宅"
        assert result.attributes["brand"] == "永慶房屋"
        assert result.attributes["tags"] == "近捷運,低總價"
        assert result.attributes["mrt"] == "忠孝敦化站"

    def test_none_area_gives_none_unit_price(self) -> None:
        result = self.mapper.to_canonical(_make_raw(pin_info=PinInfo()))
        assert result.unit_price_per_ping is None

    def test_none_rooms_gives_none_layout(self) -> None:
        result = self.mapper.to_canonical(
            _make_raw(pattern_info=PatternInfo(room=None))
        )
        assert result.room_layout is None
