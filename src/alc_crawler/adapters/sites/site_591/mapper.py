"""591 -> CanonicalListing anti-corruption mapper.

Stage 2 of the 591 parsing pipeline. The mapper is the ONLY place that
knows about both 591's raw shape (`Site591RawItem`) and the canonical
domain shape (`CanonicalListing`). When a second site joins, it gets
its own sibling mapper; this file is never edited for non-591 reasons.

Fields useful for downstream filtering/sorting (price, area, unit price,
age, room layout, floor, community, posted_at, view_count) are promoted
to first-class. Softer presentational data (shape/kind labels, agent
nick, photo count, has_video, condition ids) lives in `attributes` to
keep the canonical schema small.
"""
from __future__ import annotations

from datetime import UTC, datetime

from alc_crawler.adapters.sites.site_591.raw_item import Site591RawItem
from alc_crawler.domain.canonical_listing import CanonicalListing
from alc_crawler.domain.value_objects import Address, ListingId, Price

_SITE = "591"
_DETAIL_URL = "https://sale.591.com.tw/home/house/detail/2/{house_id}.html"


class Site591Mapper:
    def to_canonical(self, raw: Site591RawItem) -> CanonicalListing:
        return CanonicalListing(
            id=ListingId(_SITE, raw.house_id),
            title=raw.title,
            url=_DETAIL_URL.format(house_id=raw.house_id),
            price=Price(amount=round(raw.price_wan * 10_000), currency="TWD"),
            address=Address(
                city=raw.region_name,
                district=raw.section_name,
                raw=raw.address or raw.section_name,
            ),
            area_ping=raw.area,
            main_area_ping=raw.main_area,
            unit_price_per_ping=raw.unit_price,
            house_age_years=raw.house_age,
            room_layout=raw.room,
            floor=raw.floor,
            community_name=raw.community_name,
            posted_at=_epoch_to_utc(raw.posttime),
            view_count=raw.browsenum,
            attributes=_soft_attributes(raw),
        )


def _epoch_to_utc(ts: int | None) -> datetime | None:
    if ts is None or ts <= 0:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)


def _soft_attributes(raw: Site591RawItem) -> dict[str, str]:
    attrs: dict[str, str] = {}
    if raw.shape_name:
        attrs["shape"] = raw.shape_name
    if raw.kind_name:
        attrs["kind"] = raw.kind_name
    if raw.housetype:
        attrs["housetype"] = raw.housetype
    if raw.unit_price_label:
        attrs["unit_price_label"] = raw.unit_price_label
    if raw.nick_name:
        attrs["agent_nick_name"] = raw.nick_name
    if raw.photo_num is not None:
        attrs["photo_count"] = str(raw.photo_num)
    if raw.is_video is not None:
        attrs["has_video"] = str(raw.is_video)
    if raw.condition_ids:
        attrs["condition_ids"] = ",".join(str(c) for c in raw.condition_ids)
    return attrs
