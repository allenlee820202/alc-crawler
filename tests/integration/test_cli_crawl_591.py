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


@respx.mock
def test_crawl_591_taipei_persists_listings(tmp_path: Path) -> None:
    html = (FIXTURES / "search_taipei_page1.html").read_text(encoding="utf-8")
    respx.get(host="sale.591.com.tw").mock(return_value=httpx.Response(200, text=html))
    db_path = tmp_path / "listings.sqlite"

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["crawl", "591", "--region", "taipei", "--db", str(db_path)],
    )

    assert result.exit_code == 0, result.output
    assert "persisted=2" in result.output

    # Verify in the database directly (sync sqlite check to avoid nesting loops).
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT external_id, price_amount, address_district, observed_at "
            "FROM listings WHERE site=? ORDER BY external_id",
            ("591",),
        ).fetchall()

    assert len(rows) == 2
    by_id = {row[0]: row for row in rows}
    assert by_id["12345"][1] == 15_800_000
    assert by_id["12345"][2] == "大安區"
    assert by_id["12345"][3] is not None  # observed_at set


@respx.mock
def test_crawl_591_accepts_insecure_flag(tmp_path: Path) -> None:
    """`--insecure` is a documented escape hatch for sites with broken cert chains."""
    html = (FIXTURES / "search_taipei_page1.html").read_text(encoding="utf-8")
    respx.get(host="sale.591.com.tw").mock(return_value=httpx.Response(200, text=html))
    db_path = tmp_path / "listings.sqlite"

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["crawl", "591", "--region", "taipei", "--db", str(db_path), "--insecure"],
    )

    assert result.exit_code == 0, result.output
    assert "persisted=2" in result.output
