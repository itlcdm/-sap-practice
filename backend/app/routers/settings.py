from datetime import datetime

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings as env_settings
from app.schemas.settings import (
    AppSettingsOut,
    AppSettingsUpdate,
    AuthInfoOut,
    MailSettingsOut,
    MailSettingsUpdate,
    PostgresSettingsOut,
    TestEmailRequest,
)
from app.schemas.sql_connections import SqlConnectionCreate, SqlConnectionOut, SqlConnectionUpdate
from app.services.app_settings_repository import AppSettingsRepository, get_app_settings_repository
from app.services.mail_service import enviar_correo_con_adjuntos
from app.services.sql_connection_repository import SqlConnectionRepository, get_sql_connection_repository

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("/app", response_model=AppSettingsOut)
async def get_app_settings(repo: AppSettingsRepository = Depends(get_app_settings_repository)):
    return await repo.get_settings()


@router.put("/app", response_model=AppSettingsOut)
async def update_app_settings(
    payload: AppSettingsUpdate,
    repo: AppSettingsRepository = Depends(get_app_settings_repository),
):
    return await repo.update_settings(
        payload.timezone_offset_hours, payload.default_batch_size, payload.max_retry_attempts
    )


@router.get("/mail", response_model=MailSettingsOut)
async def get_mail_settings(repo: AppSettingsRepository = Depends(get_app_settings_repository)):
    config = await repo.get_mail_config()
    return MailSettingsOut(
        smtp_server=config["smtp_server"],
        smtp_port=config["smtp_port"],
        mail_user=config["mail_user"],
        mail_from=config["mail_from"],
        password_configured=bool(config["mail_password"]),
    )


@router.put("/mail", response_model=MailSettingsOut)
async def update_mail_settings(
    payload: MailSettingsUpdate,
    repo: AppSettingsRepository = Depends(get_app_settings_repository),
):
    await repo.update_mail_config(
        payload.smtp_server, payload.smtp_port, payload.mail_user, payload.mail_from, payload.mail_password
    )
    config = await repo.get_mail_config()
    return MailSettingsOut(
        smtp_server=config["smtp_server"],
        smtp_port=config["smtp_port"],
        mail_user=config["mail_user"],
        mail_from=config["mail_from"],
        password_configured=bool(config["mail_password"]),
    )


@router.post("/mail/test-email")
async def send_test_email(
    payload: TestEmailRequest, repo: AppSettingsRepository = Depends(get_app_settings_repository)
):
    config = await repo.get_mail_config()
    if not config["mail_password"]:
        raise HTTPException(status_code=400, detail="No hay credenciales de correo configuradas")
    try:
        await enviar_correo_con_adjuntos(
            payload.to,
            None,
            "Correo de prueba - SAP Practice",
            f"Este es un correo de prueba enviado desde Configuración el {datetime.now():%Y-%m-%d %H:%M}.",
            [],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo enviar el correo de prueba: {exc}") from exc
    return {"ok": True}


@router.get("/sql-connections", response_model=list[SqlConnectionOut])
async def list_sql_connections(repo: SqlConnectionRepository = Depends(get_sql_connection_repository)):
    return await repo.list_connections()


@router.post("/sql-connections", response_model=SqlConnectionOut, status_code=201)
async def create_sql_connection(
    payload: SqlConnectionCreate, repo: SqlConnectionRepository = Depends(get_sql_connection_repository)
):
    try:
        return await repo.create_connection(payload)
    except asyncpg.exceptions.UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail=f"Ya existe una conexión llamada '{payload.name}'") from exc


@router.put("/sql-connections/{connection_id}", response_model=SqlConnectionOut)
async def update_sql_connection(
    connection_id: int,
    payload: SqlConnectionUpdate,
    repo: SqlConnectionRepository = Depends(get_sql_connection_repository),
):
    result = await repo.update_connection(connection_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Conexión no encontrada")
    return result


@router.delete("/sql-connections/{connection_id}", status_code=204)
async def delete_sql_connection(
    connection_id: int, repo: SqlConnectionRepository = Depends(get_sql_connection_repository)
):
    if await repo.get_connection_by_id(connection_id) is None:
        raise HTTPException(status_code=404, detail="Conexión no encontrada")
    await repo.delete_connection(connection_id)


@router.get("/postgres", response_model=PostgresSettingsOut)
async def get_postgres_settings():
    return PostgresSettingsOut(
        host=env_settings.db_host,
        port=env_settings.db_port,
        database=env_settings.db_name,
        user=env_settings.db_user,
        password_configured=bool(env_settings.db_password),
    )


@router.get("/auth", response_model=AuthInfoOut)
async def get_auth_info():
    return AuthInfoOut(
        enabled=False,
        note=(
            "La autenticación en los endpoints está deshabilitada intencionalmente "
            "(decisión de diseño para este entorno)."
        ),
    )
