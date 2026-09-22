CREATE TABLE IF NOT EXISTS currency_tasks (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    company_id BIGINT NOT NULL REFERENCES service_layer_companies(id) ON DELETE RESTRICT,
    local_currency TEXT NOT NULL DEFAULT 'USD',
    target_currencies TEXT[] NOT NULL,
    rate_api_url TEXT NOT NULL DEFAULT 'https://v6.exchangerate-api.com/v6/7351996bac331d17f404e7ff/pair',
    run_at TIME NOT NULL DEFAULT '08:00',
    mail_to TEXT NOT NULL,
    mail_cc TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_currency_tasks_company_id ON currency_tasks(company_id);
CREATE INDEX IF NOT EXISTS idx_currency_tasks_active ON currency_tasks(is_active);

CREATE TABLE IF NOT EXISTS currency_task_executions (
    id BIGSERIAL PRIMARY KEY,
    currency_task_id BIGINT NOT NULL REFERENCES currency_tasks(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('manual', 'scheduled')),
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')) DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_currency_task_executions_status
ON currency_task_executions(status);
