# alc-crawler

Self-hosted crawler for Taiwan house-selling sites. Currently supports **591**
(`Yungching` planned). Fetches search results from 591's BFF JSON API,
persists them to SQLite, and lets you query the local DB with practical
filters (price, age, rooms, area, district, keyword, etc.).

Built with **Clean Architecture** + **DDD** so the storage backend, fetcher,
and site-specific parsers can be swapped without touching the core domain.

---

## Install

```bash
uv sync
uv run alc-crawler --help
```

Requires Python 3.13 + [`uv`](https://github.com/astral-sh/uv).

Discover supported region/section/shape ids:

```bash
uv run alc-crawler regions
```

---

## Two-step workflow

1. **`crawl`** — pull search results from 591 and write them to a SQLite file.
2. **`query`** — filter and sort the local SQLite file.

You almost always want one DB file per crawl topic (e.g. `data/daan.sqlite`,
`data/xinyi.sqlite`). The query CLI never touches the network.

### Example: find houses near 大安國中, ≤4000萬, ≤32年, 2-3房, ≥30坪

```bash
# 1) Crawl 內湖區 公寓 + 電梯大樓 (10 pages ≈ 300 listings).
#    --insecure is currently REQUIRED for 591 (TLS quirk, see below).
uv run alc-crawler crawl 591 \
    --region taipei --section 10 --shape 1,2 \
    --max-pages 10 --insecure \
    --db data/daan.sqlite
# -> pages=10 fetched=310 persisted=310

# 2) Query with all the user's hard constraints.
uv run alc-crawler query --db data/daan.sqlite \
    --section-name 內湖區 \
    --shape-name 公寓 --shape-name 電梯大樓 \
    --max-price-wan 4000 --max-age 25 \
    --min-rooms 2 --max-rooms 3 --min-area 25 \
    --order-by price_amount

# 3) Narrow further by school name appearing in the agent's title.
uv run alc-crawler query --db data/daan.sqlite \
    --section-name 內湖區 --max-price-wan 4000 \
    --title-contains 大安
```

---

## `crawl` reference

```
alc-crawler crawl SITE --region <key> [--section ID] [--shape CSV]
                       [--page N] [--max-pages N]
                       [--db PATH] [--insecure]
```

| Flag | Required | Notes |
|---|---|---|
| `SITE` (positional) | yes | Currently only `591`. |
| `--region` | yes | One of: `taipei`, `new-taipei`, `taoyuan`, `taichung`, `kaohsiung`. |
| `--section` | no | District id, see table below. Omit = whole region. |
| `--shape` | no | CSV of shape ids, see table below. Omit = all shapes. |
| `--page` | no | Starting page (1-indexed, 30 listings/page). Default `1`. |
| `--max-pages` | no | How many consecutive pages to fetch. Default `1`. Stops early when a page returns < 30 items. |
| `--db` | no | SQLite path (created if missing). Default `data/listings.sqlite`. |
| `--insecure` | no | Disable TLS verification. **Required for 591** today (see Quirks). |

**Output line:** `pages=<N> fetched=<M> persisted=<K>` — `persisted` may be
less than `fetched` only on parse errors.

### Section ids (台北市, region=`taipei`)

| id | 區 | id | 區 |
|---:|---|---:|---|
| 1 | 中正 | 8 | 士林 |
| 2 | 大同 | 9 | 北投 |
| 4 | 松山 | 10 | 內湖 |
| 5 | 大安 | 11 | 南港 |
| 6 | 萬華 | 12 | 文山 |
| 7 | 信義 | | |

### Section ids (新北市, region=`new-taipei`)

| id | 區 | id | 區 | id | 區 |
|---:|---|---:|---|---:|---|
| 20 | 萬里 | 30 | 瑞芳 | 40 | 三峽 |
| 21 | 金山 | 31 | 平溪 | 41 | 樹林 |
| 26 | 板橋 | 32 | 雙溪 | 42 | 鶯歌 |
| 27 | 汐止 | 33 | 貢寮 | 43 | 三重 |
| 28 | 深坑 | 34 | 新店 | 44 | 新莊 |
| 29 | 石碇 | 35 | 坪林 | 45 | 泰山 |
|    |     | 36 | 烏來 | 46 | 林口 |
|    |     | 37 | 永和 | 47 | 蘆洲 |
|    |     | 38 | 中和 | 48 | 五股 |
|    |     | 39 | 土城 | 49 | 八里 |
|    |     |    |     | 50 | 淡水 |

> 三芝 / 石門 may exist as ids but currently return zero listings.

For other cities (`taoyuan`, `taichung`, `kaohsiung`), section ids are not
yet probed — inspect 591's UI or run a probe.

Run `alc-crawler regions` for the same tables on the CLI.

### Shape ids

| id | 類型 |
|---:|---|
| 1 | 公寓 |
| 2 | 電梯大樓 |
| 3 | 透天厝 |
| 4 | 別墅 |
| 8 | 店面 |

### What does NOT work as a crawl-time filter

591's BFF accepts `price` and `houseage` query params but returns out-of-range
listings anyway, so this CLI does not surface them. **Apply price and age
filters at `query` time** — the data is already on disk.

---

## `query` reference

```
alc-crawler query [--db PATH] [--site KEY]
                  [--section-name 名 ...] [--shape-name 名 ...]
                  [--max-price-wan N] [--min-price-wan N]
                  [--max-age N]
                  [--min-area X.X]
                  [--min-rooms N] [--max-rooms N]
                  [--address-contains S] [--community-contains S]
                  [--title-contains S]
                  [--order-by COL] [--desc] [--limit N]
```

All filters AND together. Repeating `--section-name` / `--shape-name` ORs
within that group.

| Flag | Type | Effect |
|---|---|---|
| `--db` | path | SQLite file produced by `crawl`. |
| `--site` | str | Default `591`; tags written by the crawler. |
| `--section-name` | repeatable str | District name (`內湖區`, `信義區`, ...). |
| `--shape-name` | repeatable str | Shape label (`公寓`, `電梯大樓`, `透天厝`, ...). |
| `--max-price-wan` / `--min-price-wan` | int (萬, 1萬=10,000TWD) | Total price bounds. |
| `--max-age` | int | 屋齡 ≤ N years. |
| `--min-area` | float | 總坪數 ≥ X 坪. |
| `--min-rooms` / `--max-rooms` | int | Number of 房 parsed from `room_layout`. Excludes rows whose layout is non-standard (e.g. `開放式格局`). |
| `--address-contains` | str | Substring on raw address. |
| `--community-contains` | str | Substring on community name. |
| `--title-contains` | str | Substring on agent's listing title. Useful for school keywords (e.g. `大安`, `大安`). |
| `--order-by` | enum | `price_amount` (default), `unit_price_per_ping`, `area_ping`, `house_age_years`, `posted_at`. |
| `--desc` | flag | Reverse sort order. |
| `--limit` | int | Max rows printed. Default `50`. |

### Output format

```
matches: <count>
[<external_id>] <price>萬 <area>坪 <unit>萬/坪 <age>年 <shape> | <district> <addr> | <community> | <layout> <floor> | posted=<YYYY-MM-DD> | <title>
           <url>
```

`-` means the field is missing. Re-running the same `crawl` updates rows in
place (PK is `(site, external_id)`).

---

## Direct SQLite access

The DB is plain SQLite — query directly when the CLI is too restrictive:

```bash
sqlite3 data/daan.sqlite \
  "SELECT external_id, price_amount/10000, room_layout, community_name, url
   FROM listings
   WHERE address_district='內湖區'
     AND price_amount <= 40000000
     AND house_age_years <= 32
     AND room_layout GLOB '[2-3]房*'
   ORDER BY price_amount LIMIT 20;"
```

### Schema

Table `listings`, primary key `(site, external_id)`:

| Column | Type | Notes |
|---|---|---|
| `site` | TEXT | `591` |
| `external_id` | TEXT | 591 listing id |
| `title`, `url` | TEXT | |
| `price_amount` | INT | TWD (1萬=10,000) |
| `price_currency` | TEXT | `TWD` |
| `address_city`, `address_district`, `address_raw` | TEXT | |
| `attributes_json` | TEXT | JSON. Includes `shape`. |
| `area_ping`, `main_area_ping`, `unit_price_per_ping` | REAL | |
| `house_age_years` | INT | |
| `room_layout` | TEXT | e.g. `3房2廳2衛` |
| `floor` | TEXT | e.g. `5F/12F` |
| `community_name` | TEXT | |
| `posted_at` | TEXT | ISO 8601 |
| `view_count` | INT | |
| `observed_at` | TEXT | ISO 8601, when crawled |

---

## Architecture

```
src/alc_crawler/
├── domain/          # Listing aggregate + value objects (pure, no I/O)
├── application/     # Use cases + ports (Fetcher, ListingRepository)
├── infrastructure/  # Adapters: SQLite repo, httpx fetcher
├── adapters/sites/  # Per-site parsers + URL builders (anti-corruption layer)
└── interfaces/cli/  # Typer CLI
```

Storage is SQLite via the `ListingRepository` port; swap to PostgreSQL/Redis
without touching application or domain code.

---

## Quirks

- **591 TLS:** 591's TWCA intermediate cert is missing the RFC 5280 Subject
  Key Identifier extension and is rejected by recent OpenSSL. Pass
  `--insecure` to `crawl` to disable verification. (Curl/browsers happen to
  accept it; Python's `ssl` does not.)
- **591 detail pages:** Price/area on the per-listing detail HTML are
  client-side obfuscated (`<web-component-image>` / `<web-component-obfuscate>`
  rendered via SeaJS). The crawler uses 591's BFF list endpoint instead — it
  returns area, unit price, age, room layout, floor, community, post time,
  view count, etc. for every result.
- **Filter at query time, not crawl time:** the BFF ignores `price` and
  `houseage` constraints; crawl broadly, filter locally.

---

## Development

```bash
uv run pytest                  # unit + integration
uv run ruff check .            # lint
uv run mypy src                # types
```

Tests follow TDD; commits land per milestone with all three checks green.
