import hashlib
import json
import logging
import smtplib
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

from app.services import service_layer_batch_client, sqlserver_client
from app.services.app_settings_repository import app_settings_repository
from app.services.company_repository import company_repository
from app.services.service_call_execution_repository import service_call_execution_repository
from app.services.service_call_task_repository import service_call_task_repository
from app.services.sql_connection_repository import sql_connection_repository

logger = logging.getLogger(__name__)

# Índices dentro de la tupla que devuelve sqlserver_client.fetch_service_call_source_rows,
# en el mismo orden que SERVICE_CALL_SOURCE_COLUMNS.
_CLIENTE, _CONTRATO, _ASUNTO, _ARTICULO, _SERIE, _ORIGEN, _STATUS_EQUIPO, _TIPO_SERVICIO, _OC, _FECHA = range(10)


class TaskAlreadyRunningError(Exception):
    pass


def _build_payload(row: tuple, creator_tag: str) -> dict:
    payload = {
        "CustomerCode": row[_CLIENTE] or "",
        "ContractID": row[_CONTRATO],
        "Subject": row[_ASUNTO] or "",
        "ItemCode": row[_ARTICULO] or "",
        "ManufacturerSerialNum": row[_SERIE] or "",
        "Origin": row[_ORIGEN],
        "ProblemType": row[_STATUS_EQUIPO],
        "CallType": row[_TIPO_SERVICIO],
        "U_h_ocent": row[_OC] or "",
        "Resolution": creator_tag,
    }
    # Replica JsonIgnoreCondition.WhenWritingNull del original: omite solo los
    # campos numéricos que vinieron nulos, nunca los strings (quedan como "").
    return {k: v for k, v in payload.items() if v is not None}


def _compute_source_key(company_key: str, row: tuple, payload_json: str) -> str:
    fecha = row[_FECHA]
    fecha_str = fecha.isoformat() if hasattr(fecha, "isoformat") else (str(fecha) if fecha is not None else "")
    raw = "|".join(
        [
            company_key,
            row[_CLIENTE] or "",
            str(row[_CONTRATO]) if row[_CONTRATO] is not None else "",
            row[_ASUNTO] or "",
            row[_ARTICULO] or "",
            row[_SERIE] or "",
            row[_OC] or "",
            fecha_str,
            payload_json,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()


async def iniciar_carga(
    task_id: int, trigger_type: str, *, batch_size: int | None = None, dry_run: bool = False
) -> int:
    if await service_call_execution_repository.get_running_execution(task_id) is not None:
        raise TaskAlreadyRunningError(f"La tarea {task_id} ya tiene una carga en curso")

    task = await service_call_task_repository.get_task(task_id)
    if task is None:
        raise ValueError(f"Tarea {task_id} no encontrada")

    connection_string = await sql_connection_repository.get_connection_string(task.connection_name)
    if connection_string is None:
        raise ValueError(f"Conexión '{task.connection_name}' no configurada")

    app_settings = await app_settings_repository.get_settings()
    resolved_batch_size = batch_size if batch_size is not None else app_settings["default_batch_size"]
    tz = timezone(timedelta(hours=app_settings["timezone_offset_hours"]))

    rows = await sqlserver_client.fetch_service_call_source_rows(connection_string, task.source_view)

    local_now = datetime.now(tz)
    creator_tag = f"Origen_Carga_Masiva - {local_now:%Y-%m-%d} - {trigger_type}"

    execution_id = await service_call_execution_repository.create_execution(
        task_id, trigger_type, dry_run, resolved_batch_size
    )

    items = []
    for sequence, row in enumerate(rows, start=1):
        payload = _build_payload(row, creator_tag)
        payload_json = json.dumps(payload)
        source_key = _compute_source_key(task.company_name, row, payload_json)
        items.append((sequence, source_key, payload))

    if items:
        await service_call_execution_repository.add_items(execution_id, items)

    return execution_id


async def continuar_carga(execution_id: int, task_id: int) -> None:
    task = await service_call_task_repository.get_task(task_id)
    if task is None:
        await service_call_execution_repository.finish_execution(
            execution_id, "failed", f"Tarea {task_id} no encontrada"
        )
        return

    execution = await service_call_execution_repository.get_execution(execution_id)
    if execution is None:
        return

    credentials = None
    if not execution.dry_run:
        credentials = await company_repository.get_credentials(task.company_id)
        if credentials is None:
            await service_call_execution_repository.finish_execution(
                execution_id, "failed", "La empresa no tiene credenciales de Service Layer activas"
            )
            return

    try:
        while True:
            pending = await service_call_execution_repository.get_pending_items(
                execution_id, execution.batch_size
            )
            if not pending:
                break

            await service_call_execution_repository.mark_items_processing([p["id"] for p in pending])

            try:
                if execution.dry_run:
                    results = [
                        service_layer_batch_client.BatchItemResult(
                            item_id=p["id"],
                            success=True,
                            http_status_code=200,
                            response_body="DRY RUN: el registro fue validado y no se envió a SAP.",
                        )
                        for p in pending
                    ]
                else:
                    batch_items = [(p["id"], json.dumps(p["payload_json"])) for p in pending]
                    results = await service_layer_batch_client.create_service_calls_batch(
                        credentials["service_layer_url"],
                        credentials["company_db"],
                        credentials["username"],
                        credentials["password"],
                        batch_items,
                    )

                results_by_id = {r.item_id: r for r in results}
                for p in pending:
                    result = results_by_id.get(p["id"])
                    if result is None:
                        await service_call_execution_repository.update_item_result(
                            p["id"], "needs_review", None, "SAP no devolvió un resultado para este elemento."
                        )
                        continue

                    status = (
                        "succeeded"
                        if result.success
                        else "needs_review"
                        if result.needs_review
                        else "failed"
                    )
                    await service_call_execution_repository.update_item_result(
                        p["id"], status, result.http_status_code, result.response_body
                    )
            except Exception as exc:
                logger.exception(
                    "[LLAMADAS] Error procesando lote de %s elementos para la ejecución %s",
                    len(pending),
                    execution_id,
                )
                for p in pending:
                    await service_call_execution_repository.update_item_result(
                        p["id"], "needs_review", None, str(exc)[:8000]
                    )

            await service_call_execution_repository.refresh_counts(execution_id)

        execution = await service_call_execution_repository.get_execution(execution_id)
        final_status = (
            "completed_with_errors"
            if execution.failed_items > 0 or execution.review_items > 0
            else "completed"
        )
        await service_call_execution_repository.finish_execution(execution_id, final_status)
    except Exception as exc:
        logger.exception("[LLAMADAS] Falló la ejecución %s", execution_id)
        await service_call_execution_repository.finish_execution(execution_id, "failed", str(exc)[:4000])

    await _enviar_resumen(task, execution_id)


async def cargar_tarea(
    task_id: int, trigger_type: str, *, batch_size: int | None = None, dry_run: bool = False
) -> int:
    execution_id = await iniciar_carga(task_id, trigger_type, batch_size=batch_size, dry_run=dry_run)
    await continuar_carga(execution_id, task_id)
    return execution_id


async def _enviar_resumen(task, execution_id: int) -> None:
    execution = await service_call_execution_repository.get_execution(execution_id)
    mail_config = await app_settings_repository.get_mail_config()
    if execution is None or not mail_config["mail_password"]:
        return

    body = (
        f"Resumen de la carga de llamadas de servicio:\n"
        f"Tarea: {task.name}\n"
        f"Filial: {task.company_name}\n"
        f"Estado: {execution.status}\n"
        f"Total: {execution.total_items}\n"
        f"Correctos: {execution.successful_items}\n"
        f"Fallidos: {execution.failed_items}\n"
        f"Requieren revisión: {execution.review_items}\n"
        f"Modo prueba (dry run): {'sí' if execution.dry_run else 'no'}\n"
        f"Iniciado: {execution.started_at}\n"
        f"Finalizado: {execution.finished_at}\n"
    )
    if execution.error_message:
        body += f"\nError: {execution.error_message}\n"

    def send_sync() -> None:
        message = EmailMessage()
        message["From"] = mail_config["mail_from"]
        message["To"] = task.mail_to
        if task.mail_cc:
            message["Cc"] = task.mail_cc
        message["Subject"] = f"Carga de llamadas de servicio - {task.name} - {execution.status}"
        message.set_content(body)

        recipients = [a.strip() for a in task.mail_to.replace(";", ",").split(",") if a.strip()]
        if task.mail_cc:
            recipients += [a.strip() for a in task.mail_cc.replace(";", ",").split(",") if a.strip()]

        with smtplib.SMTP(mail_config["smtp_server"], mail_config["smtp_port"]) as server:
            server.starttls()
            server.login(mail_config["mail_user"], mail_config["mail_password"])
            server.send_message(message, to_addrs=recipients)

    import asyncio

    try:
        await asyncio.to_thread(send_sync)
    except Exception:
        logger.exception("[LLAMADAS] No se pudo enviar el correo de resumen (ejecución %s)", execution_id)
