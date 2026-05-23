# AGENTS.md

## Project

Python 3.11+ CLI crawler for Taiwan house-selling sites (currently 591).
Managed with `uv`; src-layout under `src/alc_crawler/`.

## Commands

```bash
uv sync                        # install deps (creates .venv)
uv run pytest                  # all tests (unit + integration)
uv run pytest tests/unit       # unit only (~fast, no I/O)
uv run pytest -m integration   # integration only
uv run pytest tests/unit/test_site_591_api_parser.py -k test_parse_area  # single test
uv run ruff check .            # lint
uv run ruff format --check .   # format check
uv run mypy src                # typecheck (strict mode)
```

All three gates must pass before committing: `ruff check . && mypy src && pytest`.

## Architecture (Clean Architecture / DDD)

```
domain/           Pure value objects + Listing aggregate. No I/O, no imports outside domain.
application/      Use cases + port interfaces (HttpFetcher, ListingRepository, SearchPageParser).
infrastructure/   Port implementations: httpx fetcher, playwright fetcher, SQLite repo.
adapters/sites/   Per-site anti-corruption layer (591 parser, URL builder, crawl service).
interfaces/cli/   Typer CLI. Entry point: main:app.
```

- Ports are abstract classes in `application/ports/`. New infrastructure goes behind a port.
- Site-specific code lives only under `adapters/sites/<site>/`.
- Domain objects are immutable (`frozen=True, slots=True` dataclasses or Pydantic models).

## Testing patterns

- Unit tests use in-memory fakes that implement the port interfaces (no mocking library).
- Integration tests mock the network at the httpx layer with `respx`, not at the port level.
- JSON fixtures live under `tests/fixtures/site_591/`.
- `pytest-asyncio` with `asyncio_mode = "auto"` -- async tests need no decorator.
- `pytest.mark.integration` marker exists but is **not** used to exclude by default; all tests run together.
- Playwright test is auto-skipped unless browsers are installed (`uv run playwright install chromium`).

## Style / linting

- Ruff: line-length 100, target py311, rules `E F I N UP B SIM RUF`.
- `B008` (function call in default arg) is suppressed for `interfaces/cli/*.py` because Typer requires it.
- mypy: `strict = true`. All public signatures need type annotations.

## Gotchas

- **591 requires `--insecure`** at crawl time (TLS cert issue with TWCA intermediate).
- **591 BFF ignores price/age query params** -- always crawl broadly, filter at `query` time.
- The `query` command builds raw SQL; `order_by` is validated against an allowlist but is interpolated (not parameterized). Keep that pattern if extending.
- `hatchling` builds wheels from `src/alc_crawler` (configured in `pyproject.toml`). No separate build step needed for dev.
- SQLite files go under `data/` which is gitignored. Tests use `tmp_path`.
