"""591 raw item: typed mirror of the BFF JSON record.

Stage 1 of the 591 parsing pipeline. The BFF returns a list of dicts
with mixed types (numbers occasionally arriving as strings, optional
fields absent or empty-string). `parse_raw_items` validates the JSON
shape, drops items missing identity (house_id) or non-positive price,
and coerces values into a typed `Site591RawItem` record.

This module is deliberately ignorant of the canonical domain model.
Mapping to `CanonicalListing` lives in `mapper.py` so that swapping
either side (e.g. the BFF starts returning a new field) is a one-file
change.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Site591RawItem:
    # Required identity & price (anchors for downstream processing).
    house_id: str
    title: str
    region_name: str
    section_name: str
    address: str
    price_wan: float

    # Optional first-class numerics & strings.
    area: float | None = None
    main_area: float | None = None
    unit_price: float | None = None
    house_age: int | None = None
    room: str | None = None
    floor: str | None = None
    community_name: str | None = None
    posttime: int | None = None
    browsenum: int | None = None

    # Soft fields kept verbatim from the BFF (no semantic interpretation here).
    shape_name: str | None = None
    kind_name: str | None = None
    housetype: str | None = None
    unit_price_label: str | None = None
    nick_name: str | None = None
    photo_num: int | None = None
    is_video: int | None = None
    condition_ids: tuple[int, ...] = field(default_factory=tuple)


def parse_raw_items(body: str) -> list[Site591RawItem]:
    """Parse a 591 BFF response body into typed raw items.

    Drops items missing identity (house_id) or non-positive price.
    Raises ValueError on invalid JSON or non-success API status.
    """
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    if data.get("status") != 1:
        raise ValueError(f"591 API returned non-success status: {data.get('status')!r}")

    items_raw = (data.get("data") or {}).get("house_list") or []
    items: list[Site591RawItem] = []
    for item in items_raw:
        parsed = _parse_one(item)
        if parsed is not None:
            items.append(parsed)
    return items


def _parse_one(item: dict[str, Any]) -> Site591RawItem | None:
    house_id = item.get("houseid")
    title = (item.get("title") or "").strip()
    region = (item.get("region_name") or "").strip()
    section = (item.get("section_name") or "").strip()
    raw_addr = (item.get("address") or "").strip()
    price = _as_float(item.get("price"))

    if not house_id or not title or not region or not section or price is None or price <= 0:
        return None

    cond_raw = item.get("conditionids")
    cond: tuple[int, ...] = ()
    if isinstance(cond_raw, list):
        coerced: list[int] = []
        for c in cond_raw:
            try:
                coerced.append(int(c))
            except (TypeError, ValueError):
                continue
        cond = tuple(coerced)

    return Site591RawItem(
        house_id=str(house_id),
        title=title,
        region_name=region,
        section_name=section,
        address=raw_addr,
        price_wan=price,
        area=_as_float(item.get("area")),
        main_area=_as_float(item.get("mainarea")),
        unit_price=_as_float(item.get("unitprice")),
        house_age=_as_int(item.get("houseage")),
        room=_as_str(item.get("room")),
        floor=_as_str(item.get("floor")),
        community_name=_as_str(item.get("community_name")),
        posttime=_as_int(item.get("posttime")),
        browsenum=_as_int(item.get("browsenum")),
        shape_name=_as_str(item.get("shape_name")),
        kind_name=_as_str(item.get("kind_name")),
        housetype=_as_str(item.get("housetype")),
        unit_price_label=_as_str(item.get("unit_price")),
        nick_name=_as_str(item.get("nick_name")),
        photo_num=_as_int(item.get("photoNum")),
        is_video=_as_int(item.get("is_video")),
        condition_ids=cond,
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
        result = int(float(value))  # accept "12" and "12.0"
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _as_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None
