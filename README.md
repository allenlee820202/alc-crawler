# alc-crawler

Self-hosted crawler for Taiwan house-selling sites. Supports **591**,
**Yungching (永慶房屋)**, and **hbhousing (住商不動產)**. Fetches search results,
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

1. **`crawl`** — pull search results from a site and write them to a SQLite file.
2. **`query`** — filter and sort the local SQLite file.

You almost always want one DB file per crawl topic (e.g. `data/daan.sqlite`,
`data/xinyi.sqlite`). The query CLI never touches the network.

### Example: 591 — find houses near 大安國中, ≤4000萬, ≤25年, 2-3房, ≥25坪

```bash
# 1) Crawl 大安區 公寓 + 電梯大樓 (10 pages ≈ 300 listings).
#    --insecure is currently REQUIRED for 591 (TLS quirk, see below).
uv run alc-crawler crawl 591 \
    --region taipei --section 5 --shape 1,2 \
    --max-pages 10 --insecure \
    --db data/daan.sqlite
# -> pages=10 fetched=310 persisted=310

# 2) Query with hard constraints.
uv run alc-crawler query --db data/daan.sqlite \
    --section-name 大安區 \
    --shape-name 公寓 --shape-name 電梯大樓 \
    --max-price-wan 4000 --max-age 25 \
    --min-rooms 2 --max-rooms 3 --min-area 25 \
    --order-by price_amount

# 3) Narrow further by school name appearing in the agent's title.
uv run alc-crawler query --db data/daan.sqlite \
    --section-name 大安區 --max-price-wan 4000 \
    --title-contains 大安
```

### Example: Yungching — 內湖區, ≤3500萬, 2-3房, ≤25年

```bash
# Yungching respects ALL filter params server-side (unlike 591).
# No --insecure needed.
uv run alc-crawler crawl yungching \
    --region taipei --district 內湖區 \
    --max-price-wan 3500 --min-rooms 2 --max-rooms 3 --max-age 25 \
    --max-pages 5 \
    --db data/neihu-yc.sqlite
# -> pages=5 fetched=150 persisted=150
```

### Example: hbhousing — 內湖區, ≤3500萬, 2-3房, 大樓 (elevator)

```bash
# hbhousing uses district names (not numeric ids) and --style for building type.
# 10 listings per page. No --insecure needed.
uv run alc-crawler crawl hbhousing \
    --region taipei --district 內湖區 \
    --max-price-wan 3500 --min-rooms 2 --max-rooms 3 \
    --style 大樓 \
    --max-pages 10 \
    --db data/neihu-hb.sqlite
# -> pages=10 fetched=100 persisted=100
```

---

## `crawl` reference

```
alc-crawler crawl SITE --region <key> [OPTIONS]
```

| Flag | Sites | Required | Notes |
|---|---|---|---|
| `SITE` (positional) | all | yes | `591`, `yungching`, or `hbhousing`. |
| `--region` | all | yes | `taipei`, `new-taipei`, `taoyuan`, `taichung`, `kaohsiung`. |
| `--section` | 591 | no | District id (numeric). Omit = whole region. |
| `--shape` | 591 | no | CSV of shape ids (1=公寓, 2=電梯大樓, etc.). |
| `--district` | yungching, hbhousing | no | District name in Chinese (e.g. `內湖區`). Repeatable. |
| `--min-price-wan` | yungching, hbhousing | no | Minimum price in 萬. Server-side filter. |
| `--max-price-wan` | yungching, hbhousing | no | Maximum price in 萬. Server-side filter. |
| `--min-rooms` | yungching, hbhousing | no | Minimum room count. Server-side filter. |
| `--max-rooms` | yungching, hbhousing | no | Maximum room count. Server-side filter. |
| `--max-age` | yungching | no | Maximum building age in years. Server-side filter. |
| `--style` | hbhousing | no | Building style name (e.g. `大樓`, `華廈`, `公寓`). Repeatable. |
| `--page` | 591 | no | Starting page (1-indexed). Default `1`. |
| `--max-pages` | all | no | Pages to fetch. Default `1`. |
| `--db` | all | no | SQLite path (created if missing). Default `data/listings.sqlite`. |
| `--insecure` | 591 | no | Disable TLS verification. **Required for 591** (see Quirks). |

**Output line:** `pages=<N> fetched=<M> persisted=<K>` — `persisted` may be
less than `fetched` only on parse errors.

**Page sizes:** 591 = 30/page, yungching = 30/page, hbhousing = 10/page.

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

### Section ids (桃園市, region=`taoyuan`)

| id | 區 | id | 區 | id | 區 |
|---:|---|---:|---|---:|---|
| 67 | 中壢 | 72 | 觀音 | 77 | 復興 |
| 68 | 平鎮 | 73 | 桃園 | 78 | 大園 |
| 69 | 龍潭 | 74 | 龜山 | 79 | 蘆竹 |
| 70 | 楊梅 | 75 | 八德 |    |     |
| 71 | 新屋 | 76 | 大溪 |    |     |

### Section ids (台中市, region=`taichung`)

| id | 區 | id | 區 | id | 區 |
|---:|---|---:|---|---:|---|
|  98 | 中區   | 108 | 霧峰 | 118 | 神岡 |
|  99 | 東區   | 109 | 烏日 | 119 | 大肚 |
| 100 | 南區   | 110 | 豐原 | 120 | 沙鹿 |
| 101 | 西區   | 111 | 后里 | 121 | 龍井 |
| 102 | 北區   | 112 | 石岡 | 122 | 梧棲 |
| 103 | 北屯   | 113 | 東勢 | 123 | 清水 |
| 104 | 西屯   | 114 | 和平 | 124 | 大甲 |
| 105 | 南屯   | 115 | 新社 | 125 | 外埔 |
| 106 | 太平   | 116 | 潭子 | 126 | 大安 |
| 107 | 大里   | 117 | 大雅 |     |     |

### Section ids (高雄市, region=`kaohsiung`)

| id | 區 | id | 區 | id | 區 |
|---:|---|---:|---|---:|---|
| 243 | 新興 | 254 | 仁武 | 268 | 鳳山 |
| 244 | 前金 | 255 | 大社 | 269 | 大寮 |
| 245 | 苓雅 | 258 | 岡山 | 270 | 林園 |
| 246 | 鹽埕 | 259 | 路竹 | 271 | 鳥松 |
| 247 | 鼓山 | 260 | 阿蓮 | 272 | 大樹 |
| 248 | 旗津 | 261 | 田寮 | 273 | 旗山 |
| 249 | 前鎮 | 262 | 燕巢 | 274 | 美濃 |
| 250 | 三民 | 263 | 橋頭 | 275 | 六龜 |
| 251 | 楠梓 | 264 | 梓官 | 276 | 內門 |
| 252 | 小港 | 265 | 彌陀 | 277 | 杉林 |
| 253 | 左營 | 266 | 永安 | 278 | 甲仙 |
|     |      | 267 | 湖內 | 282 | 茄萣 |

> 那瑪夏 / 桃源 / 茂林 may exist as ids but currently return zero listings.

Run `alc-crawler regions` for the same tables on the CLI.

### Shape ids

| id | 類型 |
|---:|---|
| 1 | 公寓 |
| 2 | 電梯大樓 |
| 3 | 透天厝 |
| 4 | 別墅 |
| 8 | 店面 |

### District names (for `--district`, yungching/hbhousing)

Use Chinese district names with `區` suffix. Supported districts per region:

| Region | Districts (partial list — not all regions cover every district) |
|---|---|
| `taipei` | 中正區, 大同區, 中山區, 松山區, 大安區, 萬華區, 信義區, 士林區, 北投區, 內湖區, 南港區, 文山區 |
| `new-taipei` | 板橋區, 汐止區, 永和區, 中和區, 三重區, 新莊區, 淡水區, 新店區, 土城區, 蘆洲區, 樹林區, 林口區, ... |
| `taoyuan` | 桃園區, 中壢區, 平鎮區, 八德區, 楊梅區, 蘆竹區, 龜山區, 龍潭區, 大溪區, 大園區 |
| `taichung` | 中區, 東區, 南區, 西區, 北區, 北屯區, 西屯區, 南屯區, 太平區, 大里區, 豐原區 |
| `kaohsiung` | 新興區, 前金區, 苓雅區, 鼓山區, 前鎮區, 三民區, 楠梓區, 左營區, 鳳山區, ... |

### What does NOT work as a crawl-time filter

**591 only:** 591's BFF accepts `price` and `houseage` query params but returns
out-of-range listings anyway, so this CLI does not surface them. **Apply price
and age filters at `query` time** — the data is already on disk.

Yungching and hbhousing respect all filter params server-side.

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
| `--site` | str | `591` (default), `yungching`, or `hbhousing`; matches the tag written by `crawl`. |
| `--section-name` | repeatable str | District name (`內湖區`, `信義區`, ...). |
| `--shape-name` | repeatable str | Shape label (`公寓`, `電梯大樓`, `透天厝`, ...). |
| `--max-price-wan` / `--min-price-wan` | int (萬, 1萬=10,000TWD) | Total price bounds. |
| `--max-age` | int | 屋齡 ≤ N years. |
| `--min-area` | float | 總坪數 ≥ X 坪. |
| `--min-rooms` / `--max-rooms` | int | Number of 房 parsed from `room_layout`. Excludes rows whose layout is non-standard (e.g. `開放式格局`). |
| `--address-contains` | str | Substring on raw address. |
| `--community-contains` | str | Substring on community name. |
| `--title-contains` | str | Substring on agent's listing title. Useful for school or landmark keywords. |
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
   WHERE address_district='大安區'
     AND price_amount <= 40000000
     AND house_age_years <= 25
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
├── adapters/sites/  # Per-site anti-corruption layers:
│   ├── site_591/        # 591 BFF API parser + URL builder
│   ├── site_yungching/  # Yungching AES-encrypted API parser
│   └── site_hbhousing/  # hbhousing Nuxt3 SSR HTML parser
├── interfaces/cli/  # Typer CLI (`alc-crawler`)
└── tracking/        # Time-series submodule (own domain/app/infra/cli)
    ├── domain/          # ListingSnapshot, PriceChange, DistrictSummary, ...
    ├── application/     # Use cases + SnapshotRepository port
    ├── infrastructure/  # DuckDB adapter + schema.sql
    └── interfaces/
        ├── cli/         # Typer CLI (`alc-tracker`)
        └── reports/     # Markdown + matplotlib renderers
```

Storage is SQLite via the `ListingRepository` port; swap to PostgreSQL/Redis
without touching application or domain code. The tracking submodule reads
the canonical SQLite read-only and writes its own DuckDB — never the other
way around.

---

## Tracking (price history & market trends)

`alc-crawler` always overwrites the latest state. To answer "did this
listing's price drop?" or "what's the median 大安區 unit price this week?"
you need a time-series store. The `alc-tracker` CLI maintains a separate
**DuckDB** file with one append-only row per `(snapshot_date, site,
external_id)`.

```
alc-crawler crawl ...     # writes data/listings.sqlite (latest state)
alc-tracker snapshot ...  # copies today's state -> data/tracking.duckdb
alc-tracker price-changes ...
alc-tracker market-summary ...
```

### Daily snapshot

```bash
# Run after the daily crawl. Idempotent: re-running for the same --date
# overwrites that day's rows, so cron retries are safe.
uv run alc-tracker snapshot \
    --canonical-db data/listings.sqlite \
    --tracking-db  data/tracking.duckdb \
    --date 2026-05-09           # optional; defaults to today
```

### Price changes

```bash
# Listings whose price moved between --since and --until.
# --until defaults to today. Markdown is the default output format.
uv run alc-tracker price-changes \
    --tracking-db data/tracking.duckdb \
    --since 2026-05-01 --until 2026-05-09 \
    --site 591 --only-drops
```

`--format plain` emits a fixed-width text table instead of a markdown one.

### Market summary

```bash
# Per-district median price + median/P25/P75 unit price for one day.
# Pass --chart to also write a PNG bar chart with P25-P75 error bars.
uv run alc-tracker market-summary \
    --tracking-db data/tracking.duckdb \
    --date 2026-05-09 \
    --site 591 \
    --chart out/unit-price-2026-05-09.png
```

The chart uses matplotlib's headless `Agg` backend and probes for a
CJK-capable system font (PingFang TC, Heiti TC, Noto Sans CJK, ...) so
district names render as glyphs instead of tofu boxes.

### Cron example (macOS launchd / Linux cron)

```cron
# 07:00 daily: refresh canonical state, then snapshot it.
0 7 * * *  cd ~/Documents/projects/alc-crawler && \
           uv run alc-crawler crawl 591 --region taipei --section 5 \
               --max-pages 10 --insecure --db data/daan.sqlite && \
           uv run alc-tracker snapshot \
               --canonical-db data/daan.sqlite \
               --tracking-db  data/tracking.duckdb
```

### DuckDB schema

Two tables in the tracking DB:

| Table | PK | Notes |
|---|---|---|
| `listing_snapshots` | `(snapshot_date, site, external_id)` | One row per listing per day; ON CONFLICT updates that day's row. |
| `crawl_runs` | `(run_id)` | Provenance: timestamp, status, listing_count, error message. |

Query directly when the CLI is too restrictive:

```bash
duckdb data/tracking.duckdb \
  "SELECT snapshot_date, COUNT(*) FROM listing_snapshots
   WHERE district='大安區' GROUP BY 1 ORDER BY 1 DESC LIMIT 14;"
```

---

## Quirks

### 591

- **TLS:** 591's TWCA intermediate cert is missing the RFC 5280 Subject Key
  Identifier extension and is rejected by recent OpenSSL. Pass `--insecure` to
  `crawl` to disable verification. (Curl/browsers accept it; Python's `ssl`
  does not.)
- **Detail pages:** Price/area on per-listing detail HTML are client-side
  obfuscated (`<web-component-image>` / `<web-component-obfuscate>` via SeaJS).
  The crawler uses 591's BFF list endpoint instead.
- **Filter at query time:** the BFF ignores `price` and `houseage` constraints;
  crawl broadly, filter locally.

### Yungching (永慶房屋)

- **AES-encrypted responses:** Yungching's search API wraps all JSON payloads
  in AES-256-CBC encryption (passphrase `"YungChing.Buy"`, PBKDF2 key
  derivation). The adapter decrypts transparently — no user action needed.
- **Server-side filters work:** Unlike 591, price/age/room filters are enforced
  by the API. Crawl with filters to reduce bandwidth.

### hbhousing (住商不動產)

- **Nuxt3 SSR parsing:** hbhousing is a Nuxt3 app. Listing data is embedded in
  the HTML as `<script type="application/json" data-nuxt-data="nuxt-app">` in
  devalue format (index-reference JSON arrays). The adapter parses this directly
  from the server-rendered HTML — no separate API call.
- **Path-based filters:** Filters are encoded in the URL path (zip codes,
  `{min}-{max}-price`, `{min}_{max}-room-pattern`, `{style}-style`). All
  filters are respected server-side.
- **10 items per page:** Much smaller page size than 591/yungching (30). Use
  higher `--max-pages` for equivalent coverage.

---

## Development

```bash
uv run pytest                  # unit + integration
uv run ruff check .            # lint
uv run mypy src                # types
```

Tests follow TDD; commits land per milestone with all three checks green.
