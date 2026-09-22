from app.schemas.currency_tasks import CurrencyTaskCreate, CurrencyTaskOut, CurrencyTaskUpdate
from app.services.db_service import db_service


class CurrencyTaskRepository:
    _select = """
        SELECT t.id, t.name, t.company_id, c.name AS company_name, c.company_db,
               t.local_currency, t.target_currencies, t.rate_api_url, t.run_at,
               t.mail_to, t.mail_cc, t.is_active, t.created_at, t.updated_at
        FROM currency_tasks t
        JOIN service_layer_companies c ON c.id = t.company_id
    """

    async def list_tasks(self) -> list[CurrencyTaskOut]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(self._select + " ORDER BY t.name")
        return [CurrencyTaskOut(**dict(row)) for row in rows]

    async def get_task(self, task_id: int) -> CurrencyTaskOut | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(self._select + " WHERE t.id = $1", task_id)
        return CurrencyTaskOut(**dict(row)) if row else None

    async def create_task(self, data: CurrencyTaskCreate) -> int:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO currency_tasks
                    (name, company_id, local_currency, target_currencies, rate_api_url,
                     run_at, mail_to, mail_cc)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                data.name, data.company_id, data.local_currency,
                data.target_currencies, data.rate_api_url, data.run_at,
                data.mail_to, data.mail_cc,
            )

    async def update_task(self, task_id: int, data: CurrencyTaskUpdate) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE currency_tasks
                SET name = $2, company_id = $3, local_currency = $4,
                    target_currencies = $5, rate_api_url = $6, run_at = $7,
                    mail_to = $8, mail_cc = $9, is_active = $10, updated_at = now()
                WHERE id = $1
                """,
                task_id, data.name, data.company_id, data.local_currency,
                data.target_currencies, data.rate_api_url, data.run_at,
                data.mail_to, data.mail_cc, data.is_active,
            )

    async def delete_task(self, task_id: int) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute("DELETE FROM currency_tasks WHERE id = $1", task_id)

    async def get_execution_config(self, task_id: int) -> dict | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT t.*, c.name AS company_name, c.company_db,
                       c.service_layer_url, c.username, c.password
                FROM currency_tasks t
                JOIN service_layer_companies c ON c.id = t.company_id
                WHERE t.id = $1 AND t.is_active AND c.is_active
                """,
                task_id,
            )
        return dict(row) if row else None

    async def list_active_task_configs(self) -> list[dict]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, run_at FROM currency_tasks WHERE is_active"
            )
        return [dict(row) for row in rows]

    async def create_execution(self, task_id: int, trigger_type: str) -> int:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                """INSERT INTO currency_task_executions (currency_task_id, trigger_type)
                   VALUES ($1, $2) RETURNING id""",
                task_id, trigger_type,
            )

    async def finish_execution(
        self, execution_id: int, status: str, error: str | None = None, updated_rates: list[str] | None = None
    ) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """UPDATE currency_task_executions
                   SET status = $2, error_message = $3, updated_rates = $4, finished_at = now()
                   WHERE id = $1""",
                execution_id, status, error, updated_rates or [],
            )

    async def get_execution(self, execution_id: int) -> dict | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT e.id, e.currency_task_id, t.name AS task_name,
                          c.name AS company_name, e.trigger_type, e.status,
                          e.started_at, e.finished_at, e.error_message, e.updated_rates
                   FROM currency_task_executions e
                   JOIN currency_tasks t ON t.id = e.currency_task_id
                   JOIN service_layer_companies c ON c.id = t.company_id
                   WHERE e.id = $1""",
                execution_id,
            )
        return dict(row) if row else None

    async def list_executions(self, status: str | None = None) -> list[dict]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT e.id, e.currency_task_id, t.name AS task_name,
                          c.name AS company_name, e.trigger_type, e.status,
                          e.started_at, e.finished_at, e.error_message, e.updated_rates
                   FROM currency_task_executions e
                   JOIN currency_tasks t ON t.id = e.currency_task_id
                   JOIN service_layer_companies c ON c.id = t.company_id
                   WHERE ($1::text IS NULL OR e.status = $1)
                   ORDER BY e.started_at DESC""",
                status,
            )
        return [dict(row) for row in rows]


currency_task_repository = CurrencyTaskRepository()
