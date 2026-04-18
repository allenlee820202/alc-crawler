"""591 BFF JSON API parser.

The live 591 site is a Vue/Nuxt SPA; listings are loaded by the browser
via XHR to https://bff-house.591.com.tw/v1/web/sale/list. This parser
consumes that JSON directly and converts each item into a domain Listing.
"""
from __future__ import annotations

import json
from typing import Any

from alc_crawler.domain.listing import Listing
from alc_crawler.domain.value_objects import Address, ListingId, Price

_SITE = "591"
_DETAIL_URL = "https://sale.591.com.tw/home/house/detail/2/{house_id}.html"


class Site591ApiParser:
    def parse(self, body: str, *, source_url: str) -> list[Listing]:
        del source_url  # unused; kept for SearchPageParser protocol compatibility
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc}") from exc

        if data.get("status") != 1:
            raise ValueError(f"591 API returned non-success status: {data.get('status')!r}")

        items = (data.get("data") or {}).get("house_list") or []
        listings: list[Listing] = []
        for item in items:
            listing = self._parse_item(item)
            if listing is not None:
                listings.append(listing)
        return listings

    def _parse_item(self, item: dict[str, Any]) -> Listing | None:
        house_id = item.get("houseid")
        title = (item.get("title") or "").strip()
        region = (item.get("region_name") or "").strip()
        section = (item.get("section_name") or "").strip()
        raw_addr = (item.get("address") or "").strip()
        price_wan = item.get("price")  # in 萬

        if not house_id or not title or not region or not section or price_wan is None:
            return None

        try:
            amount = round(float(price_wan) * 10_000)
        except (TypeError, ValueError):
            return None
        if amount <= 0:
            return None

        external_id = str(house_id)
        try:
            return Listing(
                id=ListingId(_SITE, external_id),
                title=title,
                url=_DETAIL_URL.format(house_id=external_id),
                price=Price(amount=amount, currency="TWD"),
                address=Address(city=region, district=section, raw=raw_addr or section),
                attributes=_extract_attrs(item),
            )
        except ValueError:
            return None


def _extract_attrs(item: dict[str, Any]) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for src_key, dst_key in (
        ("room", "room"),
        ("floor", "floor"),
        ("shape_name", "shape"),
        ("kind_name", "kind"),
        ("housetype", "housetype"),
        ("houseage", "houseage"),
        ("unit_price", "unit_price"),
    ):
        value = item.get(src_key)
        if value not in (None, ""):
            attrs[dst_key] = str(value)
    if (area := item.get("area")) not in (None, ""):
        attrs["area_ping"] = str(area)
    if (mainarea := item.get("mainarea")) not in (None, ""):
        attrs["mainarea_ping"] = str(mainarea)
    return attrs
