"""Hbhousing -> CanonicalListing anti-corruption mapper.

Stage 2 of the hbhousing parsing pipeline. The mapper is the ONLY place
that knows about both hbhousing's raw shape (`HbhousingRawItem`) and the
canonical domain shape (`CanonicalListing`).
"""

from __future__ import annotations

from alc_crawler.adapters.sites.site_hbhousing.raw_item import HbhousingRawItem
from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import Address, ListingId, Price

_SITE = "hbhousing"
_DETAIL_URL = "https://www.hbhousing.com.tw/BuyHouse/detail/{sn}"


class HbhousingMapper:
    def to_canonical(self, raw: HbhousingRawItem) -> CanonicalListing:
        city, district = _parse_city_district(raw.doorplate)
        unit_price = _compute_unit_price(raw.price, raw.area)

        return CanonicalListing(
            id=ListingId(_SITE, raw.sn),
            title=raw.obj_name,
            url=_DETAIL_URL.format(sn=raw.sn),
            price=Price(amount=raw.price * 10_000, currency="TWD"),
            address=Address(
                city=city,
                district=district,
                raw=raw.doorplate or district,
            ),
            area_ping=raw.area,
            main_area_ping=raw.main_area,
            unit_price_per_ping=unit_price,
            house_age_years=_safe_int(raw.age),
            room_layout=_build_room_layout(raw),
            floor=_build_floor(raw),
            community_name=None,
            attributes=_soft_attributes(raw),
        )


def _parse_city_district(doorplate: str | None) -> tuple[str, str]:
    """Extract city and district from doorplate address.

    Hbhousing doorplate format: "district + street" without city prefix.
    E.g. "內湖區康寧路三段" or "大安區忠孝東路四段".
    The city is not included in the doorplate, so we infer from the district suffix.
    """
    if not doorplate or len(doorplate) < 3:
        return ("未知", "")

    # Find district boundary (ending with 區/市/鄉/鎮).
    for i, ch in enumerate(doorplate):
        if ch in "區市鄉鎮" and i > 0:
            district = doorplate[: i + 1]
            # Hbhousing doorplate doesn't include city; use placeholder.
            return ("未知", district)

    # Fallback: take first 3 chars as district.
    return ("未知", doorplate[:3])


def _compute_unit_price(price_wan: int, area_ping: float | None) -> float | None:
    """Compute unit price in 萬/坪."""
    if area_ping is None or area_ping <= 0:
        return None
    return round(price_wan / area_ping, 1)


def _safe_int(value: float | None) -> int | None:
    if value is None:
        return None
    return int(value)


def _build_room_layout(raw: HbhousingRawItem) -> str | None:
    """Build room layout string like '3房2廳2衛'.

    Prefers structured room/hall/bath fields; falls back to `special` field.
    """
    if raw.room is not None:
        parts = [f"{raw.room}房"]
        if raw.hall is not None:
            parts.append(f"{raw.hall}廳")
        if raw.bath is not None:
            parts.append(f"{raw.bath}衛")
        return "".join(parts)

    # Fall back to special field (e.g. "3房(室)2廳2衛").
    if raw.special:
        return raw.special

    return None


def _build_floor(raw: HbhousingRawItem) -> str | None:
    """Build floor string like '3/12樓'."""
    if raw.floor is None:
        return None
    if raw.floor_total is not None:
        return f"{raw.floor}/{raw.floor_total}樓"
    return f"{raw.floor}樓"


def _soft_attributes(raw: HbhousingRawItem) -> dict[str, str]:
    """Build soft attributes dict from non-first-class fields."""
    attrs: dict[str, str] = {}
    if raw.style:
        attrs["style"] = raw.style
    if raw.type:
        attrs["type"] = raw.type
    if raw.parking:
        attrs["parking"] = raw.parking
    if raw.mrt:
        attrs["mrt"] = raw.mrt
    if raw.category:
        attrs["category"] = raw.category
    if raw.emphasis1:
        attrs["emphasis1"] = raw.emphasis1
    if raw.feature:
        attrs["feature"] = raw.feature
    if raw.price_down_ratio:
        attrs["price_down_ratio"] = raw.price_down_ratio
    if raw.original_price is not None and raw.original_price != raw.price:
        attrs["original_price_wan"] = str(raw.original_price)
    if raw.lon is not None:
        attrs["lon"] = str(raw.lon)
    if raw.lat is not None:
        attrs["lat"] = str(raw.lat)
    return attrs
