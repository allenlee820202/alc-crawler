"""Unit tests for 591 region -> search URL mapping."""
from __future__ import annotations

import pytest

from alc_crawler.adapters.sites.site_591.search_urls import search_url_for_region


def test_known_region_returns_url() -> None:
    url = search_url_for_region("taipei")
    assert url.startswith("https://sale.591.com.tw/")
    assert "regionid=1" in url
    assert "firstRow=0" in url


def test_pagination_offset() -> None:
    url = search_url_for_region("taipei", page=3)
    assert "firstRow=60" in url


def test_unknown_region_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown 591 region"):
        search_url_for_region("atlantis")


def test_region_lookup_is_case_insensitive() -> None:
    assert search_url_for_region("TAIPEI") == search_url_for_region("taipei")
