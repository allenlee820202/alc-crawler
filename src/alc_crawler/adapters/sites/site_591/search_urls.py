"""591 region -> URL mapping.

The live 591 site is a Nuxt SPA. Search results come from a BFF JSON API,
but the BFF rejects requests without a same-origin Referer pointing back
at sale.591.com.tw. We therefore expose two URLs per query:

- `referer_url` : the human-facing search page (used as warm-up + Referer)
- `api_url`     : the JSON BFF endpoint we actually parse
"""
from __future__ import annotations

from dataclasses import dataclass

_REGION_IDS = {
    "taipei": 1,
    "new-taipei": 3,
    "taoyuan": 6,
    "taichung": 8,
    "kaohsiung": 17,
}

_PAGE_SIZE = 30


@dataclass(frozen=True, slots=True)
class Site591SearchUrls:
    referer_url: str
    api_url: str


def search_urls_for_region(region: str, *, page: int = 1) -> Site591SearchUrls:
    region = region.lower()
    if region not in _REGION_IDS:
        raise ValueError(
            f"Unknown 591 region '{region}'. Supported: {sorted(_REGION_IDS)}"
        )
    region_id = _REGION_IDS[region]
    first_row = (page - 1) * _PAGE_SIZE
    return Site591SearchUrls(
        referer_url=(
            f"https://sale.591.com.tw/?regionid={region_id}&shType=list&firstRow={first_row}"
        ),
        api_url=(
            f"https://bff-house.591.com.tw/v1/web/sale/list?"
            f"regionid={region_id}&firstRow={first_row}&type=2"
        ),
    )


# Back-compat thin wrapper for code that only needs one URL.
def search_url_for_region(region: str, *, page: int = 1) -> str:
    return search_urls_for_region(region, page=page).api_url
