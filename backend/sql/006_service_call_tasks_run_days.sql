ALTER TABLE service_call_tasks
ADD COLUMN IF NOT EXISTS run_days TEXT[] NOT NULL DEFAULT ARRAY['mon','tue','wed','thu','fri','sat','sun'];
