"""Tests for CrawlRun provenance value object."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from alc_crawler.tracking.domain.crawl_run import CrawlRun, RunStatus


def _run(**overrides: object) -> CrawlRun:
    base: dict[str, object] = {
        "run_id": "run-1",
        "started_at": datetime(2026, 5, 9, 6, 0, 0),
        "completed_at": datetime(2026, 5, 9, 6, 5, 0),
        "site": "591",
        "region": "taipei",
        "pages_fetched": 50,
        "listings_seen": 1500,
        "listings_persisted": 1490,
        "status": RunStatus.OK,
    }
    base.update(overrides)
    return CrawlRun(**base)  # type: ignore[arg-type]


def test_crawl_run_holds_required_fields() -> None:
    run = _run()
    assert run.status is RunStatus.OK
    assert run.listings_persisted == 1490


def test_crawl_run_rejects_blank_run_id() -> None:
    with pytest.raises(ValueError, match="run_id"):
        _run(run_id="  ")


def test_crawl_run_rejects_blank_site_or_region() -> None:
    with pytest.raises(ValueError, match="site"):
        _run(site="")
    with pytest.raises(ValueError, match="region"):
        _run(region="")


def test_crawl_run_rejects_negative_counts() -> None:
    for field in ("pages_fetched", "listings_seen", "listings_persisted"):
        with pytest.raises(ValueError, match=field):
            _run(**{field: -1})


def test_crawl_run_rejects_completed_before_started() -> None:
    with pytest.raises(ValueError, match="completed_at"):
        _run(
            started_at=datetime(2026, 5, 9, 6, 0, 0),
            completed_at=datetime(2026, 5, 9, 5, 59, 0),
        )


def test_crawl_run_allows_completed_at_none_for_in_progress() -> None:
    run = _run(completed_at=None, status=RunStatus.PARTIAL)
    assert run.completed_at is None


def test_crawl_run_status_string_value() -> None:
    assert RunStatus.OK.value == "ok"
    assert RunStatus.FAILED.value == "failed"


def test_crawl_run_completed_equal_started_ok() -> None:
    t = datetime(2026, 5, 9, 6, 0, 0)
    run = _run(started_at=t, completed_at=t)
    assert run.completed_at == t


def test_crawl_run_long_runs_ok() -> None:
    start = datetime(2026, 5, 9, 6, 0, 0)
    run = _run(started_at=start, completed_at=start + timedelta(hours=2))
    assert run.completed_at is not None
