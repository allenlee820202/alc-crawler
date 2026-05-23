"""End-to-end CUJ test for the CLI:

User runs `alc-crawler crawl yungching --region taipei` and the listings end up
in the SQLite database.

Network is mocked at the httpx layer with respx so this test is fast
and deterministic.
"""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from typer.testing import CliRunner

from alc_crawler.interfaces.cli.main import app

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "site_yungching"


def _mock_yungching() -> respx.Route:
    """Mock the Yungching API endpoint."""
    api_body = (FIXTURES / "api_list_taipei_page1.json").read_text(encoding="utf-8")
    route = respx.get(host="buy.yungching.com.tw").mock(
        return_value=httpx.Response(200, text=api_body)
    )
    return route


@respx.mock
def test_crawl_yungching_taipei_persists_listings(tmp_path: Path) -> None:
    _mock_yungching()
    db_path = tmp_path / "listings.sqlite"

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["crawl", "yungching", "--region", "taipei", "--db", str(db_path)],
    )

    assert result.exit_code == 0, result.output
    assert "persisted=" in result.output
    # Fixture has 4 items: 2 valid (no caseSId and zero price dropped)
    assert "persisted=2" in result.output

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT COUNT(*), MIN(price_amount), MAX(price_amount) "
            "FROM listings WHERE site=?",
            ("yungching",),
        ).fetchall()
    count, min_price, max_price = rows[0]
    assert count == 2
    assert min_price > 0
    assert max_price > min_price


@respx.mock
def test_crawl_yungching_with_district_filter(tmp_path: Path) -> None:
    route = _mock_yungching()
    db_path = tmp_path / "listings.sqlite"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "crawl",
            "yungching",
            "--region",
            "taipei",
            "--district",
            "大安區",
            "--db",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    # Verify district was sent in URL
    last_url = str(route.calls.last.request.url)
    assert "%E5%A4%A7%E5%AE%89%E5%8D%80" in last_url


@respx.mock
def test_crawl_yungching_with_price_and_room_filters(tmp_path: Path) -> None:
    route = _mock_yungching()
    db_path = tmp_path / "listings.sqlite"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "crawl",
            "yungching",
            "--region",
            "taipei",
            "--min-price-wan",
            "1000",
            "--max-price-wan",
            "4000",
            "--min-rooms",
            "2",
            "--max-rooms",
            "3",
            "--max-age",
            "25",
            "--db",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    last_url = str(route.calls.last.request.url)
    assert "minPrice=1000" in last_url
    assert "maxPrice=4000" in last_url
    assert "minRoom=2" in last_url
    assert "maxRoom=3" in last_url
    assert "maxAge=25" in last_url


@respx.mock
def test_crawl_yungching_unsupported_region(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["crawl", "yungching", "--region", "invalid", "--db", str(tmp_path / "x.sqlite")],
    )
    assert result.exit_code != 0


def test_crawl_unsupported_site(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["crawl", "fake-site", "--region", "taipei", "--db", str(tmp_path / "x.sqlite")],
    )
    assert result.exit_code != 0
    assert "Unsupported site" in result.output
