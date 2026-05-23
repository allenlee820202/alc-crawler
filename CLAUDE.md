# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python 3.11+ CLI crawler for Taiwan house-selling sites (currently 591.com.tw).
Managed with `uv`; src-layout under `src/alc_crawler/`.

## Commands

```bash
uv sync                        # install deps (creates .venv)
uv run pytest                  # all tests (unit + integration)
uv run pytest tests/unit       # unit only (fast, no I/O)
uv run pytest tests/unit/test_site_591_api_parser.py -k test_parse_area  # single test
uv run ruff check .            # lint
uv run ruff format --check .   # format check
uv run mypy src                # typecheck (strict mode)
```

Quality gate (must pass before commit): `ruff check . && mypy src && pytest`

## Architecture (Clean Architecture / DDD)

```
src/alc_crawler/
├── domain/           Pure value objects + CanonicalListing aggregate. No I/O, no external imports.
├── application/      Use cases + port interfaces (HttpFetcher, ListingRepository, SearchPageParser).
├── infrastructure/   Port implementations: httpx fetcher, playwright fetcher, SQLite repo.
├── adapters/sites/   Per-site anti-corruption layer (591 parser, URL builder, crawl service).
├── interfaces/cli/   Typer CLI entry point (alc-crawler).
└── tracking/         Time-series analytics submodule (alc-tracker) — own domain/application/infra/cli.
```

Key rules:
- Ports are abstract classes in `application/ports/`. New infrastructure goes behind a port.
- Site-specific code lives only under `adapters/sites/<site>/`.
- Domain objects are immutable (`frozen=True, slots=True` dataclasses or Pydantic models).
- Storage separation: canonical SQLite (latest crawl state) vs tracking DuckDB (append-only time-series). Never write to canonical from tracking.

## Two CLIs

- `alc-crawler` → `src/alc_crawler/interfaces/cli/main.py` — crawl, query, regions
- `alc-tracker` → `src/alc_crawler/tracking/interfaces/cli/main.py` — snapshot, price-changes, market-summary, watch

## Testing

- Unit tests use in-memory fakes implementing port interfaces (no mocking library).
- Integration tests mock network at httpx layer with `respx`, not at port level.
- JSON fixtures: `tests/fixtures/site_591/`.
- `pytest-asyncio` with `asyncio_mode = "auto"` — async tests need no decorator.
- Playwright test auto-skipped unless browsers installed.

## Style

- Ruff: line-length 100, target py311, rules `E F I N UP B SIM RUF`.
- `B008` suppressed in `interfaces/cli/*.py` (Typer requires function calls in default args).
- mypy: `strict = true`. All public signatures need type annotations.

## Gotchas

- **591 requires `--insecure`** at crawl time (TLS cert issue with TWCA intermediate).
- **591 BFF ignores price/age query params** — always crawl broadly, filter at `query` time.
- The `query` command's `order_by` is validated against an allowlist but interpolated (not parameterized). Keep that pattern if extending.
- SQLite/DuckDB files go under `data/` (gitignored). Tests use `tmp_path`.
- `hatchling` builds wheels from `src/alc_crawler`. No separate build step needed for dev.
