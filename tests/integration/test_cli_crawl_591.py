"""End-to-end CUJ test for the CLI:

User runs `alc-crawler crawl 591 --region taipei` and the listings end up
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

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "site_591"


def _mock_591() -> None:
    """Mock both the warm-up page and the BFF JSON API."""
    api_body = (FIXTURES / "api_search_taipei_page1.json").read_text(encoding="utf-8")
    respx.get(host="sale.591.com.tw").mock(
        return_value=httpx.Response(
            200, text="<html/>", headers={"set-cookie": "T591_TOKEN=test; Path=/"}
        )
    )
    respx.get(host="bff-house.591.com.tw").mock(return_value=httpx.Response(200, text=api_body))


@respx.mock
def test_crawl_591_taipei_persists_listings(tmp_path: Path) -> None:
    _mock_591()
    db_path = tmp_path / "listings.sqlite"

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["crawl", "591", "--region", "taipei", "--db", str(db_path)],
    )

    assert result.exit_code == 0, result.output
    assert "persisted=" in result.output
    # Fixture contains 32 items; one is a pre-sale with price=0 (filtered out).
    assert "persisted=31" in result.output

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT COUNT(*), MIN(price_amount), MAX(price_amount) "
            "FROM listings WHERE site=?",
            ("591",),
        ).fetchall()
    count, min_price, max_price = rows[0]
    assert count == 31
    assert min_price >= 1_000_000
    assert max_price > min_price


@respx.mock
def test_crawl_591_accepts_insecure_flag(tmp_path: Path) -> None:
    """`--insecure` is a documented escape hatch for sites with broken cert chains."""
    _mock_591()
    db_path = tmp_path / "listings.sqlite"

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["crawl", "591", "--region", "taipei", "--db", str(db_path), "--insecure"],
    )

    assert result.exit_code == 0, result.output
    assert "persisted=31" in result.output


@respx.mock
def test_crawl_591_sends_referer_to_bff(tmp_path: Path) -> None:
    """591 BFF returns empty data without a same-origin Referer; verify we send one."""
    api_body = (FIXTURES / "api_search_taipei_page1.json").read_text(encoding="utf-8")
    respx.get(host="sale.591.com.tw").mock(return_value=httpx.Response(200, text="<html/>"))
    api_route = respx.get(host="bff-house.591.com.tw").mock(
        return_value=httpx.Response(200, text=api_body)
    )

    runner = CliRunner()
    result = runner.invoke(
        app, ["crawl", "591", "--region", "taipei", "--db", str(tmp_path / "x.sqlite")]
    )

    assert result.exit_code == 0, result.output
    referer = api_route.calls.last.request.headers.get("referer", "")
    assert "sale.591.com.tw" in referer
