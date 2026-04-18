"""591 region -> URL mapping.

The live 591 site is a Nuxt SPA. Search results come from a BFF JSON API,
but the BFF rejects requests without a same-origin Referer pointing back
at sale.591.com.tw. We therefore expose two URLs per query:

- `referer_url` : the human-facing search page (used as warm-up + Referer)
- `api_url`     : the JSON BFF endpoint we actually parse

Section / shape filters are pushed server-side to narrow what we fetch.
Note: 591's `price` and `houseage` query params are unreliable in practice
(the BFF returns out-of-range listings anyway), so those are NOT pushed
here — the `query` CLI applies them locally over persisted data instead.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlencode

_REGION_IDS = {
    "taipei": 1,
    "new-taipei": 3,
    "taoyuan": 6,
    "taichung": 8,
    "kaohsiung": 17,
}

# Public read-only views of 591's id space for CLI/agent introspection.
REGION_IDS: dict[str, int] = dict(_REGION_IDS)

# Section ids for 台北市 (region=taipei). 3 is intentionally omitted: 591's
# BFF returns malformed JSON for that section. Other regions have their own
# section id spaces; documenting only the verified-working set here.
TAIPEI_SECTION_IDS: dict[int, str] = {
    1: "中正區",
    2: "大同區",
    4: "松山區",
    5: "大安區",
    6: "萬華區",
    7: "信義區",
    8: "士林區",
    9: "北投區",
    10: "內湖區",
    11: "南港區",
    12: "文山區",
}

# Shape (建物型態) ids accepted by 591's BFF.
SHAPE_IDS: dict[int, str] = {
    1: "公寓",
    2: "電梯大樓",
    3: "透天厝",
    4: "別墅",
    8: "店面",
}

_PAGE_SIZE = 30


@dataclass(frozen=True, slots=True)
class Site591SearchUrls:
    referer_url: str
    api_url: str


def search_urls_for_region(
    region: str,
    *,
    page: int = 1,
    section_id: int | None = None,
    shape_ids: Iterable[int] | None = None,
) -> Site591SearchUrls:
    region = region.lower()
    if region not in _REGION_IDS:
        raise ValueError(
            f"Unknown 591 region '{region}'. Supported: {sorted(_REGION_IDS)}"
        )
    if section_id is not None and section_id <= 0:
        raise ValueError(f"section_id must be positive, got {section_id}")

    shape_csv: str | None = None
    if shape_ids is not None:
        shapes = list(shape_ids)
        if any(s <= 0 for s in shapes):
            raise ValueError(f"shape_ids must all be positive, got {shapes}")
        if shapes:
            shape_csv = ",".join(str(s) for s in shapes)

    region_id = _REGION_IDS[region]
    first_row = (page - 1) * _PAGE_SIZE

    common: dict[str, str | int] = {"regionid": region_id}
    if section_id is not None:
        common["section"] = section_id
    if shape_csv is not None:
        common["shape"] = shape_csv

    referer_qs = urlencode({**common, "shType": "list", "firstRow": first_row})
    api_qs = urlencode({**common, "firstRow": first_row, "type": 2})

    return Site591SearchUrls(
        referer_url=f"https://sale.591.com.tw/?{referer_qs}",
        api_url=f"https://bff-house.591.com.tw/v1/web/sale/list?{api_qs}",
    )


# Back-compat thin wrapper for code that only needs one URL.
def search_url_for_region(region: str, *, page: int = 1) -> str:
    return search_urls_for_region(region, page=page).api_url
