"""Lifecycle status: where a listing sits in its on-market life.

Inferred from snapshot recency rather than recorded explicitly:
- ON_SALE  : seen within `on_sale_days` (default 1) of today
- STALE    : seen within `stale_days`  (default 3) of today
- OFF_SALE : not seen within `stale_days`

Thresholds depend on crawl cadence; daily crawls map well to 1/3.
Surface as config; never hardcode at call sites.
"""
from __future__ import annotations

from datetime import date
from enum import StrEnum


class LifecycleStatus(StrEnum):
    ON_SALE = "on_sale"
    STALE = "stale"
    OFF_SALE = "off_sale"


def classify_status(
    *,
    last_seen: date,
    today: date,
    on_sale_days: int = 1,
    stale_days: int = 3,
) -> LifecycleStatus:
    if on_sale_days > stale_days:
        raise ValueError(
            "thresholds inverted: on_sale_days must be <= stale_days"
        )
    days_since = (today - last_seen).days
    if days_since <= on_sale_days:
        return LifecycleStatus.ON_SALE
    if days_since <= stale_days:
        return LifecycleStatus.STALE
    return LifecycleStatus.OFF_SALE
