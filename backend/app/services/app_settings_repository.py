from app.config import settings as env_settings
from app.services.db_service import db_service


class AppSettingsRepository:
    async def get_settings(self) -> dict:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT timezone_offset_hours, default_batch_size, max_retry_attempts, updated_at "
                "FROM app_settings WHERE id = 1"
            )
        return dict(row)

    async def update_settings(
        self, timezone_offset_hours: int, default_batch_size: int, max_retry_attempts: int
    ) -> dict:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE app_settings
                SET timezone_offset_hours = $1, default_batch_size = $2,
                    max_retry_attempts = $3, updated_at = now()
                WHERE id = 1
                RETURNING timezone_offset_hours, default_batch_size, max_retry_attempts, updated_at
                """,
                timezone_offset_hours,
                default_batch_size,
                max_retry_attempts,
            )
        return dict(row)

    async def get_mail_config(self) -> dict:
        """Prioriza los overrides guardados en la base de datos; si un campo
        no fue configurado ahí (o la base todavía no está conectada, p.ej. en
        pruebas), recae en las variables de entorno MAIL_*."""
        overrides = {}
        if db_service.pool is not None:
            async with db_service.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT mail_smtp_server, mail_smtp_port, mail_user, mail_password, mail_from "
                    "FROM app_settings WHERE id = 1"
                )
            if row is not None:
                overrides = dict(row)

        return {
            "smtp_server": overrides.get("mail_smtp_server") or env_settings.mail_smtp_server,
            "smtp_port": overrides.get("mail_smtp_port") or env_settings.mail_smtp_port,
            "mail_user": overrides.get("mail_user") or env_settings.mail_user,
            "mail_password": overrides.get("mail_password") or env_settings.mail_password,
            "mail_from": overrides.get("mail_from") or env_settings.mail_from,
        }

    async def update_mail_config(
        self, smtp_server: str, smtp_port: int, mail_user: str, mail_from: str, mail_password: str | None
    ) -> None:
        async with db_service.pool.acquire() as conn:
            if mail_password:
                await conn.execute(
                    """
                    UPDATE app_settings
                    SET mail_smtp_server = $1, mail_smtp_port = $2, mail_user = $3,
                        mail_from = $4, mail_password = $5, updated_at = now()
                    WHERE id = 1
                    """,
                    smtp_server, smtp_port, mail_user, mail_from, mail_password,
                )
            else:
                await conn.execute(
                    """
                    UPDATE app_settings
                    SET mail_smtp_server = $1, mail_smtp_port = $2, mail_user = $3,
                        mail_from = $4, updated_at = now()
                    WHERE id = 1
                    """,
                    smtp_server, smtp_port, mail_user, mail_from,
                )


app_settings_repository = AppSettingsRepository()


def get_app_settings_repository() -> AppSettingsRepository:
    return app_settings_repository
