from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.services.scheduler_service import get_scheduler_service
from app.services.task_repository import get_task_repository


def make_client(repo, scheduler=None):
    app.dependency_overrides[get_task_repository] = lambda: repo
    if scheduler is not None:
        app.dependency_overrides[get_scheduler_service] = lambda: scheduler
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_list_schedules_includes_next_run_time():
    repo = AsyncMock()
    repo.list_active_schedules.return_value = [
        {"task_id": 1, "task_name": "Inventario diario", "cron_expression": "0 8 * * *"}
    ]

    scheduler = MagicMock()
    scheduler.get_next_run_time.return_value = None

    gen = make_client(repo, scheduler=scheduler)
    client = next(gen)

    response = client.get("/api/schedules")

    assert response.status_code == 200
    assert response.json()[0]["task_name"] == "Inventario diario"
    next(gen, None)


def test_get_execution_404_when_missing():
    repo = AsyncMock()
    repo.get_execution.return_value = None
    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/executions/999")

    assert response.status_code == 404
    next(gen, None)


def test_download_report_404_when_missing():
    repo = AsyncMock()
    repo.get_execution_report.return_value = None
    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/executions/1/reports/1/download")

    assert response.status_code == 404
    next(gen, None)


def test_download_report_404_when_file_missing_on_disk(tmp_path):
    missing_path = tmp_path / "borrado.xlsx"

    repo = AsyncMock()
    repo.get_execution_report.return_value = {
        "id": 1,
        "file_name": "borrado.xlsx",
        "file_path": str(missing_path),
    }

    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/executions/1/reports/1/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "Archivo no disponible en disco"
    next(gen, None)


def test_download_report_returns_file(tmp_path):
    file_path = tmp_path / "reporte.xlsx"
    file_path.write_bytes(b"contenido")

    repo = AsyncMock()
    repo.get_execution_report.return_value = {
        "id": 1,
        "file_name": "reporte.xlsx",
        "file_path": str(file_path),
    }

    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/executions/1/reports/1/download")

    assert response.status_code == 200
    assert response.content == b"contenido"
    next(gen, None)
