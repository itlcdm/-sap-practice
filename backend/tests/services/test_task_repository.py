from app.schemas.tasks import TaskCreate, TaskReportIn, TaskUpdate
from app.services import db_service as db_service_module
from app.services.task_repository import TaskRepository


class _NoOpTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConnection:
    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []
        self.fetched: list[tuple[str, tuple]] = []
        self.fetchval_results: list = []
        self.fetchrow_results: list = []
        self.fetch_results: list = []

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchval(self, query, *args):
        self.fetched.append((query, args))
        return self.fetchval_results.pop(0) if self.fetchval_results else None

    async def fetchrow(self, query, *args):
        self.fetched.append((query, args))
        return self.fetchrow_results.pop(0) if self.fetchrow_results else None

    async def fetch(self, query, *args):
        self.fetched.append((query, args))
        return self.fetch_results.pop(0) if self.fetch_results else []

    def transaction(self):
        return _NoOpTransaction()


class FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return FakeAcquire(self._conn)


def use_fake_pool(monkeypatch) -> FakeConnection:
    conn = FakeConnection()
    monkeypatch.setattr(db_service_module.db_service, "pool", FakePool(conn))
    return conn


async def test_create_task_inserts_task_and_reports(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchval_results = [7]

    repo = TaskRepository()
    task_id = await repo.create_task(
        TaskCreate(
            name="Inventario diario",
            connection_name="InventarioDb",
            mail_to="a@example.com",
            reports=[
                TaskReportIn(
                    stored_procedure="ALCONSIT",
                    excel_file_name="ALCONSIT.xlsx",
                    sheet_name="ALCONSIT",
                ),
                TaskReportIn(
                    stored_procedure="ALCONIMS",
                    excel_file_name="ALCONIMS.xlsx",
                    sheet_name="ALCONIMS",
                ),
            ],
        )
    )

    assert task_id == 7

    insert_task_calls = [c for c in conn.executed if "INSERT INTO tasks" in c[0]]
    insert_report_calls = [c for c in conn.executed if "INSERT INTO task_reports" in c[0]]
    assert len(insert_task_calls) == 0  # el INSERT de tasks usa fetchval, no execute
    assert len(insert_report_calls) == 2
    assert insert_report_calls[0][1][1] == 0  # position del primer reporte
    assert insert_report_calls[1][1][1] == 1  # position del segundo reporte


async def test_get_task_returns_none_when_missing(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [None]

    repo = TaskRepository()
    result = await repo.get_task(999)

    assert result is None


async def test_get_task_returns_task_with_reports(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [
        {
            "id": 1,
            "name": "Inventario diario",
            "description": None,
            "connection_name": "InventarioDb",
            "mail_to": "a@example.com",
            "mail_cc": None,
            "mail_subject_template": None,
            "is_active": True,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    conn.fetch_results = [
        [
            {
                "id": 10,
                "position": 0,
                "stored_procedure": "ALCONSIT",
                "excel_file_name": "ALCONSIT.xlsx",
                "sheet_name": "ALCONSIT",
            }
        ]
    ]

    repo = TaskRepository()
    task = await repo.get_task(1)

    assert task.id == 1
    assert task.reports[0].stored_procedure == "ALCONSIT"


async def test_list_tasks_maps_rows(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetch_results = [
        [
            {"id": 1, "name": "Inventario diario", "description": None, "is_active": True, "has_schedule": True}
        ]
    ]

    repo = TaskRepository()
    tasks = await repo.list_tasks()

    assert tasks[0].name == "Inventario diario"
    assert tasks[0].has_schedule is True


async def test_update_task_replaces_reports(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.update_task(
        1,
        TaskUpdate(
            name="Inventario diario",
            connection_name="InventarioDb",
            mail_to="a@example.com",
            is_active=False,
            reports=[
                TaskReportIn(
                    stored_procedure="ALCONSIT",
                    excel_file_name="ALCONSIT.xlsx",
                    sheet_name="ALCONSIT",
                )
            ],
        ),
    )

    update_calls = [c for c in conn.executed if "UPDATE tasks" in c[0]]
    delete_calls = [c for c in conn.executed if "DELETE FROM task_reports" in c[0]]
    insert_calls = [c for c in conn.executed if "INSERT INTO task_reports" in c[0]]

    assert len(update_calls) == 1
    assert update_calls[0][1][-1] is False  # is_active = False
    assert len(delete_calls) == 1
    assert len(insert_calls) == 1


async def test_upsert_schedule_replaces_existing(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchval_results = [5]

    repo = TaskRepository()
    schedule_id = await repo.upsert_schedule(1, "0 8 * * *")

    assert schedule_id == 5
    delete_calls = [c for c in conn.executed if "DELETE FROM task_schedules" in c[0]]
    insert_calls = [c for c in conn.fetched if "INSERT INTO task_schedules" in c[0]]
    assert len(delete_calls) == 1
    assert len(insert_calls) == 1
    assert insert_calls[0][1] == (1, "0 8 * * *")


async def test_delete_schedule_deletes_by_task_id(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.delete_schedule(1)

    delete_calls = [c for c in conn.executed if "DELETE FROM task_schedules" in c[0]]
    assert delete_calls == [("DELETE FROM task_schedules WHERE task_id = $1", (1,))]


async def test_get_schedule_cron_returns_expression(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchval_results = ["0 8 * * *"]

    repo = TaskRepository()
    cron_expression = await repo.get_schedule_cron(1)

    assert cron_expression == "0 8 * * *"
    select_calls = [c for c in conn.fetched if "FROM task_schedules" in c[0]]
    assert len(select_calls) == 1
    assert select_calls[0][1] == (1,)


async def test_get_schedule_cron_returns_none_when_no_schedule(monkeypatch):
    use_fake_pool(monkeypatch)

    repo = TaskRepository()

    assert await repo.get_schedule_cron(1) is None


async def test_list_active_schedules_joins_task_name(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetch_results = [
        [{"task_id": 1, "task_name": "Inventario diario", "cron_expression": "0 8 * * *"}]
    ]

    repo = TaskRepository()
    schedules = await repo.list_active_schedules()

    assert schedules == [
        {"task_id": 1, "task_name": "Inventario diario", "cron_expression": "0 8 * * *"}
    ]


async def test_create_execution_returns_id(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchval_results = [42]

    repo = TaskRepository()
    execution_id = await repo.create_execution(1, "manual")

    assert execution_id == 42
    assert conn.fetched[0][1] == (1, "manual")


async def test_get_running_execution_returns_id_or_none(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchval_results = [None]

    repo = TaskRepository()
    result = await repo.get_running_execution(1)

    assert result is None


async def test_mark_stale_running_as_failed_updates_all_running_rows(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.mark_stale_running_as_failed()

    assert len(conn.executed) == 1
    query, args = conn.executed[0]
    assert "UPDATE task_executions" in query
    assert "status = 'failed'" in query
    assert "WHERE status = 'running'" in query
    assert "Interrumpida por reinicio del servidor" in query
    assert "finished_at = now()" in query
    assert args == ()


async def test_finish_execution_updates_status(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.finish_execution(42, "failed", "boom")

    assert conn.executed[0][1] == (42, "failed", "boom")


async def test_add_execution_report_inserts_row(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.add_execution_report(42, "ALCONSIT", "ALCONSIT_42.xlsx", "/output/ALCONSIT_42.xlsx", 100)

    assert conn.executed[0][1] == (42, "ALCONSIT", "ALCONSIT_42.xlsx", "/output/ALCONSIT_42.xlsx", 100)


async def test_add_execution_log_inserts_row(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.add_execution_log(42, "info", "Ejecutando ALCONSIT")

    assert conn.executed[0][1] == (42, "info", "Ejecutando ALCONSIT")


async def test_list_executions_maps_rows(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetch_results = [
        [
            {
                "id": 42,
                "task_id": 1,
                "task_name": "Inventario diario",
                "trigger_type": "manual",
                "status": "running",
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": None,
                "error_message": None,
            }
        ]
    ]

    repo = TaskRepository()
    executions = await repo.list_executions(status="running", limit=50, offset=0)

    assert executions[0].id == 42
    assert executions[0].status == "running"


async def test_get_execution_returns_none_when_missing(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [None]

    repo = TaskRepository()
    result = await repo.get_execution(999)

    assert result is None


async def test_get_execution_returns_detail_with_reports(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [
        {
            "id": 42,
            "task_id": 1,
            "task_name": "Inventario diario",
            "trigger_type": "manual",
            "status": "success",
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:05:00+00:00",
            "error_message": None,
        }
    ]
    conn.fetch_results = [
        [{"id": 1, "stored_procedure": "ALCONSIT", "file_name": "ALCONSIT_42.xlsx", "row_count": 100}]
    ]

    repo = TaskRepository()
    execution = await repo.get_execution(42)

    assert execution.id == 42
    assert execution.reports[0].file_name == "ALCONSIT_42.xlsx"


async def test_list_execution_logs_maps_rows(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetch_results = [
        [{"id": 1, "timestamp": "2026-01-01T00:00:00+00:00", "level": "info", "message": "Ejecutando ALCONSIT"}]
    ]

    repo = TaskRepository()
    logs = await repo.list_execution_logs(42)

    assert logs[0].message == "Ejecutando ALCONSIT"


async def test_get_execution_report_returns_file_info(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [
        {"id": 1, "file_name": "ALCONSIT_42.xlsx", "file_path": "/output/ALCONSIT_42.xlsx"}
    ]

    repo = TaskRepository()
    report = await repo.get_execution_report(42, 1)

    assert report["file_path"] == "/output/ALCONSIT_42.xlsx"
