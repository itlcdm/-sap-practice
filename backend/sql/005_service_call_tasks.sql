CREATE TABLE IF NOT EXISTS service_call_tasks (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    company_id BIGINT NOT NULL REFERENCES service_layer_companies(id) ON DELETE CASCADE,
    connection_name TEXT NOT NULL DEFAULT 'InventarioDb',
    source_view TEXT NOT NULL,
    run_at TIME NOT NULL DEFAULT '08:00',
    mail_to TEXT NOT NULL,
    mail_cc TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_service_call_tasks_company_id ON service_call_tasks(company_id);
