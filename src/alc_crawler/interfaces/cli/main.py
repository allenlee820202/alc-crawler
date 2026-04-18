"""Typer CLI entry point for alc-crawler."""
from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from alc_crawler.adapters.sites.site_591.crawl_service import Site591CrawlService
from alc_crawler.adapters.sites.site_591.search_urls import search_urls_for_region
from alc_crawler.infrastructure.http.httpx_fetcher import HttpxFetcher
from alc_crawler.infrastructure.persistence.sqlite.listing_repository import (
    SqliteListingRepository,
)

app = typer.Typer(
    help="Self-hosted crawler for Taiwan house-selling sites.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """alc-crawler: self-hosted crawler for Taiwan house-selling sites."""


@app.command(name="crawl")
def crawl(
    site: str = typer.Argument(..., help="Site to crawl. Currently only '591' is supported."),
    region: str = typer.Option(..., "--region", help="Region key, e.g. 'taipei'."),
    page: int = typer.Option(1, "--page", help="Search page number (1-indexed)."),
    db: Path = typer.Option(Path("data/listings.sqlite"), "--db", help="SQLite DB path."),
    insecure: bool = typer.Option(
        False,
        "--insecure",
        help=(
            "Disable TLS verification. Workaround for sites whose CA chain is "
            "rejected by your local OpenSSL (e.g. 591's TWCA intermediate is "
            "missing the RFC 5280 Subject Key Identifier extension)."
        ),
    ),
) -> None:
    """Crawl one search page and persist results to SQLite."""
    if site != "591":
        raise typer.BadParameter(f"Unsupported site '{site}'. Currently only '591'.")

    urls = search_urls_for_region(region, page=page)
    db.parent.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        repo = SqliteListingRepository(db)
        await repo.initialize()
        service = Site591CrawlService(
            fetcher=HttpxFetcher(verify=not insecure),
            repo=repo,
        )
        result = await service.crawl(urls)
        typer.echo(f"fetched={result.fetched} persisted={result.persisted}")

    asyncio.run(_run())


if __name__ == "__main__":
    app()
