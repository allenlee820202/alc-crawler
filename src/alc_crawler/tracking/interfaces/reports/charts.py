"""Matplotlib chart renderers for tracking reports.

Two charts:
- price_history: line chart of one listing's price over time.
- unit_price_distribution: bar chart of per-district median unit
  price with P25-P75 error bars.

Both write a PNG to a caller-supplied path. The caller is
responsible for ensuring the parent directory exists. We use the
non-interactive 'Agg' backend so charts render headlessly (cron,
CI) without requiring a display.

Returning the Path of the written file (rather than the Figure)
keeps the contract simple and avoids leaking matplotlib types.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless; must come before pyplot import.
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
from matplotlib import font_manager

from alc_crawler.tracking.domain.district_summary import DistrictSummary
from alc_crawler.tracking.domain.snapshot import ListingSnapshot

# Try to pick a CJK-capable font so district names like "大安區" render as
# glyphs instead of tofu boxes. We probe common platform fonts; if none
# are installed matplotlib falls back to its default and emits a warning.
_CJK_CANDIDATES = (
    "PingFang TC",
    "PingFang SC",
    "Heiti TC",
    "Hiragino Sans GB",
    "Noto Sans CJK TC",
    "Noto Sans CJK SC",
    "Microsoft JhengHei",
    "Microsoft YaHei",
    "Arial Unicode MS",
)
_available = {f.name for f in font_manager.fontManager.ttflist}
for _candidate in _CJK_CANDIDATES:
    if _candidate in _available:
        plt.rcParams["font.family"] = [_candidate, "DejaVu Sans"]
        break


def render_price_history_chart(
    snapshots: Sequence[ListingSnapshot],
    output: Path,
    *,
    title: str | None = None,
) -> Path:
    """Render one listing's price-over-time as a PNG line chart.

    `snapshots` should be ordered oldest-first; this function does
    not sort. Raises ValueError on empty input (no chart to make).
    """
    if not snapshots:
        raise ValueError("render_price_history_chart: snapshots is empty")
    dates = [mdates.date2num(s.snapshot_date) for s in snapshots]  # type: ignore[no-untyped-call]
    prices = [s.price_amount for s in snapshots]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, prices, marker="o", linewidth=1.5)
    ax.xaxis_date()
    ax.set_xlabel("Snapshot date")
    ax.set_ylabel("Price (TWD)")
    ax.set_title(title or f"Price history for {snapshots[0].listing_id}")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.ticklabel_format(axis="y", style="plain")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=120)
    plt.close(fig)
    return output


def render_unit_price_distribution_chart(
    summaries: Sequence[DistrictSummary],
    output: Path,
    *,
    snapshot_date: date,
) -> Path:
    """Render per-district median unit price with P25/P75 error bars.

    Districts without unit-price data are dropped (no median to plot).
    Raises ValueError if no district has unit-price data.
    """
    plotable = [
        s for s in summaries if s.median_unit_price_per_ping is not None
    ]
    if not plotable:
        raise ValueError(
            "render_unit_price_distribution_chart: no districts have unit-price data"
        )
    districts = [s.district for s in plotable]
    medians: list[float] = [
        s.median_unit_price_per_ping
        for s in plotable
        if s.median_unit_price_per_ping is not None
    ]
    # Error bars: distance from median to p25 (lower) and p75 (upper).
    # If a quartile is None (very sparse district), fall back to 0.
    lower = [
        (s.median_unit_price_per_ping or 0.0) - (s.p25_unit_price_per_ping or 0.0)
        for s in plotable
    ]
    upper = [
        (s.p75_unit_price_per_ping or 0.0) - (s.median_unit_price_per_ping or 0.0)
        for s in plotable
    ]
    fig, ax = plt.subplots(figsize=(max(6, len(districts) * 0.7), 4.5))
    bars = ax.bar(districts, medians, yerr=[lower, upper], capsize=4, alpha=0.85)
    ax.set_xlabel("District")
    ax.set_ylabel("Unit price per ping (TWD/ping, in 萬)")
    ax.set_title(
        f"Unit price by district — {snapshot_date.isoformat()}"
    )
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    for bar, count in zip(bars, [s.listing_count for s in plotable], strict=True):
        ax.annotate(
            f"n={count}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=120)
    plt.close(fig)
    return output
