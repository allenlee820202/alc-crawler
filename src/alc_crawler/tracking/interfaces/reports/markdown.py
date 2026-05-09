"""Markdown renderers for tracking reports.

Pure-Python string assembly — no third-party templating. Output is
GitHub-flavored markdown tables, which Slack also renders cleanly
(via `mrkdwn` / unfurled links). Designed for piping to a webhook
poster or saving to a file:

    alc-tracker price-changes ... --format markdown > report.md

Each renderer is a pure function: in -> string. No I/O.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from alc_crawler.tracking.domain.district_summary import DistrictSummary
from alc_crawler.tracking.domain.price_change import PriceChange
from alc_crawler.tracking.domain.watch_report import WatchReportEntry


def render_price_changes(
    changes: Sequence[PriceChange],
    *,
    since: date,
    until: date,
    site: str | None = None,
    only_drops: bool = False,
) -> str:
    """Render a price-change list as a markdown table."""
    suffix_bits: list[str] = []
    if site:
        suffix_bits.append(f"site={site}")
    if only_drops:
        suffix_bits.append("drops only")
    suffix = f" ({', '.join(suffix_bits)})" if suffix_bits else ""
    header = f"## Price changes {since.isoformat()} → {until.isoformat()}{suffix}"
    if not changes:
        return f"{header}\n\n_No price changes in window._\n"
    lines = [
        header,
        "",
        "| Listing | From | To | Δ amount | Δ % |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in changes:
        lines.append(
            f"| `{c.listing_id}` "
            f"| {c.from_amount:,} "
            f"| {c.to_amount:,} "
            f"| {c.delta_amount:+,} "
            f"| {c.delta_pct:+.2f}% |"
        )
    return "\n".join(lines) + "\n"


def render_market_summary(
    summaries: Sequence[DistrictSummary],
    *,
    snapshot_date: date,
    site: str | None = None,
) -> str:
    """Render per-district market stats as a markdown table."""
    suffix = f" (site={site})" if site else ""
    header = f"## Market summary {snapshot_date.isoformat()}{suffix}"
    if not summaries:
        return f"{header}\n\n_No snapshots on this date._\n"
    lines = [
        header,
        "",
        "| District | Listings | Median price | Median unit | P25 unit | P75 unit |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        lines.append(
            f"| {s.district} "
            f"| {s.listing_count} "
            f"| {_fmt_price(s.median_price_amount)} "
            f"| {_fmt_unit(s.median_unit_price_per_ping)} "
            f"| {_fmt_unit(s.p25_unit_price_per_ping)} "
            f"| {_fmt_unit(s.p75_unit_price_per_ping)} |"
        )
    return "\n".join(lines) + "\n"


def _fmt_price(value: float | None) -> str:
    return f"{int(value):,}" if value is not None else "—"


def _fmt_unit(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "—"


def render_watch_report(
    entries: Sequence[WatchReportEntry],
    *,
    today: date,
    site: str | None = None,
) -> str:
    """Render the watchlist report as a markdown table.

    One row per watched listing. Columns chosen for at-a-glance
    triage: identity, lifecycle status, days_on_market, price arc
    (first → latest with delta and %), and historical extremes.
    """
    suffix = f" (site={site})" if site else ""
    header = f"## Watch report {today.isoformat()}{suffix}"
    if not entries:
        return f"{header}\n\n_No watched listings._\n"
    lines = [
        header,
        "",
        "| Listing | Nickname | Status | Days | First → Latest | Δ | Min | Max | Snaps |",
        "|---|---|---|---:|---|---:|---:|---:|---:|",
    ]
    for e in entries:
        first_to_latest = (
            f"{e.first_price:,} → {e.latest_price:,}"
            if e.first_price is not None and e.latest_price is not None
            else "—"
        )
        delta_cell = (
            f"{e.total_delta:+,} ({e.total_delta_pct:+.2f}%)"
            if e.total_delta is not None and e.total_delta_pct is not None
            else "—"
        )
        status = e.lifecycle_status.value if e.lifecycle_status else "—"
        lines.append(
            f"| `{e.listing_id}` "
            f"| {e.nickname or ''} "
            f"| {status} "
            f"| {e.days_on_market if e.days_on_market is not None else '—'} "
            f"| {first_to_latest} "
            f"| {delta_cell} "
            f"| {_fmt_price(e.min_price)} "
            f"| {_fmt_price(e.max_price)} "
            f"| {e.snapshot_count} |"
        )
    return "\n".join(lines) + "\n"
