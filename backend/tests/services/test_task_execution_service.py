from unittest.mock import AsyncMock

import pytest

from app.services.task_execution_service import (
    TaskAlreadyRunningError,
    continuar_ejecucion,
    ejecutar_tarea,
    iniciar_ejecucion,
)


class FakeReport:
    def __init__(self, stored_procedure, excel_file_name, sheet_name):
        self.stored_procedure = stored_procedure
        self.excel_file_name = excel_file_name
        self.sheet_name = sheet_name


class FakeTask:
    def __init__(self, reports):
        self.name = "Inventario diario"
        self.connection_name = "InventarioDb"
        self.mail_to = "a@example.com"
        self.mail_cc = None
        self.mail_subject_template = None
        self.reports = reports


def make_repo(task, running_execution_id=None, new_execution_id=100):
    repo = AsyncMock()
    repo.get_running_execution.return_value = running_execution_id
    repo.get_task.return_value = task
    repo.create_execution.return_value = new_execution_id
    return repo


async def test_iniciar_ejecucion_raises_when_already_running():
    repo = make_repo(task=None, running_execution_id=55)

    with pytest.raises(TaskAlreadyRunningError):
        await iniciar_ejecucion(1, "manual", repo=repo)

    repo.create_execution.assert_not_called()


async def test_iniciar_ejecucion_creates_execution_when_free():
    repo = make_repo(task=None, running_execution_id=None, new_execution_id=100)

    execution_id = await iniciar_ejecucion(1, "manual", repo=repo)

    assert execution_id == 100
    repo.create_execution.assert_called_once_with(1, "manual")


async def test_continuar_ejecucion_success_generates_files_and_sends_one_email(monkeypatch):
    task = FakeTask(
        reports=[
            FakeReport("ALCONSIT", "ALCONSIT.xlsx", "ALCONSIT"),
            FakeReport("ALCONIMS", "ALCONIMS.xlsx", "ALCONIMS"),
        ]
    )
    repo = make_repo(task=task)

    sql_client = AsyncMock()
    sql_client.fetch_stored_procedure_rows.return_value = (["ItemCode"], [("A1",)])

    excel = AsyncMock()
    excel.generar_excel = AsyncMock(return_value=1)

    mailer = AsyncMock()

    monkeypatch.setattr(
        "app.services.task_execution_service.settings.task_sql_connections",
        {"InventarioDb": "DRIVER=x;"},
    )
    monkeypatch.setattr(
        "app.services.task_execution_service.settings.task_output_folder", "output"
    )

    await continuar_ejecucion(100, 1, repo=repo, sql_client=sql_client, excel=excel, mailer=mailer)

    assert sql_client.fetch_stored_procedure_rows.call_count == 2
    assert excel.generar_excel.call_count == 2
    mailer.enviar_correo_con_adjuntos.assert_called_once()
    repo.finish_execution.assert_called_once_with(100, "success", None)


async def test_continuar_ejecucion_stops_and_marks_failed_on_report_error(monkeypatch):
    task = FakeTask(
        reports=[
            FakeReport("ALCONSIT", "ALCONSIT.xlsx", "ALCONSIT"),
            FakeReport("ALCONIMS", "ALCONIMS.xlsx", "ALCONIMS"),
        ]
    )
    repo = make_repo(task=task)

    sql_client = AsyncMock()
    sql_client.fetch_stored_procedure_rows.side_effect = RuntimeError("SP falló")

    excel = AsyncMock()
    mailer = AsyncMock()

    monkeypatch.setattr(
        "app.services.task_execution_service.settings.task_sql_connections",
        {"InventarioDb": "DRIVER=x;"},
    )

    await continuar_ejecucion(100, 1, repo=repo, sql_client=sql_client, excel=excel, mailer=mailer)

    assert sql_client.fetch_stored_procedure_rows.call_count == 1
    excel.generar_excel.assert_not_called()
    mailer.enviar_correo_con_adjuntos.assert_not_called()
    repo.finish_execution.assert_called_once_with(100, "failed", "SP falló")


async def test_continuar_ejecucion_fails_when_connection_name_unknown(monkeypatch):
    task = FakeTask(reports=[FakeReport("ALCONSIT", "ALCONSIT.xlsx", "ALCONSIT")])
    repo = make_repo(task=task)

    sql_client = AsyncMock()
    excel = AsyncMock()
    mailer = AsyncMock()

    monkeypatch.setattr(
        "app.services.task_execution_service.settings.task_sql_connections", {}
    )

    await continuar_ejecucion(100, 1, repo=repo, sql_client=sql_client, excel=excel, mailer=mailer)

    sql_client.fetch_stored_procedure_rows.assert_not_called()
    status, error = repo.finish_execution.call_args.args[1], repo.finish_execution.call_args.args[2]
    assert status == "failed"
    assert "InventarioDb" in error


async def test_ejecutar_tarea_calls_iniciar_and_continuar():
    task = FakeTask(reports=[FakeReport("ALCONSIT", "ALCONSIT.xlsx", "ALCONSIT")])
    repo = make_repo(task=task, new_execution_id=200)

    sql_client = AsyncMock()
    sql_client.fetch_stored_procedure_rows.return_value = (["ItemCode"], [("A1",)])
    excel = AsyncMock()
    excel.generar_excel = AsyncMock(return_value=1)
    mailer = AsyncMock()

    import app.services.task_execution_service as module

    module.settings.task_sql_connections = {"InventarioDb": "DRIVER=x;"}

    execution_id = await ejecutar_tarea(
        1, "scheduled", repo=repo, sql_client=sql_client, excel=excel, mailer=mailer
    )

    assert execution_id == 200
    repo.create_execution.assert_called_once_with(1, "scheduled")
    mailer.enviar_correo_con_adjuntos.assert_called_once()
