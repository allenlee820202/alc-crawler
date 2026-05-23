"""Yungching -> CanonicalListing anti-corruption mapper.

Stage 2 of the Yungching parsing pipeline. The mapper is the ONLY place
that knows about both Yungching's raw shape (`YungchingRawItem`) and the
canonical domain shape (`CanonicalListing`).
"""
from __future__ import annotations

from alc_crawler.adapters.sites.site_yungching.raw_item import YungchingRawItem
from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import Address, ListingId, Price

_SITE = "yungching"
_DETAIL_URL = "https://buy.yungching.com.tw/house/{case_id}"


class YungchingMapper:
    def to_canonical(self, raw: YungchingRawItem) -> CanonicalListing:
        city, district = _parse_city_district(raw.address)
        area_ping = raw.pin_info.reg_area
        main_area = _compute_main_area(raw)
        unit_price = _compute_unit_price(raw.price_wan, area_ping)

        return CanonicalListing(
            id=ListingId(_SITE, raw.case_id),
            title=raw.case_name,
            url=_DETAIL_URL.format(case_id=raw.case_id),
            price=Price(amount=round(raw.price_wan * 10_000), currency="TWD"),
            address=Address(
                city=city,
                district=district,
                raw=raw.address or district,
            ),
            area_ping=area_ping,
            main_area_ping=main_area,
            unit_price_per_ping=unit_price,
            house_age_years=_safe_int(raw.build_age),
            room_layout=_build_room_layout(raw),
            floor=_build_floor(raw),
            community_name=raw.community_name,
            attributes=_soft_attributes(raw),
        )


def _parse_city_district(address: str) -> tuple[str, str]:
    """Extract city (first 3 chars) and district from a Yungching address.

    Yungching addresses typically start with "台北市大安區..." or "新北市板橋區...".
    City is 3 chars, district is the next 2-3 chars ending with 區/市/鄉/鎮.
    """
    if len(address) < 3:
        return (address or "未知", "")

    city = address[:3]
    remaining = address[3:]

    # Find district boundary (ending with 區/市/鄉/鎮)
    for i, ch in enumerate(remaining):
        if ch in "區市鄉鎮" and i > 0:
            district = remaining[: i + 1]
            return (city, district)

    # Fallback: take first 3 chars as district
    district = remaining[:3] if len(remaining) >= 3 else remaining
    return (city, district)


def _compute_main_area(raw: YungchingRawItem) -> float | None:
    """Main area = mainArea + porchArea (matching 591 convention)."""
    main = raw.pin_info.main_area
    porch = raw.pin_info.porch_area
    if main is None:
        return None
    return main + (porch or 0)


def _compute_unit_price(price_wan: float, area_ping: float | None) -> float | None:
    """Compute unit price in 萬/坪."""
    if area_ping is None or area_ping <= 0:
        return None
    return round(price_wan / area_ping, 1)


def _safe_int(value: float | None) -> int | None:
    if value is None:
        return None
    return int(value)


def _build_room_layout(raw: YungchingRawItem) -> str | None:
    """Build room layout string like '3房2廳2衛'."""
    p = raw.pattern_info
    if p.room is None:
        return None
    parts = [f"{p.room}房"]
    if p.living_room is not None:
        parts.append(f"{p.living_room}廳")
    if p.bath_room is not None:
        parts.append(f"{p.bath_room}衛")
    return "".join(parts)


def _build_floor(raw: YungchingRawItem) -> str | None:
    """Build floor string like '3/12樓'."""
    f = raw.floor_info
    if f.from_floor is None:
        return None
    if f.up_floor is not None:
        return f"{f.from_floor}/{f.up_floor}樓"
    return f"{f.from_floor}樓"


def _soft_attributes(raw: YungchingRawItem) -> dict[str, str]:
    attrs: dict[str, str] = {}
    if raw.case_type_name:
        attrs["case_type"] = raw.case_type_name
    if raw.purpose_name:
        attrs["purpose"] = raw.purpose_name
    if raw.parking:
        attrs["parking"] = raw.parking
    if raw.brand:
        attrs["brand"] = raw.brand
    if raw.tags:
        attrs["tags"] = ",".join(raw.tags)
    if raw.mrt_infos:
        attrs["mrt"] = ",".join(raw.mrt_infos)
    if raw.is_discount:
        attrs["is_discount"] = "true"
    if raw.down_ratio is not None:
        attrs["down_ratio"] = str(raw.down_ratio)
    if raw.last_price is not None:
        attrs["last_price_wan"] = str(raw.last_price)
    return attrs
