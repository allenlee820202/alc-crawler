"""Typer CLI entry point for the tracking submodule.

Separate console script (`alc-tracker`) so the crawler binary stays
focused. Three subcommands:

  alc-tracker snapshot       --canonical-db PATH --tracking-db PATH [--date YYYY-MM-DD]
  alc-tracker price-changes  --tracking-db PATH --since DATE [--until DATE] [--only-drops]
  alc-tracker market-summary --tracking-db PATH [--date YYYY-MM-DD]

Output is plain text to stdout (no rendering yet — Commit F adds
markdown tables and matplotlib charts). Stdout-only design means
downstream Slack posting is a separate hop.
"""
from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import typer

from alc_crawler.infrastructure.persistence.sqlite.listing_repository import (
    SqliteListingRepository,
)
from alc_crawler.tracking.application.use_cases.build_market_summary import (
    BuildMarketSummary,
)
from alc_crawler.tracking.application.use_cases.detect_price_changes import (
    DetectPriceChanges,
)
from alc_crawler.tracking.application.use_cases.record_daily_snapshots import (
    RecordDailySnapshots,
)
from alc_crawler.tracking.infrastructure.duckdb.snapshot_repository import (
    DuckDbSnapshotRepository,
)
from alc_crawler.tracking.interfaces.reports.charts import (
    render_unit_price_distribution_chart,
)
from alc_crawler.tracking.interfaces.reports.markdown import (
    render_market_summary,
    render_price_changes,
)

app = typer.Typer(
    help=(
        "Time-series tracking on top of canonical listings.\n\n"
        "Daily flow:\n"
        "  1) Crawl writes canonical SQLite (alc-crawler).\n"
        "  2) `alc-tracker snapshot` copies today's canonical state\n"
        "     into a tracking DuckDB.\n"
        "  3) `alc-tracker price-changes` / `market-summary` produce\n"
        "     reports against the tracking DuckDB."
    ),
    no_args_is_help=True,
)


@app.command()
def snapshot(
    canonical_db: Path = typer.Option(
        ..., "--canonical-db", help="Path to canonical SQLite (read-only)."
    ),
    tracking_db: Path = typer.Option(
        ..., "--tracking-db", help="Path to tracking DuckDB (created if absent)."
    ),
    snapshot_date: str | None = typer.Option(
        None,
        "--date",
        help="Snapshot date (YYYY-MM-DD). Defaults to today.",
    ),
) -> None:
    """Record one snapshot of every canonical listing for `--date`.

    Idempotent: re-running for the same date overwrites that day's rows.
    """
    target = _parse_date(snapshot_date) if snapshot_date else date.today()
    reader = SqliteListingRepository(canonical_db)
    repo = DuckDbSnapshotRepository(tracking_db)
    use_case = RecordDailySnapshots(reader, repo)
    result = asyncio.run(use_case.execute(target))
    typer.echo(
        f"Snapshotted {result.listings_persisted} listings for "
        f"{result.snapshot_date.isoformat()} -> {tracking_db}"
    )


@app.command(name="price-changes")
def price_changes(
    tracking_db: Path = typer.Option(
        ..., "--tracking-db", help="Path to tracking DuckDB."
    ),
    since: str = typer.Option(
        ..., "--since", help="Anchor date (YYYY-MM-DD)."
    ),
    until: str | None = typer.Option(
        None, "--until", help="Tip date (YYYY-MM-DD). Defaults to today."
    ),
    site: str | None = typer.Option(
        None, "--site", help="Restrict to one site (e.g. '591')."
    ),
    only_drops: bool = typer.Option(
        False, "--only-drops", help="Skip price rises."
    ),
    output_format: str = typer.Option(
        "markdown",
        "--format",
        help="Output format: 'markdown' (default) or 'plain'.",
    ),
) -> None:
    """Print listings whose price moved between --since and --until."""
    since_d = _parse_date(since)
    until_d = _parse_date(until) if until else date.today()
    repo = DuckDbSnapshotRepository(tracking_db)
    repo.initialize()
    changes = DetectPriceChanges(repo).execute(
        since=since_d, until=until_d, site=site, only_drops=only_drops
    )
    if output_format == "markdown":
        typer.echo(
            render_price_changes(
                changes,
                since=since_d,
                until=until_d,
                site=site,
                only_drops=only_drops,
            ),
            nl=False,
        )
    elif output_format == "plain":
        if not changes:
            typer.echo("(no price changes in window)")
            return
        typer.echo(
            f"# Price changes {since_d.isoformat()} -> {until_d.isoformat()}"
            + (f" (site={site})" if site else "")
            + (" [drops only]" if only_drops else "")
        )
        typer.echo(
            f"{'listing':<24} {'from':>14} {'to':>14} {'delta':>14} {'pct':>8}"
        )
        for c in changes:
            typer.echo(
                f"{c.listing_id!s:<24} "
                f"{c.from_amount:>14,} {c.to_amount:>14,} "
                f"{c.delta_amount:>+14,} {c.delta_pct:>+7.2f}%"
            )
    else:
        raise typer.BadParameter(
            f"--format must be 'markdown' or 'plain', got: {output_format!r}"
        )


@app.command(name="market-summary")
def market_summary(
    tracking_db: Path = typer.Option(
        ..., "--tracking-db", help="Path to tracking DuckDB."
    ),
    snapshot_date: str | None = typer.Option(
        None, "--date", help="Snapshot date (YYYY-MM-DD). Defaults to today."
    ),
    site: str | None = typer.Option(
        None, "--site", help="Restrict to one site (e.g. '591')."
    ),
    output_format: str = typer.Option(
        "markdown",
        "--format",
        help="Output format: 'markdown' (default) or 'plain'.",
    ),
    chart: Path | None = typer.Option(
        None,
        "--chart",
        help="Optional PNG path to write a unit-price distribution chart.",
    ),
) -> None:
    """Print per-district aggregate stats for one snapshot day."""
    target = _parse_date(snapshot_date) if snapshot_date else date.today()
    repo = DuckDbSnapshotRepository(tracking_db)
    repo.initialize()
    summaries = BuildMarketSummary(repo).execute(target, site=site)
    if output_format == "markdown":
        typer.echo(
            render_market_summary(summaries, snapshot_date=target, site=site),
            nl=False,
        )
    elif output_format == "plain":
        if not summaries:
            typer.echo(f"(no snapshots on {target.isoformat()})")
        else:
            typer.echo(
                f"# Market summary {target.isoformat()}"
                + (f" (site={site})" if site else "")
            )
            typer.echo(
                f"{'district':<12} {'count':>6} {'median_price':>14} "
                f"{'med_unit':>10} {'p25_unit':>10} {'p75_unit':>10}"
            )
            for s in summaries:
                med_p = (
                    f"{int(s.median_price_amount):,}"
                    if s.median_price_amount
                    else "-"
                )
                med_u = (
                    f"{s.median_unit_price_per_ping:.1f}"
                    if s.median_unit_price_per_ping
                    else "-"
                )
                p25 = (
                    f"{s.p25_unit_price_per_ping:.1f}"
                    if s.p25_unit_price_per_ping
                    else "-"
                )
                p75 = (
                    f"{s.p75_unit_price_per_ping:.1f}"
                    if s.p75_unit_price_per_ping
                    else "-"
                )
                typer.echo(
                    f"{s.district:<12} {s.listing_count:>6} {med_p:>14} "
                    f"{med_u:>10} {p25:>10} {p75:>10}"
                )
    else:
        raise typer.BadParameter(
            f"--format must be 'markdown' or 'plain', got: {output_format!r}"
        )
    if chart is not None:
        chart.parent.mkdir(parents=True, exist_ok=True)
        try:
            render_unit_price_distribution_chart(
                summaries, chart, snapshot_date=target
            )
            typer.echo(f"Chart written to {chart}", err=True)
        except ValueError as exc:
            typer.echo(f"Chart skipped: {exc}", err=True)


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise typer.BadParameter(
            f"date must be ISO format (YYYY-MM-DD), got: {raw!r}"
        ) from exc
