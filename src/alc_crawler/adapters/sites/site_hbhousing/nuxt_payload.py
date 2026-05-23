"""Nuxt3 devalue payload extractor for hbhousing HTML pages.

Hbhousing is a Nuxt3 SSR app. Search result data is embedded in HTML as
a `<script type="application/json" ... id="__NUXT_DATA__">` element
containing a devalue-format JSON array.

Devalue format:
  - The payload is a flat JSON array where entries reference each other by index.
  - Object entries are dicts mapping string keys to integer indices.
  - Array entries are lists of integer indices.
  - Scalar entries (str, int, float, bool, null) are leaf values.

To resolve a listing:
  1. Find the dict containing `buyHouseListDatas` key.
  2. Resolve its value (an array of listing indices).
  3. Each listing index points to a dict mapping field names to value indices.
  4. Resolve each field by looking up `data[value_idx]`.
"""

from __future__ import annotations

import json
import re
from typing import Any

_NUXT_SCRIPT_RE = re.compile(
    r'<script\s+[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>',
    re.DOTALL,
)


def extract_nuxt_payload(html: str) -> list[Any]:
    """Extract the raw devalue array from HTML.

    Raises ValueError if the script tag is not found or JSON is invalid.
    """
    match = _NUXT_SCRIPT_RE.search(html)
    if not match:
        raise ValueError("No __NUXT_DATA__ script tag found in HTML")

    raw_json = match.group(1).strip()
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in __NUXT_DATA__: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("__NUXT_DATA__ payload is not a JSON array")

    return data


def resolve_listings(data: list[Any]) -> tuple[list[dict[str, Any]], int]:
    """Resolve listing dicts and total count from devalue payload.

    Returns:
        Tuple of (resolved_listings, total_count).
        Each listing is a flat dict with field names as keys and resolved values.

    Raises:
        ValueError: If the expected structure is not found.
    """
    # Find the dict containing 'buyHouseListDatas'.
    container_idx = _find_container_index(data)
    if container_idx is None:
        raise ValueError("No dict with 'buyHouseListDatas' found in payload")

    container = data[container_idx]

    # Resolve total count.
    cnts_idx = container.get("cnts")
    total_count = 0
    if cnts_idx is not None and isinstance(cnts_idx, int) and cnts_idx < len(data):
        raw_cnts = data[cnts_idx]
        if isinstance(raw_cnts, (int, float)):
            total_count = int(raw_cnts)

    # Resolve listing array.
    list_idx = container["buyHouseListDatas"]
    if not isinstance(list_idx, int) or list_idx >= len(data):
        return ([], total_count)

    listing_indices = data[list_idx]
    if not isinstance(listing_indices, list):
        return ([], total_count)

    # Resolve each listing.
    listings: list[dict[str, Any]] = []
    for idx in listing_indices:
        if not isinstance(idx, int) or idx >= len(data):
            continue
        schema = data[idx]
        if not isinstance(schema, dict):
            continue
        resolved = _resolve_dict(data, schema)
        if resolved:
            listings.append(resolved)

    return (listings, total_count)


def _find_container_index(data: list[Any]) -> int | None:
    """Find the index of the dict containing 'buyHouseListDatas'."""
    for i, entry in enumerate(data):
        if isinstance(entry, dict) and "buyHouseListDatas" in entry:
            return i
    return None


def _resolve_dict(data: list[Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve a schema dict by looking up each value index in the data array."""
    resolved: dict[str, Any] = {}
    for key, value_idx in schema.items():
        if isinstance(value_idx, int) and value_idx < len(data):
            resolved[key] = data[value_idx]
        else:
            # Non-integer value or out of bounds: use as-is (shouldn't happen normally).
            resolved[key] = value_idx
    return resolved
