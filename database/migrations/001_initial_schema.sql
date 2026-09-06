CREATE TABLE IF NOT EXISTS ngdp.dataset_source (
    source_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL CHECK (BTRIM(provider) <> ''),
    table_id TEXT NOT NULL CHECK (BTRIM(table_id) <> ''),
    title TEXT NOT NULL CHECK (BTRIM(title) <> ''),
    table_url TEXT NOT NULL CHECK (BTRIM(table_url) <> ''),
    api_url TEXT NOT NULL CHECK (BTRIM(api_url) <> ''),
    unit TEXT NOT NULL CHECK (BTRIM(unit) <> ''),
    frequency TEXT NOT NULL CHECK (BTRIM(frequency) <> ''),
    license_identifier TEXT NOT NULL CHECK (BTRIM(license_identifier) <> ''),
    license_url TEXT NOT NULL CHECK (BTRIM(license_url) <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT dataset_source_identity UNIQUE (provider, table_id)
);

CREATE TABLE IF NOT EXISTS ngdp.source_snapshot (
    snapshot_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id BIGINT NOT NULL REFERENCES ngdp.dataset_source(source_id),
    raw_sha256 TEXT NOT NULL,
    processed_sha256 TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    source_updated_at TIMESTAMPTZ,
    verified_on DATE NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    record_count INTEGER NOT NULL CHECK (record_count > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT source_snapshot_identity
        UNIQUE (source_id, raw_sha256, processed_sha256),
    CONSTRAINT source_snapshot_hash_format
        CHECK (
            raw_sha256 ~ '^[0-9a-f]{64}$'
            AND processed_sha256 ~ '^[0-9a-f]{64}$'
        ),
    CONSTRAINT source_snapshot_period_order CHECK (period_start <= period_end),
    CONSTRAINT source_snapshot_month_start
        CHECK (
            EXTRACT(DAY FROM period_start) = 1
            AND EXTRACT(DAY FROM period_end) = 1
        )
);

CREATE TABLE IF NOT EXISTS ngdp.energy_source (
    energy_source_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id BIGINT NOT NULL REFERENCES ngdp.dataset_source(source_id),
    source_code TEXT NOT NULL CHECK (BTRIM(source_code) <> ''),
    name TEXT NOT NULL CHECK (BTRIM(name) <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT energy_source_code_identity UNIQUE (source_id, source_code),
    CONSTRAINT energy_source_name_identity UNIQUE (source_id, name)
);

CREATE TABLE IF NOT EXISTS ngdp.generation_observation (
    snapshot_id BIGINT NOT NULL REFERENCES ngdp.source_snapshot(snapshot_id),
    energy_source_id BIGINT NOT NULL
        REFERENCES ngdp.energy_source(energy_source_id),
    period_start DATE NOT NULL,
    production_mwh NUMERIC(20, 3) NOT NULL CHECK (production_mwh >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (snapshot_id, energy_source_id, period_start),
    CONSTRAINT generation_observation_month_start
        CHECK (EXTRACT(DAY FROM period_start) = 1)
);

CREATE INDEX IF NOT EXISTS generation_observation_period_idx
    ON ngdp.generation_observation (period_start);

CREATE INDEX IF NOT EXISTS generation_observation_source_period_idx
    ON ngdp.generation_observation (energy_source_id, period_start);

CREATE OR REPLACE VIEW ngdp.current_generation AS
WITH latest_snapshot AS (
    SELECT DISTINCT ON (source_id)
        source_id,
        snapshot_id
    FROM ngdp.source_snapshot
    ORDER BY source_id, retrieved_at DESC, snapshot_id DESC
)
SELECT
    ds.provider,
    ds.table_id,
    ds.title,
    ds.unit,
    es.source_code,
    es.name AS energy_source,
    observation.period_start,
    observation.production_mwh,
    snapshot.raw_sha256,
    snapshot.processed_sha256,
    snapshot.retrieved_at,
    snapshot.source_updated_at,
    snapshot.verified_on
FROM latest_snapshot AS latest
JOIN ngdp.source_snapshot AS snapshot
    ON snapshot.snapshot_id = latest.snapshot_id
JOIN ngdp.dataset_source AS ds
    ON ds.source_id = snapshot.source_id
JOIN ngdp.generation_observation AS observation
    ON observation.snapshot_id = snapshot.snapshot_id
JOIN ngdp.energy_source AS es
    ON es.energy_source_id = observation.energy_source_id;
