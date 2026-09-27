-- schema.sql — table definitions

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS cities (
    city_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    country    TEXT    NOT NULL,
    latitude   REAL    NOT NULL,
    longitude  REAL    NOT NULL,
    timezone   TEXT    NOT NULL,
    UNIQUE(name, country)
);

CREATE TABLE IF NOT EXISTS weather_readings (
    reading_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id          INTEGER NOT NULL REFERENCES cities(city_id),
    observed_at      TEXT    NOT NULL,          -- ISO 8601 UTC
    temperature_c    REAL,
    humidity_pct     REAL,
    precipitation_mm REAL,
    wind_speed_kmh   REAL,
    source           TEXT    NOT NULL DEFAULT 'open-meteo',
    ingested_at      TEXT    NOT NULL,          -- when the pipeline wrote it
    UNIQUE(city_id, observed_at)               -- idempotency key
);

CREATE TABLE IF NOT EXISTS rejected_records (
    rejected_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_payload  TEXT    NOT NULL,              -- original JSON for debugging
    reason       TEXT    NOT NULL,
    city_id      INTEGER,
    rejected_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at     TEXT    NOT NULL,
    finished_at    TEXT,
    status         TEXT    NOT NULL,            -- 'running' | 'success' | 'failed'
    rows_extracted INTEGER DEFAULT 0,
    rows_loaded    INTEGER DEFAULT 0,
    rows_rejected  INTEGER DEFAULT 0,
    error_message  TEXT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_readings_city_time
    ON weather_readings(city_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_readings_time
    ON weather_readings(observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_rejected_city
    ON rejected_records(city_id, rejected_at DESC);
