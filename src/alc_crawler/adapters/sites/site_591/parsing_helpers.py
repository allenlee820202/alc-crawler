"""Pure parsing helpers for 591-style data.

Kept separate from the HTML parser so the tricky string logic can be
unit-tested in isolation (no DOM, no fixtures).
"""
from __future__ import annotations

import re

from alc_crawler.domain.value_objects import Address

_NUM_PATTERN = re.compile(r"^[\d,]+(?:\.\d+)?$")
_CITY_DISTRICT_PATTERN = re.compile(r"^(.{2,3}[市縣])(.{1,4}[區鄉鎮市])")
_SIZE_PATTERN = re.compile(r"^([\d.]+)坪$")
_FLOOR_PATTERN = re.compile(r"^(\d+(?:/\d+)?)樓$")
_LAYOUT_PATTERN = re.compile(r"^\d+房\d+廳")


def parse_chinese_price(num_text: str, unit_text: str) -> int | None:
    """Convert e.g. ('1,580', '萬') -> 15_800_000.

    Returns None for non-numeric inputs (e.g. '價格議定').
    """
    cleaned = num_text.replace(",", "").strip()
    if not cleaned or not _NUM_PATTERN.match(num_text.strip()):
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None

    multipliers = {"": 1, "萬": 10_000, "億": 100_000_000}
    multiplier = multipliers.get(unit_text.strip())
    if multiplier is None:
        return None
    return int(value * multiplier)


def parse_taiwan_address(raw: str) -> Address | None:
    match = _CITY_DISTRICT_PATTERN.match(raw.strip())
    if not match:
        return None
    return Address(city=match.group(1), district=match.group(2), raw=raw.strip())


def parse_attribute_tokens(tokens: list[str]) -> dict[str, str]:
    """Map tokens like '3房2廳', '28.5坪', '5/12樓' into a typed-ish dict."""
    out: dict[str, str] = {}
    for token in tokens:
        token = token.strip()
        if _LAYOUT_PATTERN.match(token):
            out["layout"] = token
        elif size := _SIZE_PATTERN.match(token):
            out["size_ping"] = size.group(1)
        elif floor := _FLOOR_PATTERN.match(token):
            out["floor"] = floor.group(1)
    return out
