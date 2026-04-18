"""Typer CLI entry point for alc-crawler."""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import typer

from alc_crawler.adapters.sites.site_591.crawl_service import Site591CrawlService
from alc_crawler.adapters.sites.site_591.search_urls import (
    REGION_IDS,
    SHAPE_IDS,
    TAIPEI_SECTION_IDS,
    search_urls_for_region,
)
from alc_crawler.infrastructure.http.httpx_fetcher import HttpxFetcher
from alc_crawler.infrastructure.persistence.sqlite.listing_repository import (
    SqliteListingRepository,
)

app = typer.Typer(
    help=(
        "Self-hosted crawler for Taiwan house-selling sites.\n\n"
        "Two-step workflow:\n"
        "  1) `alc-crawler crawl 591 --region taipei --section 10 --shape 1,2 "
        "--max-pages 10 --insecure --db data/daan.sqlite`\n"
        "  2) `alc-crawler query --db data/daan.sqlite --section-name 內湖區 "
        "--max-price-wan 4000 --max-age 25 --min-rooms 2 --max-rooms 3`\n\n"
        "Run `alc-crawler crawl --help` and `alc-crawler query --help` for the "
        "full ID tables and filter list."
        "\n\nRun `alc-crawler regions` to introspect supported region/section/shape ids."
    ),
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """alc-crawler: self-hosted crawler for Taiwan house-selling sites."""


def _parse_csv_ints(raw: str | None, *, flag: str) -> list[int] | None:
    if raw is None or not raw.strip():
        return None
    try:
        return [int(piece) for piece in raw.split(",") if piece.strip()]
    except ValueError as exc:
        raise typer.BadParameter(f"{flag} must be a comma-separated list of ints") from exc


@app.command(name="crawl")
def crawl(
    site: str = typer.Argument(..., help="Site to crawl. Currently only '591' is supported."),
    region: str = typer.Option(
        ...,
        "--region",
        help=(
            "Region key. Supported: taipei, new-taipei, taoyuan, taichung, "
            "kaohsiung."
        ),
    ),
    page: int = typer.Option(
        1,
        "--page",
        help="Starting page number (1-indexed; 30 listings/page).",
    ),
    max_pages: int = typer.Option(
        1,
        "--max-pages",
        min=1,
        help="Crawl up to this many pages (loop stops early if a page is short).",
    ),
    section: int | None = typer.Option(
        None,
        "--section",
        help=(
            "591 section/district id. 台北市: 1=中正 2=大同 4=松山 5=大安 "
            "6=萬華 7=信義 8=士林 9=北投 10=內湖 11=南港 12=文山. "
            "Other cities have their own ids; check 591's UI."
        ),
    ),
    shape: str | None = typer.Option(
        None,
        "--shape",
        help=(
            "Comma-separated 591 shape ids. 1=公寓 2=電梯大樓 3=透天厝 "
            "4=別墅 8=店面. Example: --shape 1,2 (公寓 OR 電梯大樓)."
        ),
    ),
    db: Path = typer.Option(Path("data/listings.sqlite"), "--db", help="SQLite DB path."),
    insecure: bool = typer.Option(
        False,
        "--insecure",
        help=(
            "Disable TLS verification. Currently REQUIRED for 591 because "
            "their TWCA intermediate cert is missing the RFC 5280 Subject Key "
            "Identifier extension and is rejected by recent OpenSSL."
        ),
    ),
) -> None:
    """Crawl 591 search pages and persist listings to a SQLite DB.

    Examples:

      # 內湖區, 公寓+電梯大樓, first 10 pages -> ~300 listings
      alc-crawler crawl 591 --region taipei --section 10 --shape 1,2 \\
          --max-pages 10 --insecure --db data/daan.sqlite

      # Whole 台北市 (no --section), only 透天厝, deeper crawl
      alc-crawler crawl 591 --region taipei --shape 3 \\
          --max-pages 30 --insecure --db data/taipei-houses.sqlite

    Output line format:  pages=<N> fetched=<M> persisted=<K>
    """
    if site != "591":
        raise typer.BadParameter(f"Unsupported site '{site}'. Currently only '591'.")

    shape_ids = _parse_csv_ints(shape, flag="--shape")

    def urls_for(p: int) -> object:
        return search_urls_for_region(
            region,
            page=page + p - 1,
            section_id=section,
            shape_ids=shape_ids,
        )

    db.parent.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        repo = SqliteListingRepository(db)
        await repo.initialize()
        service = Site591CrawlService(
            fetcher=HttpxFetcher(verify=not insecure),
            repo=repo,
        )
        result = await service.crawl_pages(urls_for, max_pages=max_pages)  # type: ignore[arg-type]
        typer.echo(
            f"pages={result.pages} fetched={result.fetched} persisted={result.persisted}"
        )

    asyncio.run(_run())


@app.command(name="query")
def query(
    db: Path = typer.Option(Path("data/listings.sqlite"), "--db", help="SQLite DB path."),
    site: str = typer.Option("591", "--site", help="Filter by site key."),
    section_name: list[str] = typer.Option(
        [],
        "--section-name",
        help="District name (e.g. 內湖區). Repeat to match any of several.",
    ),
    shape_name: list[str] = typer.Option(
        [],
        "--shape-name",
        help="Shape label as stored in attributes (e.g. 公寓, 電梯大樓). Repeat for OR.",
    ),
    max_price_wan: int | None = typer.Option(
        None,
        "--max-price-wan",
        help="Maximum total price in 萬 (1萬 = 10,000 TWD).",
    ),
    min_price_wan: int | None = typer.Option(
        None, "--min-price-wan", help="Minimum total price in 萬."
    ),
    max_age: int | None = typer.Option(
        None, "--max-age", help="Maximum 屋齡 in years."
    ),
    min_area: float | None = typer.Option(
        None, "--min-area", help="Minimum total area in 坪."
    ),
    min_rooms: int | None = typer.Option(
        None,
        "--min-rooms",
        help="Minimum number of 房 (parsed from room_layout, e.g. '3房2廳').",
    ),
    max_rooms: int | None = typer.Option(
        None,
        "--max-rooms",
        help="Maximum number of 房 (parsed from room_layout).",
    ),
    address_contains: str | None = typer.Option(
        None,
        "--address-contains",
        help="Substring filter on address_raw (e.g. street name, lane).",
    ),
    community_contains: str | None = typer.Option(
        None,
        "--community-contains",
        help="Substring filter on community_name.",
    ),
    title_contains: str | None = typer.Option(
        None,
        "--title-contains",
        help="Substring filter on listing title.",
    ),
    order_by: str = typer.Option(
        "price_amount",
        "--order-by",
        help=(
            "Sort column. One of: price_amount, unit_price_per_ping, "
            "area_ping, house_age_years, posted_at."
        ),
    ),
    desc: bool = typer.Option(False, "--desc", help="Sort descending."),
    limit: int = typer.Option(50, "--limit", help="Max rows to print."),
) -> None:
    """Query persisted listings with practical filters.

    All filters AND together. `--section-name` and `--shape-name` accept
    repeats which OR within their group. Numeric ranges use 萬 for price
    (1萬 = 10,000 TWD) and 坪 for area.

    Output: one listing per pair of lines. Header line is
    "matches: N", followed by:

      [<external_id>] <price>萬 <area>坪 <unit>萬/坪 <age>年 <shape> | \\
      <district> <addr> | <community> | <room_layout> <floor> | \\
      posted=<YYYY-MM-DD> | <title>
                 <url>

    Examples:

      # Full constraint set: 內湖區 公寓/電梯大樓, ≤4000萬, ≤32年, 2-3房, ≥30坪
      alc-crawler query --db data/daan.sqlite \\
          --section-name 內湖區 \\
          --shape-name 公寓 --shape-name 電梯大樓 \\
          --max-price-wan 4000 --max-age 25 \\
          --min-rooms 2 --max-rooms 3 --min-area 25

      # Narrow by school keyword in agent's title
      alc-crawler query --db data/daan.sqlite \\
          --title-contains 大安 --order-by price_amount

      # Sort by best $/坪 within budget, take top 10
      alc-crawler query --db data/daan.sqlite \\
          --max-price-wan 4000 --order-by unit_price_per_ping --limit 10
    """
    allowed_sort = {
        "price_amount",
        "unit_price_per_ping",
        "area_ping",
        "posted_at",
        "house_age_years",
    }
    if order_by not in allowed_sort:
        raise typer.BadParameter(f"--order-by must be one of {sorted(allowed_sort)}")
    if not db.exists():
        raise typer.BadParameter(f"DB not found: {db}. Run `alc-crawler crawl` first.")

    where: list[str] = ["site = ?"]
    params: list[object] = [site]

    if section_name:
        placeholders = ",".join("?" for _ in section_name)
        where.append(f"address_district IN ({placeholders})")
        params.extend(section_name)

    if shape_name:
        # `shape` is stored under attributes_json (e.g. {"shape": "公寓"}).
        # SQLite has no JSON1 dependency guarantee, so substring-match the JSON.
        clauses = []
        for sn in shape_name:
            clauses.append("attributes_json LIKE ?")
            params.append(f'%"shape": "{sn}"%')
        where.append("(" + " OR ".join(clauses) + ")")

    if max_price_wan is not None:
        where.append("price_amount <= ?")
        params.append(max_price_wan * 10_000)
    if min_price_wan is not None:
        where.append("price_amount >= ?")
        params.append(min_price_wan * 10_000)
    if max_age is not None:
        where.append("(house_age_years IS NOT NULL AND house_age_years <= ?)")
        params.append(max_age)
    if min_area is not None:
        where.append("(area_ping IS NOT NULL AND area_ping >= ?)")
        params.append(min_area)
    if min_rooms is not None or max_rooms is not None:
        # room_layout looks like "3房2廳2衛"; require single-digit 房 prefix.
        where.append(
            "(room_layout IS NOT NULL AND room_layout GLOB '[0-9]房*')"
        )
        if min_rooms is not None:
            where.append("CAST(SUBSTR(room_layout, 1, 1) AS INTEGER) >= ?")
            params.append(min_rooms)
        if max_rooms is not None:
            where.append("CAST(SUBSTR(room_layout, 1, 1) AS INTEGER) <= ?")
            params.append(max_rooms)
    if address_contains:
        where.append("address_raw LIKE ?")
        params.append(f"%{address_contains}%")
    if community_contains:
        where.append("(community_name IS NOT NULL AND community_name LIKE ?)")
        params.append(f"%{community_contains}%")
    if title_contains:
        where.append("title LIKE ?")
        params.append(f"%{title_contains}%")

    sql = (
        "SELECT external_id, title, price_amount, area_ping, unit_price_per_ping, "
        "house_age_years, room_layout, floor, community_name, address_raw, "
        "address_district, attributes_json, url, posted_at "
        "FROM listings WHERE " + " AND ".join(where) + f" ORDER BY {order_by} "
        f"{'DESC' if desc else 'ASC'} LIMIT ?"
    )
    params.append(limit)

    with sqlite3.connect(db) as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        typer.echo("(no matches)")
        return

    typer.echo(f"matches: {len(rows)}")
    for row in rows:
        (
            ext_id,
            title,
            price_amount,
            area_ping,
            unit_price,
            age,
            room,
            floor,
            community,
            addr,
            district,
            attrs_json,
            url,
            posted_at,
        ) = row
        price_wan = price_amount // 10_000
        shape = ""
        if attrs_json and '"shape":' in attrs_json:
            # Cheap parse without importing json for hot path.
            import json as _json

            shape = _json.loads(attrs_json).get("shape", "")
        area_str = f"{area_ping:.1f}坪" if area_ping is not None else "-"
        unit_str = f"{unit_price:.1f}萬/坪" if unit_price is not None else "-"
        age_str = f"{age}年" if age is not None else "-"
        community_str = community or ""
        posted_str = posted_at[:10] if posted_at else "-"
        typer.echo(
            f"[{ext_id}] {price_wan:>5}萬 {area_str:>8} {unit_str:>10} "
            f"{age_str:>4} {shape:<5} | {district} {addr or ''} | "
            f"{community_str} | {room or ''} {floor or ''} | posted={posted_str} | {title}"
        )
        typer.echo(f"           {url}")


@app.command(name="regions")
def regions() -> None:
    """List 591 region keys, 台北市 section ids, and shape ids.

    Use this to discover the values you can pass to `crawl --region`,
    `crawl --section`, and `crawl --shape`.
    """
    typer.echo("Regions (--region):")
    typer.echo(f"  {'key':<12}  region_id")
    for key, rid in sorted(REGION_IDS.items(), key=lambda kv: kv[1]):
        typer.echo(f"  {key:<12}  {rid}")
    typer.echo("")
    typer.echo("Section ids for 台北市 (--section, when --region taipei):")
    typer.echo(f"  {'id':>3}  區")
    for sid, name in sorted(TAIPEI_SECTION_IDS.items()):
        typer.echo(f"  {sid:>3}  {name}")
    typer.echo("  (Other regions have their own section id spaces; inspect 591's UI.)")
    typer.echo("")
    typer.echo("Shape ids (--shape, comma-separated for OR):")
    typer.echo(f"  {'id':>3}  類型")
    for shid, label in sorted(SHAPE_IDS.items()):
        typer.echo(f"  {shid:>3}  {label}")


if __name__ == "__main__":
    app()
