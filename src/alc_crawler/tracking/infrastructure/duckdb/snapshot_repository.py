"""DuckDB-backed implementation of SnapshotRepository.

Each method opens its own short-lived connection. DuckDB allows only
one writer at a time per file; for our batch-job usage this is fine
and avoids leaking handles across long-lived processes.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

import duckdb

from alc_crawler.domain.value_objects import ListingId
from alc_crawler.tracking.domain.crawl_run import CrawlRun
from alc_crawler.tracking.domain.snapshot import ListingSnapshot

_SCHEMA_RESOURCE = ("alc_crawler.tracking.infrastructure.duckdb", "schema.sql")


class DuckDbSnapshotRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    @contextmanager
    def _connect(self) -> Any:
        conn = duckdb.connect(str(self._db_path))
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        schema_sql = (
            resources.files(_SCHEMA_RESOURCE[0])
            .joinpath(_SCHEMA_RESOURCE[1])
            .read_text(encoding="utf-8")
        )
        with self._connect() as conn:
            conn.execute(schema_sql)

    def record_snapshots(self, snapshots: Iterable[ListingSnapshot]) -> int:
        rows = [self._snapshot_to_row(s) for s in snapshots]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO listing_snapshots (
                    snapshot_date, site, external_id, price_amount,
                    area_ping, unit_price_per_ping, house_age_years,
                    view_count, community_name, address_district, shape,
                    source_attributes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (snapshot_date, site, external_id) DO UPDATE SET
                    price_amount           = excluded.price_amount,
                    area_ping              = excluded.area_ping,
                    unit_price_per_ping    = excluded.unit_price_per_ping,
                    house_age_years        = excluded.house_age_years,
                    view_count             = excluded.view_count,
                    community_name         = excluded.community_name,
                    address_district       = excluded.address_district,
                    shape                  = excluded.shape,
                    source_attributes_json = excluded.source_attributes_json
                """,
                rows,
            )
        return len(rows)

    def record_run(self, run: CrawlRun) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO crawl_runs (
                    run_id, started_at, completed_at, site, region,
                    pages_fetched, listings_seen, listings_persisted,
                    status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run.run_id,
                    run.started_at,
                    run.completed_at,
                    run.site,
                    run.region,
                    run.pages_fetched,
                    run.listings_seen,
                    run.listings_persisted,
                    run.status.value,
                    run.error_message,
                ],
            )

    def snapshots_for_listing(
        self,
        listing_id: ListingId,
        *,
        since: date | None = None,
    ) -> Sequence[ListingSnapshot]:
        sql = """
            SELECT snapshot_date, site, external_id, price_amount,
                   area_ping, unit_price_per_ping, house_age_years,
                   view_count, community_name, address_district, shape,
                   source_attributes_json
            FROM listing_snapshots
            WHERE site = ? AND external_id = ?
        """
        params: list[Any] = [listing_id.site, listing_id.external_id]
        if since is not None:
            sql += " AND snapshot_date >= ?"
            params.append(since)
        sql += " ORDER BY snapshot_date ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def latest_snapshot_date(self, *, site: str) -> date | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(snapshot_date) FROM listing_snapshots WHERE site = ?",
                [site],
            ).fetchone()
        return row[0] if row and row[0] is not None else None

    def earliest_snapshot_on_or_after(
        self, anchor_date: date, *, site: str | None = None
    ) -> Sequence[ListingSnapshot]:
        return self._boundary_snapshots(
            anchor_date, direction="after", site=site
        )

    def latest_snapshot_on_or_before(
        self, target_date: date, *, site: str | None = None
    ) -> Sequence[ListingSnapshot]:
        return self._boundary_snapshots(
            target_date, direction="before", site=site
        )

    def _boundary_snapshots(
        self, pivot: date, *, direction: str, site: str | None
    ) -> Sequence[ListingSnapshot]:
        # ROW_NUMBER over (site, external_id) picks one row per listing:
        # the earliest >= pivot (direction='after') or latest <= pivot (direction='before').
        if direction == "after":
            where_op = ">="
            order = "ASC"
        elif direction == "before":
            where_op = "<="
            order = "DESC"
        else:  # pragma: no cover — defensive
            raise ValueError(f"unknown direction: {direction}")
        sql = f"""
            SELECT snapshot_date, site, external_id, price_amount,
                   area_ping, unit_price_per_ping, house_age_years,
                   view_count, community_name, address_district, shape,
                   source_attributes_json
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY site, external_id
                           ORDER BY snapshot_date {order}
                       ) AS rn
                FROM listing_snapshots
                WHERE snapshot_date {where_op} ?
            ) WHERE rn = 1
        """
        params: list[Any] = [pivot]
        if site is not None:
            sql = sql.replace(
                f"WHERE snapshot_date {where_op} ?",
                f"WHERE snapshot_date {where_op} ? AND site = ?",
            )
            params.append(site)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    @staticmethod
    def _snapshot_to_row(s: ListingSnapshot) -> tuple[Any, ...]:
        return (
            s.snapshot_date,
            s.listing_id.site,
            s.listing_id.external_id,
            s.price_amount,
            s.area_ping,
            s.unit_price_per_ping,
            s.house_age_years,
            s.view_count,
            s.community_name,
            s.address_district,
            s.shape,
            s.source_attributes_json,
        )

    @staticmethod
    def _row_to_snapshot(row: tuple[Any, ...]) -> ListingSnapshot:
        (
            snapshot_date,
            site,
            external_id,
            price_amount,
            area_ping,
            unit_price_per_ping,
            house_age_years,
            view_count,
            community_name,
            address_district,
            shape,
            source_attributes_json,
        ) = row
        return ListingSnapshot(
            snapshot_date=snapshot_date,
            listing_id=ListingId(site, external_id),
            price_amount=price_amount,
            area_ping=area_ping,
            unit_price_per_ping=unit_price_per_ping,
            house_age_years=house_age_years,
            view_count=view_count,
            community_name=community_name,
            address_district=address_district,
            shape=shape,
            source_attributes_json=source_attributes_json,
        )
