"""Hbhousing (住商不動產) region -> URL mapping.

Hbhousing is a Nuxt3 SSR app. The search page URL encodes city, zip codes,
and filter segments as path components:

  /buyhouse/{cityKey}/{zipCodes}/{filters}/{page}-page/

Examples:
  /buyhouse/台北市/114/                       (Neihu, page 1)
  /buyhouse/台北市/114/0-3500-price/2-page/   (Neihu, price ≤3500萬, page 2)
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

_BASE_URL = "https://www.hbhousing.com.tw"
_PAGE_SIZE = 10

# Mapping from CLI region keys to city names.
REGION_NAMES: dict[str, str] = {
    "taipei": "台北市",
    "new-taipei": "新北市",
    "taoyuan": "桃園市",
    "taichung": "台中市",
    "kaohsiung": "高雄市",
}

# Districts -> zip codes per region.
DISTRICT_ZIP_CODES: dict[str, dict[str, str]] = {
    "taipei": {
        "中正區": "100",
        "大同區": "103",
        "中山區": "104",
        "松山區": "105",
        "大安區": "106",
        "萬華區": "108",
        "信義區": "110",
        "士林區": "111",
        "北投區": "112",
        "內湖區": "114",
        "南港區": "115",
        "文山區": "116",
    },
    "new-taipei": {
        "板橋區": "220",
        "汐止區": "221",
        "永和區": "234",
        "中和區": "235",
        "三重區": "241",
        "新莊區": "242",
        "淡水區": "251",
        "新店區": "231",
        "土城區": "236",
        "蘆洲區": "247",
        "樹林區": "238",
        "鶯歌區": "239",
        "三峽區": "237",
        "林口區": "244",
        "五股區": "248",
        "泰山區": "243",
        "八里區": "249",
        "深坑區": "222",
    },
    "taoyuan": {
        "桃園區": "330",
        "中壢區": "320",
        "平鎮區": "324",
        "八德區": "334",
        "楊梅區": "326",
        "蘆竹區": "338",
        "龜山區": "333",
        "龍潭區": "325",
        "大溪區": "335",
        "大園區": "337",
    },
    "taichung": {
        "中區": "400",
        "東區": "401",
        "南區": "402",
        "西區": "403",
        "北區": "404",
        "北屯區": "406",
        "西屯區": "407",
        "南屯區": "408",
        "太平區": "411",
        "大里區": "412",
        "豐原區": "420",
    },
    "kaohsiung": {
        "新興區": "800",
        "前金區": "801",
        "苓雅區": "802",
        "鹽埕區": "803",
        "鼓山區": "804",
        "前鎮區": "806",
        "三民區": "807",
        "楠梓區": "811",
        "小港區": "812",
        "左營區": "813",
        "仁武區": "814",
        "鳳山區": "830",
    },
}

# Flat list of districts per region (for CLI introspection).
DISTRICTS: dict[str, list[str]] = {
    region: list(dmap.keys()) for region, dmap in DISTRICT_ZIP_CODES.items()
}


@dataclass(frozen=True, slots=True)
class HbhousingSearchParams:
    """Parameters for an hbhousing search page request."""

    page_url: str
    referer_url: str


def search_params(
    region: str,
    *,
    page: int = 1,
    districts: list[str] | None = None,
    min_price_wan: int | None = None,
    max_price_wan: int | None = None,
    min_rooms: int | None = None,
    max_rooms: int | None = None,
    styles: list[str] | None = None,
) -> HbhousingSearchParams:
    """Build hbhousing search URL from region + optional filters.

    Args:
        region: CLI region key (e.g. 'taipei').
        page: Page number (1-indexed). Page 1 has no suffix.
        districts: District names (e.g. ['內湖區']). Mapped to zip codes.
        min_price_wan: Minimum price in 萬 (0 if None).
        max_price_wan: Maximum price in 萬.
        min_rooms: Minimum room count.
        max_rooms: Maximum room count.
        styles: Building styles (e.g. ['大樓', '華廈']).

    Raises:
        ValueError: For unknown region or district.
    """
    region = region.lower()
    if region not in REGION_NAMES:
        raise ValueError(f"Unknown hbhousing region '{region}'. Supported: {sorted(REGION_NAMES)}")

    city_key = REGION_NAMES[region]
    zip_map = DISTRICT_ZIP_CODES[region]

    # Resolve zip codes from district names.
    if districts:
        zip_codes: list[str] = []
        for d in districts:
            if d not in zip_map:
                raise ValueError(
                    f"Unknown district '{d}' for region '{region}'. Valid: {sorted(zip_map)}"
                )
            zip_codes.append(zip_map[d])
    else:
        # All districts in the region.
        zip_codes = list(zip_map.values())

    zip_segment = "-".join(zip_codes)

    # Build filter segments.
    filter_segments: list[str] = []

    # Price filter: {min}-{max}-price
    if min_price_wan is not None or max_price_wan is not None:
        p_min = min_price_wan if min_price_wan is not None else 0
        p_max = max_price_wan if max_price_wan is not None else 0
        filter_segments.append(f"{p_min}-{p_max}-price")

    # Room filter: {min}_{max}-room-pattern
    if min_rooms is not None or max_rooms is not None:
        r_min = min_rooms if min_rooms is not None else 0
        r_max = max_rooms if max_rooms is not None else 0
        filter_segments.append(f"{r_min}_{r_max}-room-pattern")

    # Style filter: {style1}-{style2}-style
    if styles:
        style_segment = "-".join(styles) + "-style"
        filter_segments.append(style_segment)

    # Page segment: only for page > 1.
    if page > 1:
        filter_segments.append(f"{page}-page")

    # Assemble URL path.
    city_encoded = quote(city_key, safe="")
    path_parts = ["buyhouse", city_encoded, zip_segment]
    if filter_segments:
        path_parts.extend(filter_segments)

    # Trailing slash is required.
    path = "/".join(path_parts) + "/"
    page_url = f"{_BASE_URL}/{path}"

    # Referer: the page 1 version without page suffix.
    referer_parts = ["buyhouse", city_encoded, zip_segment]
    referer_filter_segments = [s for s in filter_segments if not s.endswith("-page")]
    if referer_filter_segments:
        referer_parts.extend(referer_filter_segments)
    referer_path = "/".join(referer_parts) + "/"
    referer_url = f"{_BASE_URL}/{referer_path}"

    return HbhousingSearchParams(page_url=page_url, referer_url=referer_url)
