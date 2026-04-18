"""Integration tests for the `alc-crawler regions` introspection subcommand."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from alc_crawler.interfaces.cli.main import app

pytestmark = pytest.mark.integration


def test_regions_lists_all_supported_regions() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["regions"])

    assert result.exit_code == 0, result.output
    # All 5 known region keys appear.
    for key in ("taipei", "new-taipei", "taoyuan", "taichung", "kaohsiung"):
        assert key in result.output, f"missing region key {key!r} in output"
    # Region id column shows real 591 ids.
    assert "1" in result.output  # taipei
    assert "17" in result.output  # kaohsiung


def test_regions_shows_taipei_section_table() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["regions"])

    assert result.exit_code == 0, result.output
    # Section ids for 台北市 are documented inline.
    assert "內湖" in result.output
    assert "10" in result.output
    assert "信義" in result.output
    assert "7" in result.output


def test_regions_shows_new_taipei_section_table() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["regions"])

    assert result.exit_code == 0, result.output
    # A handful of well-known 新北 districts and their probed ids.
    assert "板橋" in result.output  # id 26
    assert "26" in result.output
    assert "新店" in result.output  # id 34
    assert "34" in result.output
    assert "淡水" in result.output  # id 50
    assert "50" in result.output


def test_regions_shows_shape_table() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["regions"])

    assert result.exit_code == 0, result.output
    assert "公寓" in result.output
    assert "電梯大樓" in result.output
    assert "透天厝" in result.output
