"""Hbhousing raw item: typed mirror of the Nuxt devalue listing record.

Stage 1 of the hbhousing parsing pipeline. The HTML page contains a Nuxt3
devalue payload with listing data. `parse_raw_items` extracts the payload,
resolves references, validates the structure, and produces typed
`HbhousingRawItem` records.

This module is deliberately ignorant of the canonical domain model.
Mapping to `CanonicalListing` lives in `mapper.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from alc_crawler.adapters.sites.site_hbhousing.nuxt_payload import (
    extract_nuxt_payload,
    resolve_listings,
)


@dataclass(frozen=True, slots=True)
class HbhousingRawItem:
    """Typed representation of a single hbhousing listing."""

    sn: str
    obj_name: str
    price: int
    original_price: int | None = None
    room: int | None = None
    hall: int | None = None
    bath: int | None = None
    special: str | None = None
    area: float | None = None
    main_area: float | None = None
    land_area: float | None = None
    affiliated_area: float | None = None
    type: str | None = None
    style: str | None = None
    parking: str | None = None
    floor: str | None = None
    floor_total: str | None = None
    age: float | None = None
    doorplate: str | None = None
    mrt: str | None = None
    lon: float | None = None
    lat: float | None = None
    category: str | None = None
    emphasis1: str | None = None
    feature: str | None = None
    price_down_ratio: str | None = None


def parse_raw_items(html: str) -> tuple[list[HbhousingRawItem], int]:
    """Parse HTML page into typed raw items and total count.

    Returns:
        Tuple of (items, total_count).
        Items missing required identity (sn) or non-positive price are dropped.

    Raises:
        ValueError: If the HTML does not contain valid __NUXT_DATA__.
    """
    data = extract_nuxt_payload(html)
    resolved, total_count = resolve_listings(data)

    items: list[HbhousingRawItem] = []
    for listing_dict in resolved:
        parsed = _parse_one(listing_dict)
        if parsed is not None:
            items.append(parsed)

    return (items, total_count)


def _parse_one(raw: dict[str, Any]) -> HbhousingRawItem | None:
    """Convert a resolved listing dict to a typed HbhousingRawItem.

    Returns None if required fields are missing or invalid.
    """
    sn = _as_str(raw.get("sn"))
    obj_name = _as_str(raw.get("objName"))
    price = _as_int(raw.get("price"))

    if not sn or not obj_name or price is None or price <= 0:
        return None

    return HbhousingRawItem(
        sn=sn,
        obj_name=obj_name,
        price=price,
        original_price=_as_int(raw.get("originalPrice")),
        room=_as_int(raw.get("room")),
        hall=_as_int(raw.get("hall")),
        bath=_as_int(raw.get("bath")),
        special=_as_str(raw.get("special")),
        area=_as_float(raw.get("area")),
        main_area=_as_float(raw.get("mainArea")),
        land_area=_as_float(raw.get("landArea")),
        affiliated_area=_as_float(raw.get("affiliatedArea")),
        type=_as_str(raw.get("type")),
        style=_as_str(raw.get("style")),
        parking=_as_str(raw.get("parking")),
        floor=_as_str(raw.get("floor")),
        floor_total=_as_str(raw.get("floorTotal")),
        age=_as_float(raw.get("age")),
        doorplate=_as_str(raw.get("doorplate")),
        mrt=_as_str(raw.get("mrt")),
        lon=_as_float(raw.get("lon")),
        lat=_as_float(raw.get("lat")),
        category=_as_str(raw.get("category")),
        emphasis1=_as_str(raw.get("emphasis1")),
        feature=_as_str(raw.get("feature")),
        price_down_ratio=_as_str(raw.get("priceDownRatio")),
    )


def _as_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        result = int(float(value))
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None
