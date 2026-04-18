"""591 search-page parser.

Given the HTML of a 591 search/listing page, returns a list of `Listing`
domain objects. Selectors are isolated as constants so they can be
updated without touching parsing logic.

NOTE: The selectors below match the fixture in tests and reflect the
historical 591 markup. The live site changes frequently; update these
constants and the fixture together when the markup shifts.
"""
from __future__ import annotations

from urllib.parse import urljoin

from selectolax.parser import HTMLParser, Node

from alc_crawler.adapters.sites.site_591.parsing_helpers import (
    parse_attribute_tokens,
    parse_chinese_price,
    parse_taiwan_address,
)
from alc_crawler.domain.listing import Listing
from alc_crawler.domain.value_objects import ListingId, Price

_SITE = "591"
_BASE_URL = "https://sale.591.com.tw"

# Selector constants -- update here when 591 changes markup.
_ITEM_SELECTOR = "li.houseList-item"
_ITEM_ID_ATTR = "data-bind"
_TITLE_SELECTOR = "a.houseList-item-title"
_ADDRESS_SELECTOR = ".houseList-item-address"
_PRICE_NUM_SELECTOR = ".houseList-item-price-num"
_PRICE_UNIT_SELECTOR = ".houseList-item-price-unit"
_ATTRS_SELECTOR = ".houseList-item-attrs span"


class Site591SearchParser:
    def parse(self, html: str, *, source_url: str) -> list[Listing]:
        tree = HTMLParser(html)
        listings: list[Listing] = []
        for node in tree.css(_ITEM_SELECTOR):
            listing = self._parse_item(node, source_url=source_url)
            if listing is not None:
                listings.append(listing)
        return listings

    def _parse_item(self, node: Node, *, source_url: str) -> Listing | None:
        external_id = node.attributes.get(_ITEM_ID_ATTR)
        if not external_id:
            return None

        title_node = node.css_first(_TITLE_SELECTOR)
        if title_node is None or not title_node.text(strip=True):
            return None
        title = title_node.text(strip=True)
        href = title_node.attributes.get("href") or ""
        url = urljoin(_BASE_URL, href) if href else urljoin(source_url, "")

        price_num = node.css_first(_PRICE_NUM_SELECTOR)
        price_unit = node.css_first(_PRICE_UNIT_SELECTOR)
        if price_num is None:
            return None
        amount = parse_chinese_price(
            price_num.text(strip=True),
            price_unit.text(strip=True) if price_unit else "",
        )
        if amount is None:
            return None

        addr_node = node.css_first(_ADDRESS_SELECTOR)
        address = parse_taiwan_address(addr_node.text(strip=True)) if addr_node else None
        if address is None:
            return None

        attrs = parse_attribute_tokens(
            [n.text(strip=True) for n in node.css(_ATTRS_SELECTOR)]
        )

        try:
            return Listing(
                id=ListingId(_SITE, external_id),
                title=title,
                url=url,
                price=Price(amount=amount, currency="TWD"),
                address=address,
                attributes=attrs,
            )
        except ValueError:
            return None
