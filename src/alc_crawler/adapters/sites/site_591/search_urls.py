"""591 region -> search URL mapping.

This is intentionally simple. Adding regions = adding entries here.
"""
from __future__ import annotations

_REGION_IDS = {
    "taipei": 1,
    "new-taipei": 3,
    "taoyuan": 6,
    "taichung": 8,
    "kaohsiung": 17,
}


def search_url_for_region(region: str, *, page: int = 1) -> str:
    region = region.lower()
    if region not in _REGION_IDS:
        raise ValueError(
            f"Unknown 591 region '{region}'. Supported: {sorted(_REGION_IDS)}"
        )
    return f"https://sale.591.com.tw/?regionid={_REGION_IDS[region]}&firstRow={(page - 1) * 30}"
