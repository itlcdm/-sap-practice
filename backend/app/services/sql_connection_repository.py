from app.config import settings as env_settings
from app.services.db_service import db_service


def _build_connection_string(conn: dict) -> str:
    extra = conn.get("extra_params") or ""
    return (
        f"DRIVER={{{conn['driver']}}};SERVER={conn['server']};DATABASE={conn['database']};"
        f"UID={conn['username']};PWD={conn['password']};{extra}"
    )


class SqlConnectionRepository:
    async def list_connections(self) -> list[dict]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, driver, server, database, username, extra_params,
                       created_at, updated_at, (password IS NOT NULL AND password != '') AS password_configured
                FROM sql_connections ORDER BY name
                """
            )
        return [dict(r) for r in rows]

    async def get_connection_by_id(self, connection_id: int) -> dict | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, driver, server, database, username, password, extra_params,
                       created_at, updated_at, (password IS NOT NULL AND password != '') AS password_configured
                FROM sql_connections WHERE id = $1
                """,
                connection_id,
            )
        return dict(row) if row else None

    async def get_connection_string(self, name: str) -> str | None:
        """Prioriza la conexión configurada en la base de datos; si no existe,
        recae en TASK_SQL_CONNECTIONS del .env (compatibilidad hacia atrás y
        entornos donde la base de datos aún no está conectada, p.ej. pruebas)."""
        if db_service.pool is not None:
            async with db_service.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT driver, server, database, username, password, extra_params "
                    "FROM sql_connections WHERE name = $1",
                    name,
                )
            if row is not None:
                return _build_connection_string(dict(row))
        return env_settings.task_sql_connections.get(name)

    async def create_connection(self, data) -> dict:
        async with db_service.pool.acquire() as conn:
            connection_id = await conn.fetchval(
                """
                INSERT INTO sql_connections (name, driver, server, database, username, password, extra_params)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                data.name,
                data.driver,
                data.server,
                data.database,
                data.username,
                data.password,
                data.extra_params,
            )
        return await self.get_connection_by_id(connection_id)

    async def update_connection(self, connection_id: int, data) -> dict | None:
        existing = await self.get_connection_by_id(connection_id)
        if existing is None:
            return None
        password = data.password if data.password else existing["password"]
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sql_connections
                SET driver = $2, server = $3, database = $4, username = $5,
                    password = $6, extra_params = $7, updated_at = now()
                WHERE id = $1
                """,
                connection_id,
                data.driver,
                data.server,
                data.database,
                data.username,
                password,
                data.extra_params,
            )
        return await self.get_connection_by_id(connection_id)

    async def delete_connection(self, connection_id: int) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute("DELETE FROM sql_connections WHERE id = $1", connection_id)


sql_connection_repository = SqlConnectionRepository()


def get_sql_connection_repository() -> SqlConnectionRepository:
    return sql_connection_repository
