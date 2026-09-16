from datetime import datetime
from pathlib import Path

import asyncpg

from app.config import settings
from app.services import excel_export, mail_service, sqlserver_client
from app.services.task_repository import TaskRepository, task_repository

DEFAULT_SUBJECT_TEMPLATE = "Reportes {task_name} - {timestamp}"


class TaskAlreadyRunningError(Exception):
    pass


def _default_repo(repo: TaskRepository | None) -> TaskRepository:
    return repo or task_repository


async def iniciar_ejecucion(
    task_id: int, trigger_type: str, *, repo: TaskRepository | None = None
) -> int:
    repo = _default_repo(repo)

    if await repo.get_running_execution(task_id) is not None:
        raise TaskAlreadyRunningError(
            f"La tarea {task_id} ya tiene una ejecución en curso"
        )

    try:
        return await repo.create_execution(task_id, trigger_type)
    except asyncpg.exceptions.UniqueViolationError:
        raise TaskAlreadyRunningError(
            f"La tarea {task_id} ya tiene una ejecución en curso"
        )


async def continuar_ejecucion(
    execution_id: int,
    task_id: int,
    *,
    repo: TaskRepository | None = None,
    sql_client=sqlserver_client,
    excel=excel_export,
    mailer=mail_service,
) -> None:
    repo = _default_repo(repo)
    task = await repo.get_task(task_id)

    if task is None:
        message = f"Tarea {task_id} no encontrada"
        await repo.add_execution_log(execution_id, "error", message)
        await repo.finish_execution(execution_id, "failed", message)
        return

    connection_string = settings.task_sql_connections.get(task.connection_name)
    if connection_string is None:
        message = f"Conexión '{task.connection_name}' no configurada"
        await repo.add_execution_log(execution_id, "error", message)
        await repo.finish_execution(execution_id, "failed", message)
        return

    generated_files = []

    for report in task.reports:
        await repo.add_execution_log(
            execution_id, "info", f"Ejecutando {report.stored_procedure}"
        )

        try:
            columns, rows = await sql_client.fetch_stored_procedure_rows(
                connection_string, report.stored_procedure
            )
        except Exception as exc:
            message = str(exc)
            await repo.add_execution_log(
                execution_id, "error", f"Error ejecutando {report.stored_procedure}: {message}"
            )
            await repo.finish_execution(execution_id, "failed", message)
            return

        base_name = report.excel_file_name.rsplit(".", 1)[0]
        file_name = f"{base_name}_{execution_id}.xlsx"
        file_path = str(Path(settings.task_output_folder) / file_name)

        try:
            row_count = excel.generar_excel(columns, rows, report.sheet_name, file_path)
        except Exception as exc:
            message = str(exc)
            await repo.add_execution_log(
                execution_id, "error", f"Error generando Excel para {report.stored_procedure}: {message}"
            )
            await repo.finish_execution(execution_id, "failed", message)
            return

        generated_files.append(file_path)

        await repo.add_execution_report(
            execution_id, report.stored_procedure, file_name, file_path, row_count
        )
        await repo.add_execution_log(
            execution_id, "info", f"Excel generado: {file_name} ({row_count} filas)"
        )

    subject_template = task.mail_subject_template or DEFAULT_SUBJECT_TEMPLATE
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        subject = subject_template.format(task_name=task.name, timestamp=timestamp)
    except (KeyError, IndexError, ValueError) as exc:
        await repo.add_execution_log(
            execution_id,
            "warning",
            f"Plantilla de asunto inválida ('{subject_template}'): {exc}. Se usa la plantilla por defecto.",
        )
        subject = DEFAULT_SUBJECT_TEMPLATE.format(task_name=task.name, timestamp=timestamp)

    try:
        await mailer.enviar_correo_con_adjuntos(
            to=task.mail_to,
            cc=task.mail_cc,
            subject=subject,
            body=f"Adjunto se envían los reportes generados por la tarea '{task.name}'.",
            attachments=generated_files,
        )
    except Exception as exc:
        message = str(exc)
        await repo.add_execution_log(execution_id, "error", f"Error enviando correo: {message}")
        await repo.finish_execution(execution_id, "failed", message)
        return

    await repo.add_execution_log(execution_id, "info", "Correo enviado correctamente")
    await repo.finish_execution(execution_id, "success", None)


async def ejecutar_tarea(
    task_id: int,
    trigger_type: str,
    *,
    repo: TaskRepository | None = None,
    sql_client=sqlserver_client,
    excel=excel_export,
    mailer=mail_service,
) -> int:
    repo = _default_repo(repo)

    execution_id = await iniciar_ejecucion(task_id, trigger_type, repo=repo)
    await continuar_ejecucion(
        execution_id, task_id, repo=repo, sql_client=sql_client, excel=excel, mailer=mailer
    )

    return execution_id
