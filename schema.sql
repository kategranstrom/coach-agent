-- Coach: SQLite schema

CREATE TABLE IF NOT EXISTS activities (
    activity_id       TEXT PRIMARY KEY,      -- Garmin's activity ID
    sport             TEXT NOT NULL,
    start_time        TEXT NOT NULL,         -- ISO 8601
    duration_s        REAL,
    distance_m        REAL,
    avg_hr            INTEGER,
    max_hr            INTEGER,
    calories          INTEGER,
    elevation_gain_m  REAL,
    training_load     REAL,                  -- Garmin's own training load metric, if present
    avg_pace_s_per_km REAL,
    raw_json          TEXT NOT NULL,         -- full Garmin payload; covers sport-specific fields not modeled above (stroke count, cadence, power, laps, etc.)
    synced_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wellness (
    date              TEXT PRIMARY KEY,      -- ISO date, one row per day
    resting_hr        INTEGER,
    sleep_score       INTEGER,
    sleep_duration_s  REAL,
    body_battery_min  INTEGER,
    body_battery_max  INTEGER,
    stress_avg        INTEGER,
    steps             INTEGER,
    weight_kg         REAL,
    vo2max            REAL,
    raw_json          TEXT NOT NULL,
    synced_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS checkins (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    date              TEXT NOT NULL,
    activity_id       TEXT REFERENCES activities(activity_id),
    activity_text     TEXT,                  -- freeform "what I did" when there's no linked Garmin activity yet (e.g. historical import)
    knee_stress       INTEGER,               -- self-rating, e.g. 1-5; nullable
    comment           TEXT,
    source            TEXT NOT NULL CHECK (source IN ('sheet_import', 'chatbot')),
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analyses (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    date              TEXT NOT NULL,
    type              TEXT NOT NULL,         -- 'auto_activity_note' | 'weekly_summary' | 'chat_response'
    activity_id       TEXT REFERENCES activities(activity_id),
    content           TEXT NOT NULL,
    flags_json        TEXT,                  -- structured flags raised (load spike, injury risk, technique note), for backtesting/eval
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_history (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    role              TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content           TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sync_state (
    source            TEXT PRIMARY KEY,      -- e.g. 'garmin_activities', 'garmin_wellness'
    last_synced_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_activities_start_time ON activities(start_time);
CREATE INDEX IF NOT EXISTS idx_checkins_date ON checkins(date);
CREATE INDEX IF NOT EXISTS idx_analyses_date ON analyses(date);
