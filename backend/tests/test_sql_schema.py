from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent / "sql" / "002_tasks_schema.sql"


def test_schema_file_exists():
    assert SCHEMA_PATH.exists()


def test_schema_defines_expected_tables():
    content = SCHEMA_PATH.read_text(encoding="utf-8")

    for table in [
        "tasks",
        "task_reports",
        "task_schedules",
        "task_executions",
        "execution_reports",
        "execution_logs",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in content


def test_schema_has_foreign_keys_to_tasks():
    content = SCHEMA_PATH.read_text(encoding="utf-8")

    assert "REFERENCES tasks(id) ON DELETE CASCADE" in content
    assert "REFERENCES task_executions(id) ON DELETE CASCADE" in content
