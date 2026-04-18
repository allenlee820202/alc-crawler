# alc-crawler

Self-hosted crawler for Taiwan house-selling sites (`591`, `Yungching`).

Built with **Clean Architecture** + **DDD** so the storage backend, fetcher,
and site-specific parsers can be swapped without touching the core domain.

## Quick start

```bash
uv sync
uv run pytest
uv run alc-crawler --help
```

## Architecture

```
src/alc_crawler/
├── domain/          # Entities + Value Objects (pure, no I/O)
├── application/     # Use cases + Ports (interfaces)
├── infrastructure/  # Adapters: SQLite, httpx, Playwright
├── adapters/sites/  # Per-site parsers (anti-corruption layer)
└── interfaces/cli/  # Typer CLI
```

Storage starts with SQLite; the `ListingRepository` port can be re-implemented
with PostgreSQL/Redis later without changing application or domain code.
