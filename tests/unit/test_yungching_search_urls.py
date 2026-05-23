"""Unit tests for Yungching search URL generation."""
from __future__ import annotations

import pytest

from alc_crawler.adapters.sites.site_yungching.search_urls import search_params


class TestSearchParams:
    def test_basic_region(self) -> None:
        result = search_params("taipei")
        assert "area=%E5%8F%B0%E5%8C%97%E5%B8%82" in result.api_url
        assert "pg=1" in result.api_url
        assert "ps=30" in result.api_url

    def test_page_param(self) -> None:
        result = search_params("taipei", page=3)
        assert "pg=3" in result.api_url

    def test_district_filter(self) -> None:
        result = search_params("taipei", districts=["大安區"])
        assert "%E5%8F%B0%E5%8C%97%E5%B8%82-%E5%A4%A7%E5%AE%89%E5%8D%80" in result.api_url

    def test_multiple_districts(self) -> None:
        result = search_params("taipei", districts=["大安區", "信義區"])
        assert "area=" in result.api_url
        # Both districts should be in the URL
        assert "%E5%A4%A7%E5%AE%89%E5%8D%80" in result.api_url
        assert "%E4%BF%A1%E7%BE%A9%E5%8D%80" in result.api_url

    def test_price_filter(self) -> None:
        result = search_params("taipei", min_price_wan=1000, max_price_wan=3000)
        assert "minPrice=1000" in result.api_url
        assert "maxPrice=3000" in result.api_url

    def test_room_filter(self) -> None:
        result = search_params("taipei", min_rooms=2, max_rooms=3)
        assert "minRoom=2" in result.api_url
        assert "maxRoom=3" in result.api_url

    def test_age_filter(self) -> None:
        result = search_params("taipei", max_age=25.0)
        assert "maxAge=25.0" in result.api_url

    def test_unknown_region_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown Yungching region"):
            search_params("invalid-region")

    def test_referer_url(self) -> None:
        result = search_params("taipei", districts=["大安區"])
        assert result.referer_url.startswith("https://buy.yungching.com.tw/list?")

    def test_all_regions_valid(self) -> None:
        for region in ("taipei", "new-taipei", "taoyuan", "taichung", "kaohsiung"):
            result = search_params(region)
            assert "buy.yungching.com.tw/api/v2/list" in result.api_url
