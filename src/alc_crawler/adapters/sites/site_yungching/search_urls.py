"""Yungching region -> URL mapping.

Yungching's buy site uses /api/v2/list with query params for filtering.
Unlike 591, Yungching uses county-district names (Chinese) rather than
numeric IDs for region filtering.

URL pattern:
  GET https://buy.yungching.com.tw/api/v2/list?area=台北市-大安區&pg=1&ps=30
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

_PAGE_SIZE = 30

# Mapping from CLI region keys to county names.
REGION_NAMES: dict[str, str] = {
    "taipei": "台北市",
    "new-taipei": "新北市",
    "taoyuan": "桃園市",
    "taichung": "台中市",
    "kaohsiung": "高雄市",
}

# Districts per region. Used for CLI introspection and validation.
DISTRICTS: dict[str, list[str]] = {
    "taipei": [
        "中正區", "大同區", "中山區", "松山區", "大安區", "萬華區",
        "信義區", "士林區", "北投區", "內湖區", "南港區", "文山區",
    ],
    "new-taipei": [
        "板橋區", "三重區", "中和區", "永和區", "新莊區", "新店區",
        "土城區", "蘆洲區", "汐止區", "樹林區", "鶯歌區", "三峽區",
        "淡水區", "林口區", "五股區", "泰山區", "八里區", "深坑區",
        "石碇區", "坪林區", "烏來區", "瑞芳區", "萬里區", "金山區",
        "貢寮區", "雙溪區", "平溪區",
    ],
    "taoyuan": [
        "桃園區", "中壢區", "平鎮區", "八德區", "楊梅區", "蘆竹區",
        "龜山區", "龍潭區", "大溪區", "大園區", "觀音區", "新屋區",
        "復興區",
    ],
    "taichung": [
        "中區", "東區", "南區", "西區", "北區", "北屯區", "西屯區",
        "南屯區", "太平區", "大里區", "霧峰區", "烏日區", "豐原區",
        "后里區", "石岡區", "東勢區", "和平區", "新社區", "潭子區",
        "大雅區", "神岡區", "大肚區", "沙鹿區", "龍井區", "梧棲區",
        "清水區", "大甲區", "外埔區", "大安區",
    ],
    "kaohsiung": [
        "新興區", "前金區", "苓雅區", "鹽埕區", "鼓山區", "旗津區",
        "前鎮區", "三民區", "楠梓區", "小港區", "左營區", "仁武區",
        "大社區", "岡山區", "路竹區", "阿蓮區", "田寮區", "燕巢區",
        "橋頭區", "梓官區", "彌陀區", "永安區", "湖內區", "鳳山區",
        "大寮區", "林園區", "鳥松區", "大樹區", "旗山區", "美濃區",
        "六龜區", "內門區", "杉林區", "甲仙區", "茄萣區",
    ],
}


@dataclass(frozen=True, slots=True)
class YungchingSearchParams:
    """Parameters for a Yungching list API request."""

    api_url: str
    referer_url: str


def search_params(
    region: str,
    *,
    page: int = 1,
    districts: list[str] | None = None,
    min_price_wan: float | None = None,
    max_price_wan: float | None = None,
    min_rooms: int | None = None,
    max_rooms: int | None = None,
    max_age: float | None = None,
) -> YungchingSearchParams:
    """Build Yungching search API URL from region + optional filters.

    Unlike 591, Yungching actually respects filter params server-side.
    """
    region = region.lower()
    if region not in REGION_NAMES:
        raise ValueError(
            f"Unknown Yungching region '{region}'. Supported: {sorted(REGION_NAMES)}"
        )

    county = REGION_NAMES[region]

    # Build area params
    area_params: list[tuple[str, str]] = []
    if districts:
        for d in districts:
            area_params.append(("area", f"{county}-{d}"))
    else:
        area_params.append(("area", county))

    # Build query params
    params: list[tuple[str, str | int | float]] = list(area_params)
    params.append(("pg", page))
    params.append(("ps", _PAGE_SIZE))

    if min_price_wan is not None:
        params.append(("minPrice", min_price_wan))
    if max_price_wan is not None:
        params.append(("maxPrice", max_price_wan))
    if min_rooms is not None:
        params.append(("minRoom", min_rooms))
    if max_rooms is not None:
        params.append(("maxRoom", max_rooms))
    if max_age is not None:
        params.append(("maxAge", max_age))

    qs = urlencode(params)
    api_url = f"https://buy.yungching.com.tw/api/v2/list?{qs}"

    # Referer: human-facing search page
    referer_qs = urlencode(area_params)
    referer_url = f"https://buy.yungching.com.tw/list?{referer_qs}"

    return YungchingSearchParams(api_url=api_url, referer_url=referer_url)
