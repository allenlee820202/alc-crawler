"""Yungching raw item: typed mirror of the /api/v2/list JSON record.

Stage 1 of the Yungching parsing pipeline. The API returns AES-encrypted
JSON containing a list of listing objects. `parse_raw_items` decrypts,
validates the response shape, drops items missing identity or non-positive
price, and coerces values into typed `YungchingRawItem` records.

This module is deliberately ignorant of the canonical domain model.
Mapping to `CanonicalListing` lives in `mapper.py`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from alc_crawler.adapters.sites.site_yungching.crypto import decrypt_response_data


@dataclass(frozen=True, slots=True)
class PinInfo:
    reg_area: float | None = None
    main_area: float | None = None
    platform_area: float | None = None
    porch_area: float | None = None


@dataclass(frozen=True, slots=True)
class FloorInfo:
    from_floor: int | None = None
    to_floor: int | None = None
    up_floor: int | None = None


@dataclass(frozen=True, slots=True)
class PatternInfo:
    room: int | None = None
    living_room: int | None = None
    bath_room: int | None = None


@dataclass(frozen=True, slots=True)
class YungchingRawItem:
    # Required identity & price.
    case_id: str
    case_name: str
    address: str
    price_wan: float

    # Area info.
    pin_info: PinInfo = field(default_factory=PinInfo)

    # Floor info.
    floor_info: FloorInfo = field(default_factory=FloorInfo)

    # Room layout.
    pattern_info: PatternInfo = field(default_factory=PatternInfo)

    # Optional fields.
    build_age: float | None = None
    community_name: str | None = None
    case_type_name: str | None = None
    purpose_name: str | None = None
    parking: str | None = None
    brand: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    mrt_infos: tuple[str, ...] = field(default_factory=tuple)
    is_discount: bool = False
    down_ratio: float | None = None
    last_price: float | None = None


def parse_raw_items(body: str) -> list[YungchingRawItem]:
    """Parse a Yungching API response body into typed raw items.

    The body is the full JSON response from /api/v2/list. The 'data' field
    is AES-encrypted and must be decrypted before parsing listing items.

    Drops items missing identity (caseSId) or non-positive price.
    Raises ValueError on invalid JSON or non-success API status.
    """
    try:
        envelope = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    status = envelope.get("status")
    if status != "Success":
        raise ValueError(f"Yungching API returned non-success status: {status!r}")

    encrypted_data = envelope.get("data")
    if not encrypted_data:
        raise ValueError("Yungching API response missing 'data' field")

    data = decrypt_response_data(encrypted_data)

    items_raw = data.get("list") or data.get("li") or []

    items: list[YungchingRawItem] = []
    for item in items_raw:
        parsed = _parse_one(item)
        if parsed is not None:
            items.append(parsed)
    return items


def get_pagination_info(body: str) -> tuple[int, int]:
    """Extract (total_pages, total_items) from a Yungching API response."""
    try:
        envelope = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    encrypted_data = envelope.get("data")
    if not encrypted_data:
        return (0, 0)

    data = decrypt_response_data(encrypted_data)
    pagination = data.get("pa") or {}
    return (
        int(pagination.get("totalPageCount", 0)),
        int(pagination.get("totalItemCount", 0)),
    )


def _parse_one(item: dict[str, Any]) -> YungchingRawItem | None:
    case_id = item.get("caseSId")
    case_name = (item.get("caseName") or "").strip()
    address = (item.get("address") or "").strip()
    price = _as_float(item.get("price"))

    if not case_id or not case_name or price is None or price <= 0:
        return None

    # Pin info (area)
    pin_raw = item.get("pinInfo") or {}
    pin_info = PinInfo(
        reg_area=_as_float(pin_raw.get("regArea")),
        main_area=_as_float(pin_raw.get("mainArea")),
        platform_area=_as_float(pin_raw.get("platformArea")),
        porch_area=_as_float(pin_raw.get("porchArea")),
    )

    # Floor info
    floor_raw = item.get("floorInfo") or {}
    floor_info = FloorInfo(
        from_floor=_as_int(floor_raw.get("fromFloor")),
        to_floor=_as_int(floor_raw.get("toFloor")),
        up_floor=_as_int(floor_raw.get("upFloor")),
    )

    # Pattern info (rooms)
    pattern_raw = item.get("patternInfo") or {}
    pattern_info = PatternInfo(
        room=_as_int(pattern_raw.get("room")),
        living_room=_as_int(pattern_raw.get("livingRoom")),
        bath_room=_as_int(pattern_raw.get("bathRoom")),
    )

    # Tags
    tags_raw = item.get("tag") or []
    tags = tuple(str(t) for t in tags_raw if t)

    # MRT — can be list of strings or list of dicts
    mrt_raw = item.get("mrtInfos") or []
    mrt_infos: tuple[str, ...] = ()
    if mrt_raw:
        if isinstance(mrt_raw[0], str):
            mrt_infos = tuple(str(m) for m in mrt_raw if m)
        else:
            mrt_infos = tuple(
                str(m.get("name", ""))
                for m in mrt_raw
                if isinstance(m, dict) and m.get("name")
            )

    # Community
    community_raw = item.get("communityInfo") or {}
    community_name = _as_str(community_raw.get("communityName"))

    return YungchingRawItem(
        case_id=str(case_id),
        case_name=case_name,
        address=address,
        price_wan=price,
        pin_info=pin_info,
        floor_info=floor_info,
        pattern_info=pattern_info,
        build_age=_as_float(item.get("buildAge")),
        community_name=community_name,
        case_type_name=_as_str(item.get("caseTypeName")),
        purpose_name=_as_str(item.get("purposeName")),
        parking=_as_str(item.get("parking")),
        brand=_as_str(item.get("brand")),
        tags=tags,
        mrt_infos=mrt_infos,
        is_discount=bool(item.get("isDiscount")),
        down_ratio=_as_float(item.get("downRatio")),
        last_price=_as_float(item.get("lastPrice")),
    )


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        result = int(float(value))
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _as_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None
