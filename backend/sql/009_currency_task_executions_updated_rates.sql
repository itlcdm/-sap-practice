ALTER TABLE currency_task_executions
ADD COLUMN IF NOT EXISTS updated_rates TEXT[] NOT NULL DEFAULT '{}';
