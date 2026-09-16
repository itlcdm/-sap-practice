from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.tasks import TaskOut
from app.services.task_repository import get_task_repository
from app.services.scheduler_service import get_scheduler_service
import app.routers.tasks as tasks_router_module


def a_task_out(is_active=True):
    # update_task declares response_model=TaskOut, so repo.get_task has to
    # return something that actually validates (a bare AsyncMock would not).
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return TaskOut(
        id=1,
        name="Inventario diario",
        description=None,
        connection_name="InventarioDb",
        mail_to="a@example.com",
        mail_cc=None,
        mail_subject_template=None,
        is_active=is_active,
        created_at=now,
        updated_at=now,
        reports=[],
    )


def a_task_update_payload(is_active):
    return {
        "name": "Inventario diario",
        "connection_name": "InventarioDb",
        "mail_to": "a@example.com",
        "is_active": is_active,
        "reports": [
            {
                "stored_procedure": "ALCONSIT",
                "excel_file_name": "ALCONSIT.xlsx",
                "sheet_name": "ALCONSIT",
            }
        ],
    }


def make_client(repo, scheduler=None):
    app.dependency_overrides[get_task_repository] = lambda: repo
    if scheduler is not None:
        app.dependency_overrides[get_scheduler_service] = lambda: scheduler
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_list_tasks_returns_summaries():
    repo = AsyncMock()
    repo.list_tasks.return_value = []
    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert response.json() == []
    next(gen, None)


def test_get_task_404_when_missing():
    repo = AsyncMock()
    repo.get_task.return_value = None
    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/tasks/999")

    assert response.status_code == 404
    next(gen, None)


def test_update_task_unschedules_when_deactivated():
    repo = AsyncMock()
    repo.get_task.return_value = a_task_out(is_active=False)

    scheduler = MagicMock()

    gen = make_client(repo, scheduler=scheduler)
    client = next(gen)

    response = client.put("/api/tasks/1", json=a_task_update_payload(is_active=False))

    assert response.status_code == 200
    scheduler.unschedule_task.assert_called_once_with(1)
    scheduler.schedule_task.assert_not_called()
    next(gen, None)


def test_update_task_reschedules_when_reactivated_with_existing_schedule():
    repo = AsyncMock()
    repo.get_task.return_value = a_task_out(is_active=True)
    repo.get_schedule_cron.return_value = "0 8 * * *"

    scheduler = MagicMock()

    gen = make_client(repo, scheduler=scheduler)
    client = next(gen)

    response = client.put("/api/tasks/1", json=a_task_update_payload(is_active=True))

    assert response.status_code == 200
    scheduler.schedule_task.assert_called_once_with(1, "0 8 * * *")
    scheduler.unschedule_task.assert_not_called()
    next(gen, None)


def test_update_task_does_not_schedule_when_task_has_no_schedule():
    repo = AsyncMock()
    repo.get_task.return_value = a_task_out(is_active=True)
    repo.get_schedule_cron.return_value = None

    scheduler = MagicMock()

    gen = make_client(repo, scheduler=scheduler)
    client = next(gen)

    response = client.put("/api/tasks/1", json=a_task_update_payload(is_active=True))

    assert response.status_code == 200
    scheduler.schedule_task.assert_not_called()
    next(gen, None)


def test_run_task_returns_409_when_already_running(monkeypatch):
    repo = AsyncMock()
    repo.get_task.return_value = object()
    repo.get_running_execution.return_value = 55

    gen = make_client(repo)
    client = next(gen)

    response = client.post("/api/tasks/1/run")

    assert response.status_code == 409
    next(gen, None)


def test_run_task_returns_execution_id_and_schedules_background_work(monkeypatch):
    repo = AsyncMock()
    repo.get_task.return_value = object()
    repo.get_running_execution.return_value = None
    repo.create_execution.return_value = 321

    continuar_calls = []

    async def fake_continuar(execution_id, task_id, **kwargs):
        continuar_calls.append((execution_id, task_id))

    monkeypatch.setattr(tasks_router_module, "continuar_ejecucion", fake_continuar)

    gen = make_client(repo)
    client = next(gen)

    response = client.post("/api/tasks/1/run")

    assert response.status_code == 200
    assert response.json() == {"execution_id": 321}
    assert continuar_calls == [(321, 1)]
    next(gen, None)


def test_create_schedule_registers_job_and_returns_next_run_time():
    repo = AsyncMock()
    repo.get_task.return_value = type("T", (), {"name": "Inventario diario"})()

    # SchedulerService.schedule_task / get_next_run_time are synchronous in
    # production (see app/services/scheduler_service.py), so the double must
    # be a MagicMock: a bare AsyncMock() would make these attributes
    # AsyncMock too, returning unawaited coroutines instead of real values.
    scheduler = MagicMock()
    scheduler.get_next_run_time.return_value = None

    gen = make_client(repo, scheduler=scheduler)
    client = next(gen)

    response = client.post("/api/tasks/1/schedule", json={"cron_expression": "0 8 * * *"})

    assert response.status_code == 200
    scheduler.schedule_task.assert_called_once_with(1, "0 8 * * *")
    next(gen, None)


def test_create_schedule_rejects_invalid_cron_before_persisting():
    repo = AsyncMock()
    repo.get_task.return_value = type("T", (), {"name": "Inventario diario"})()

    scheduler = MagicMock()

    gen = make_client(repo, scheduler=scheduler)
    client = next(gen)

    response = client.post("/api/tasks/1/schedule", json={"cron_expression": "99 8 * * *"})

    # El validador de ScheduleIn corta el request antes del router, así que la
    # fila inválida nunca llega a Postgres ni al scheduler en memoria.
    assert response.status_code == 422
    repo.upsert_schedule.assert_not_called()
    scheduler.schedule_task.assert_not_called()
    next(gen, None)
