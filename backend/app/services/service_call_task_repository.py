from app.schemas.service_call_tasks import (
    ServiceCallTaskCreate,
    ServiceCallTaskOut,
    ServiceCallTaskUpdate,
)
from app.services.db_service import db_service


class ServiceCallTaskRepository:
    async def list_tasks(self) -> list[ServiceCallTaskOut]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.id, t.name, t.company_id, c.name AS company_name,
                       t.connection_name, t.source_view, t.run_at,
                       t.schedule_type, t.run_days, t.run_day_of_month,
                       t.mail_to, t.mail_cc, t.is_active, t.created_at, t.updated_at
                FROM service_call_tasks t
                JOIN service_layer_companies c ON c.id = t.company_id
                ORDER BY t.name
                """
            )
        return [ServiceCallTaskOut(**dict(row)) for row in rows]

    async def get_task(self, task_id: int) -> ServiceCallTaskOut | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT t.id, t.name, t.company_id, c.name AS company_name,
                       t.connection_name, t.source_view, t.run_at,
                       t.schedule_type, t.run_days, t.run_day_of_month,
                       t.mail_to, t.mail_cc, t.is_active, t.created_at, t.updated_at
                FROM service_call_tasks t
                JOIN service_layer_companies c ON c.id = t.company_id
                WHERE t.id = $1
                """,
                task_id,
            )
        return ServiceCallTaskOut(**dict(row)) if row else None

    async def create_task(self, data: ServiceCallTaskCreate) -> int:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO service_call_tasks
                    (name, company_id, connection_name, source_view, run_at,
                     schedule_type, run_days, run_day_of_month, mail_to, mail_cc)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
                """,
                data.name,
                data.company_id,
                data.connection_name,
                data.source_view,
                data.run_at,
                data.schedule_type,
                data.run_days,
                data.run_day_of_month,
                data.mail_to,
                data.mail_cc,
            )

    async def update_task(self, task_id: int, data: ServiceCallTaskUpdate) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE service_call_tasks
                SET name = $2, company_id = $3, connection_name = $4, source_view = $5,
                    run_at = $6, schedule_type = $7, run_days = $8, run_day_of_month = $9,
                    mail_to = $10, mail_cc = $11, is_active = $12, updated_at = now()
                WHERE id = $1
                """,
                task_id,
                data.name,
                data.company_id,
                data.connection_name,
                data.source_view,
                data.run_at,
                data.schedule_type,
                data.run_days,
                data.run_day_of_month,
                data.mail_to,
                data.mail_cc,
                data.is_active,
            )

    async def delete_task(self, task_id: int) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute("DELETE FROM service_call_tasks WHERE id = $1", task_id)


service_call_task_repository = ServiceCallTaskRepository()
