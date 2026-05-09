"""Integration tests for DuckDbWatchlistRepository."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.infrastructure.duckdb.watchlist_repository import (
    DuckDbWatchlistRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(tmp_path: Path) -> DuckDbWatchlistRepository:
    r = DuckDbWatchlistRepository(tmp_path / "tracking.duckdb")
    r.initialize()
    return r


class TestAdd:
    def test_returns_watched_listing_with_added_at(
        self, repo: DuckDbWatchlistRepository
    ) -> None:
        w = repo.add(ListingId("591", "1"))
        assert w.listing_id == ListingId("591", "1")
        assert w.added_at is not None
        assert w.nickname is None

    def test_persists_nickname(self, repo: DuckDbWatchlistRepository) -> None:
        w = repo.add(ListingId("591", "1"), nickname="dream home")
        assert w.nickname == "dream home"
        assert repo.get(ListingId("591", "1")) == w

    def test_idempotent_does_not_bump_added_at(
        self, repo: DuckDbWatchlistRepository
    ) -> None:
        first = repo.add(ListingId("591", "1"))
        # Sleep enough to make added_at differ if it were re-set.
        time.sleep(0.01)
        second = repo.add(ListingId("591", "1"))
        assert second.added_at == first.added_at

    def test_re_add_updates_nickname(
        self, repo: DuckDbWatchlistRepository
    ) -> None:
        repo.add(ListingId("591", "1"), nickname="old")
        w = repo.add(ListingId("591", "1"), nickname="new")
        assert w.nickname == "new"


class TestRemove:
    def test_returns_true_when_removed(
        self, repo: DuckDbWatchlistRepository
    ) -> None:
        repo.add(ListingId("591", "1"))
        assert repo.remove(ListingId("591", "1")) is True
        assert repo.get(ListingId("591", "1")) is None

    def test_returns_false_when_not_watched(
        self, repo: DuckDbWatchlistRepository
    ) -> None:
        assert repo.remove(ListingId("591", "999")) is False

    def test_only_removes_target(self, repo: DuckDbWatchlistRepository) -> None:
        repo.add(ListingId("591", "1"))
        repo.add(ListingId("591", "2"))
        repo.remove(ListingId("591", "1"))
        assert repo.get(ListingId("591", "1")) is None
        assert repo.get(ListingId("591", "2")) is not None


class TestGet:
    def test_returns_none_when_absent(self, repo: DuckDbWatchlistRepository) -> None:
        assert repo.get(ListingId("591", "999")) is None

    def test_round_trips_nickname(self, repo: DuckDbWatchlistRepository) -> None:
        added = repo.add(ListingId("591", "1"), nickname="x")
        got = repo.get(ListingId("591", "1"))
        assert got == added


class TestListAll:
    def test_empty(self, repo: DuckDbWatchlistRepository) -> None:
        assert list(repo.list_all()) == []

    def test_oldest_first(self, repo: DuckDbWatchlistRepository) -> None:
        a = repo.add(ListingId("591", "1"))
        time.sleep(0.01)
        b = repo.add(ListingId("591", "2"))
        time.sleep(0.01)
        c = repo.add(ListingId("yungching", "9"))
        all_ = list(repo.list_all())
        assert [w.listing_id for w in all_] == [
            a.listing_id,
            b.listing_id,
            c.listing_id,
        ]

    def test_site_filter(self, repo: DuckDbWatchlistRepository) -> None:
        repo.add(ListingId("591", "1"))
        repo.add(ListingId("591", "2"))
        repo.add(ListingId("yungching", "9"))
        out = list(repo.list_all(site="591"))
        assert {w.listing_id.site for w in out} == {"591"}
        assert len(out) == 2


class TestInitialize:
    def test_initialize_is_idempotent(self, tmp_path: Path) -> None:
        r = DuckDbWatchlistRepository(tmp_path / "x.duckdb")
        r.initialize()
        r.initialize()  # must not raise
        r.add(ListingId("591", "1"))
        assert r.get(ListingId("591", "1")) is not None

    def test_separate_repo_instances_share_state(self, tmp_path: Path) -> None:
        path = tmp_path / "x.duckdb"
        r1 = DuckDbWatchlistRepository(path)
        r1.initialize()
        r1.add(ListingId("591", "1"), nickname="seen")
        r2 = DuckDbWatchlistRepository(path)
        # initialize on a second instance must not wipe data.
        r2.initialize()
        got = r2.get(ListingId("591", "1"))
        assert got is not None
        assert got.nickname == "seen"
