CREATE TABLE IF NOT EXISTS app_settings (
    id SMALLINT PRIMARY KEY DEFAULT 1,
    timezone_offset_hours SMALLINT NOT NULL DEFAULT -5,
    default_batch_size SMALLINT NOT NULL DEFAULT 20,
    max_retry_attempts SMALLINT NOT NULL DEFAULT 5,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT app_settings_singleton CHECK (id = 1)
);

INSERT INTO app_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
