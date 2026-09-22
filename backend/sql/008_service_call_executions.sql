CREATE TABLE IF NOT EXISTS service_call_executions (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES service_call_tasks(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('manual', 'scheduled')),
    status TEXT NOT NULL CHECK (
        status IN ('running', 'completed', 'completed_with_errors', 'failed')
    ) DEFAULT 'running',
    dry_run BOOLEAN NOT NULL DEFAULT FALSE,
    batch_size INTEGER NOT NULL DEFAULT 20,
    total_items INTEGER NOT NULL DEFAULT 0,
    successful_items INTEGER NOT NULL DEFAULT 0,
    failed_items INTEGER NOT NULL DEFAULT 0,
    review_items INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_service_call_executions_one_running_per_task
ON service_call_executions(task_id) WHERE status = 'running';

CREATE INDEX IF NOT EXISTS idx_service_call_executions_task_id ON service_call_executions(task_id);

CREATE TABLE IF NOT EXISTS service_call_execution_items (
    id BIGSERIAL PRIMARY KEY,
    execution_id BIGINT NOT NULL REFERENCES service_call_executions(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    source_key TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'processing', 'succeeded', 'failed', 'needs_review')
    ) DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    http_status_code INTEGER,
    sap_response TEXT,
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_service_call_execution_items_execution_id
ON service_call_execution_items(execution_id, status, sequence);
