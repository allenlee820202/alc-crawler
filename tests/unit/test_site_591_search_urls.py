"""Unit tests for 591 region -> search URL mapping."""
from __future__ import annotations

import pytest

from alc_crawler.adapters.sites.site_591.search_urls import (
    search_url_for_region,
    search_urls_for_region,
)


def test_known_region_returns_both_urls() -> None:
    urls = search_urls_for_region("taipei")
    assert urls.referer_url.startswith("https://sale.591.com.tw/")
    assert "regionid=1" in urls.referer_url
    assert urls.api_url.startswith("https://bff-house.591.com.tw/")
    assert "regionid=1" in urls.api_url
    assert "firstRow=0" in urls.api_url


def test_pagination_offset_uses_page_size_30() -> None:
    urls = search_urls_for_region("taipei", page=3)
    assert "firstRow=60" in urls.api_url
    assert "firstRow=60" in urls.referer_url


def test_unknown_region_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown 591 region"):
        search_urls_for_region("atlantis")


def test_region_lookup_is_case_insensitive() -> None:
    assert search_urls_for_region("TAIPEI") == search_urls_for_region("taipei")


def test_back_compat_helper_returns_api_url() -> None:
    assert search_url_for_region("taipei") == search_urls_for_region("taipei").api_url
