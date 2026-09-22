ALTER TABLE app_settings
  ADD COLUMN IF NOT EXISTS mail_smtp_server TEXT,
  ADD COLUMN IF NOT EXISTS mail_smtp_port SMALLINT,
  ADD COLUMN IF NOT EXISTS mail_user TEXT,
  ADD COLUMN IF NOT EXISTS mail_password TEXT,
  ADD COLUMN IF NOT EXISTS mail_from TEXT;

CREATE TABLE IF NOT EXISTS sql_connections (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    driver TEXT NOT NULL DEFAULT 'ODBC Driver 17 for SQL Server',
    server TEXT NOT NULL,
    database TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    extra_params TEXT NOT NULL DEFAULT 'TrustServerCertificate=yes;',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
