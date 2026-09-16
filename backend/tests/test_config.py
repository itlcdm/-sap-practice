from app.config import Settings

BASE_KWARGS = dict(
    sap_url="https://sap.example.com",
    sap_company_db="TEST",
    sap_username="user",
    sap_password="pass",
    admin_email="admin@example.com",
    admin_password="pass",
    db_host="localhost",
    db_name="test",
    db_user="test",
    db_password="test",
    mail_from="info@example.com",
    mail_smtp_server="smtp.example.com",
    mail_user="info@example.com",
    mail_password="pass",
)


def test_task_sql_connections_parses_json_from_env(monkeypatch):
    monkeypatch.setenv(
        "TASK_SQL_CONNECTIONS",
        '{"InventarioDb": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=x;"}',
    )

    settings = Settings(_env_file=None, **BASE_KWARGS)

    assert settings.task_sql_connections == {
        "InventarioDb": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=x;"
    }


def test_task_output_folder_defaults_to_output(monkeypatch):
    monkeypatch.delenv("TASK_OUTPUT_FOLDER", raising=False)

    settings = Settings(_env_file=None, **BASE_KWARGS)

    assert settings.task_output_folder == "output"


def test_mail_smtp_port_defaults_to_587(monkeypatch):
    monkeypatch.delenv("MAIL_SMTP_PORT", raising=False)

    settings = Settings(_env_file=None, **BASE_KWARGS)

    assert settings.mail_smtp_port == 587
