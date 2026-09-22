CREATE TABLE IF NOT EXISTS service_layer_companies (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    company_db TEXT NOT NULL,
    service_layer_url TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_service_layer_companies_company_db
ON service_layer_companies(company_db);

CREATE INDEX IF NOT EXISTS idx_service_layer_companies_active
ON service_layer_companies(is_active);
