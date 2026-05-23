"""Unit tests for hbhousing search URL generation."""

from __future__ import annotations

import pytest

from alc_crawler.adapters.sites.site_hbhousing.search_urls import search_params


class TestSearchParams:
    def test_basic_region_single_district(self) -> None:
        result = search_params("taipei", districts=["內湖區"])
        assert "buyhouse/" in result.page_url
        assert "114" in result.page_url
        assert result.page_url.endswith("/")

    def test_page_1_no_page_suffix(self) -> None:
        result = search_params("taipei", districts=["內湖區"], page=1)
        assert "-page" not in result.page_url

    def test_page_2_has_page_suffix(self) -> None:
        result = search_params("taipei", districts=["內湖區"], page=2)
        assert "2-page/" in result.page_url

    def test_price_filter(self) -> None:
        result = search_params("taipei", districts=["大安區"], max_price_wan=3500)
        assert "0-3500-price" in result.page_url

    def test_price_filter_with_min(self) -> None:
        result = search_params(
            "taipei", districts=["大安區"], min_price_wan=1000, max_price_wan=3500
        )
        assert "1000-3500-price" in result.page_url

    def test_room_filter(self) -> None:
        result = search_params("taipei", districts=["內湖區"], min_rooms=2, max_rooms=3)
        assert "2_3-room-pattern" in result.page_url

    def test_style_filter(self) -> None:
        result = search_params("taipei", districts=["內湖區"], styles=["大樓", "華廈"])
        assert "大樓-華廈-style" in result.page_url

    def test_multiple_districts_join_zips(self) -> None:
        result = search_params("taipei", districts=["內湖區", "南港區"])
        assert "114-115" in result.page_url

    def test_unknown_region_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown hbhousing region"):
            search_params("invalid-region")

    def test_unknown_district_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown district"):
            search_params("taipei", districts=["不存在區"])

    def test_referer_url_no_page(self) -> None:
        result = search_params("taipei", districts=["內湖區"], page=3)
        assert "-page" not in result.referer_url
        assert "114" in result.referer_url

    def test_all_regions_valid(self) -> None:
        for region in ("taipei", "new-taipei", "taoyuan", "taichung", "kaohsiung"):
            result = search_params(region)
            assert "hbhousing.com.tw" in result.page_url

    def test_combined_filters_and_page(self) -> None:
        result = search_params(
            "taipei",
            districts=["內湖區"],
            min_price_wan=0,
            max_price_wan=3500,
            min_rooms=2,
            max_rooms=3,
            page=2,
        )
        assert "0-3500-price" in result.page_url
        assert "2_3-room-pattern" in result.page_url
        assert "2-page/" in result.page_url
