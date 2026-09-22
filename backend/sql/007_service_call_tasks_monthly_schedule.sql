ALTER TABLE service_call_tasks
ADD COLUMN IF NOT EXISTS schedule_type TEXT NOT NULL DEFAULT 'weekly'
    CHECK (schedule_type IN ('weekly', 'monthly'));

ALTER TABLE service_call_tasks
ADD COLUMN IF NOT EXISTS run_day_of_month SMALLINT;
