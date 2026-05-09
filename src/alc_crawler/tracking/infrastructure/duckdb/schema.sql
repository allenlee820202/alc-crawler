-- Tracking storage schema (DuckDB).
--
-- listing_snapshots: append-only daily snapshots. Re-running the same
-- day overwrites that day's row (idempotent), so cron retries are safe.
-- Composite PK (snapshot_date, site, external_id) is the natural identity.
CREATE TABLE IF NOT EXISTS listing_snapshots (
    snapshot_date          DATE      NOT NULL,
    site                   TEXT      NOT NULL,
    external_id            TEXT      NOT NULL,
    price_amount           BIGINT    NOT NULL,
    area_ping              DOUBLE,
    unit_price_per_ping    DOUBLE,
    house_age_years        INTEGER,
    view_count             INTEGER,
    community_name         TEXT,
    address_district       TEXT,
    shape                  TEXT,
    source_attributes_json TEXT,
    PRIMARY KEY (snapshot_date, site, external_id)
);

-- Provenance for one crawl invocation. Links a snapshot day to its
-- source crawl so reports can flag partial/failed days.
CREATE TABLE IF NOT EXISTS crawl_runs (
    run_id             TEXT       PRIMARY KEY,
    started_at         TIMESTAMP  NOT NULL,
    completed_at       TIMESTAMP,
    site               TEXT       NOT NULL,
    region             TEXT       NOT NULL,
    pages_fetched      INTEGER    NOT NULL,
    listings_seen      INTEGER    NOT NULL,
    listings_persisted INTEGER    NOT NULL,
    status             TEXT       NOT NULL,
    error_message      TEXT
);

-- watched_listings: manual watchlist curated by the user.
-- One row per (site, external_id). Re-adding updates nickname but
-- does NOT bump added_at (use ON CONFLICT DO UPDATE on nickname only).
CREATE TABLE IF NOT EXISTS watched_listings (
    site        TEXT      NOT NULL,
    external_id TEXT      NOT NULL,
    nickname    TEXT,
    added_at    TIMESTAMP NOT NULL,
    PRIMARY KEY (site, external_id)
);
