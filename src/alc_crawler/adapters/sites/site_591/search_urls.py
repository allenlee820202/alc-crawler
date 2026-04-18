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

# Section ids for 新北市 (region=new-taipei). Discovered by probing 591's
# BFF. 27 of 新北市's 29 administrative districts have confirmed ids;
# 三芝/石門 may exist but currently return zero listings, so they are
# omitted to avoid asserting unverified ids.
NEW_TAIPEI_SECTION_IDS: dict[int, str] = {
    20: "萬里區",
    21: "金山區",
    26: "板橋區",
    27: "汐止區",
    28: "深坑區",
    29: "石碇區",
    30: "瑞芳區",
    31: "平溪區",
    32: "雙溪區",
    33: "貢寮區",
    34: "新店區",
    35: "坪林區",
    36: "烏來區",
    37: "永和區",
    38: "中和區",
    39: "土城區",
    40: "三峽區",
    41: "樹林區",
    42: "鶯歌區",
    43: "三重區",
    44: "新莊區",
    45: "泰山區",
    46: "林口區",
    47: "蘆洲區",
    48: "五股區",
    49: "八里區",
    50: "淡水區",
}

# Section ids for 桃園市 (region=taoyuan). All 13 administrative districts
# verified against the BFF.
TAOYUAN_SECTION_IDS: dict[int, str] = {
    67: "中壢區",
    68: "平鎮區",
    69: "龍潭區",
    70: "楊梅區",
    71: "新屋區",
    72: "觀音區",
    73: "桃園區",
    74: "龜山區",
    75: "八德區",
    76: "大溪區",
    77: "復興區",
    78: "大園區",
    79: "蘆竹區",
}

# Section ids for 台中市 (region=taichung). All 29 administrative districts
# verified against the BFF.
TAICHUNG_SECTION_IDS: dict[int, str] = {
    98: "中區",
    99: "東區",
    100: "南區",
    101: "西區",
    102: "北區",
    103: "北屯區",
    104: "西屯區",
    105: "南屯區",
    106: "太平區",
    107: "大里區",
    108: "霧峰區",
    109: "烏日區",
    110: "豐原區",
    111: "后里區",
    112: "石岡區",
    113: "東勢區",
    114: "和平區",
    115: "新社區",
    116: "潭子區",
    117: "大雅區",
    118: "神岡區",
    119: "大肚區",
    120: "沙鹿區",
    121: "龍井區",
    122: "梧棲區",
    123: "清水區",
    124: "大甲區",
    125: "外埔區",
    126: "大安區",
}

# Section ids for 高雄市 (region=kaohsiung). 35 of 高雄市's 38 administrative
# districts have confirmed ids; mountain-indigenous districts (那瑪夏/桃源/茂林)
# are likely 256, 257, 279-281 but currently return zero listings, so they
# are omitted to avoid asserting unverified ids.
KAOHSIUNG_SECTION_IDS: dict[int, str] = {
    243: "新興區",
    244: "前金區",
    245: "苓雅區",
    246: "鹽埕區",
    247: "鼓山區",
    248: "旗津區",
    249: "前鎮區",
    250: "三民區",
    251: "楠梓區",
    252: "小港區",
    253: "左營區",
    254: "仁武區",
    255: "大社區",
    258: "岡山區",
    259: "路竹區",
    260: "阿蓮區",
    261: "田寮區",
    262: "燕巢區",
    263: "橋頭區",
    264: "梓官區",
    265: "彌陀區",
    266: "永安區",
    267: "湖內區",
    268: "鳳山區",
    269: "大寮區",
    270: "林園區",
    271: "鳥松區",
    272: "大樹區",
    273: "旗山區",
    274: "美濃區",
    275: "六龜區",
    276: "內門區",
    277: "杉林區",
    278: "甲仙區",
    282: "茄萣區",
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
