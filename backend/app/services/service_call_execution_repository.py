import json

from app.schemas.service_call_executions import ServiceCallExecutionItemOut, ServiceCallExecutionOut
from app.services.db_service import db_service


class ServiceCallExecutionRepository:
    async def get_running_execution(self, task_id: int) -> int | None:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT id FROM service_call_executions WHERE task_id = $1 AND status = 'running' LIMIT 1",
                task_id,
            )

    async def create_execution(
        self, task_id: int, trigger_type: str, dry_run: bool, batch_size: int
    ) -> int:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO service_call_executions (task_id, trigger_type, dry_run, batch_size)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                task_id,
                trigger_type,
                dry_run,
                batch_size,
            )

    async def add_items(
        self, execution_id: int, items: list[tuple[int, str, dict]]
    ) -> None:
        """items: lista de (sequence, source_key, payload_dict)."""
        async with db_service.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO service_call_execution_items
                    (execution_id, sequence, source_key, payload_json)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                [
                    (execution_id, sequence, source_key, json.dumps(payload))
                    for sequence, source_key, payload in items
                ],
            )
            await conn.execute(
                "UPDATE service_call_executions SET total_items = $2 WHERE id = $1",
                execution_id,
                len(items),
            )

    async def get_pending_items(self, execution_id: int, limit: int) -> list[dict]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, sequence, source_key, payload_json
                FROM service_call_execution_items
                WHERE execution_id = $1 AND status = 'pending'
                ORDER BY sequence
                LIMIT $2
                """,
                execution_id,
                limit,
            )
        return [
            {
                "id": r["id"],
                "sequence": r["sequence"],
                "source_key": r["source_key"],
                "payload_json": json.loads(r["payload_json"]),
            }
            for r in rows
        ]

    async def mark_items_processing(self, item_ids: list[int]) -> None:
        if not item_ids:
            return
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE service_call_execution_items
                SET status = 'processing', attempt_count = attempt_count + 1
                WHERE id = ANY($1::bigint[])
                """,
                item_ids,
            )

    async def update_item_result(
        self,
        item_id: int,
        status: str,
        http_status_code: int | None,
        sap_response: str | None,
    ) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE service_call_execution_items
                SET status = $2, http_status_code = $3, sap_response = $4, processed_at = now()
                WHERE id = $1
                """,
                item_id,
                status,
                http_status_code,
                sap_response,
            )

    async def requeue_failed_items(self, execution_id: int, max_attempts: int) -> int:
        async with db_service.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE service_call_execution_items
                SET status = 'pending', http_status_code = NULL, sap_response = NULL, processed_at = NULL
                WHERE execution_id = $1 AND status IN ('failed', 'needs_review')
                      AND attempt_count < $2
                """,
                execution_id,
                max_attempts,
            )
        return int(result.split()[-1])

    async def refresh_counts(self, execution_id: int) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE service_call_executions e
                SET successful_items = (
                        SELECT count(*) FROM service_call_execution_items
                        WHERE execution_id = e.id AND status = 'succeeded'
                    ),
                    failed_items = (
                        SELECT count(*) FROM service_call_execution_items
                        WHERE execution_id = e.id AND status = 'failed'
                    ),
                    review_items = (
                        SELECT count(*) FROM service_call_execution_items
                        WHERE execution_id = e.id AND status = 'needs_review'
                    )
                WHERE e.id = $1
                """,
                execution_id,
            )

    async def reopen_execution(self, execution_id: int) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE service_call_executions
                SET status = 'running', error_message = NULL, finished_at = NULL
                WHERE id = $1
                """,
                execution_id,
            )

    async def finish_execution(
        self, execution_id: int, status: str, error_message: str | None = None
    ) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE service_call_executions
                SET status = $2, error_message = $3, finished_at = now()
                WHERE id = $1
                """,
                execution_id,
                status,
                error_message,
            )

    async def mark_stale_running_as_failed(self) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE service_call_executions
                SET status = 'failed',
                    error_message = 'Interrumpida por reinicio del servidor',
                    finished_at = now()
                WHERE status = 'running'
                """
            )

    async def list_executions(
        self, task_id: int | None, limit: int, offset: int
    ) -> list[ServiceCallExecutionOut]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT e.id, e.task_id, t.name AS task_name, e.trigger_type, e.status,
                       e.dry_run, e.batch_size, e.total_items, e.successful_items,
                       e.failed_items, e.review_items, e.error_message,
                       e.started_at, e.finished_at
                FROM service_call_executions e
                JOIN service_call_tasks t ON t.id = e.task_id
                WHERE ($1::bigint IS NULL OR e.task_id = $1)
                ORDER BY e.started_at DESC
                LIMIT $2 OFFSET $3
                """,
                task_id,
                limit,
                offset,
            )
        return [ServiceCallExecutionOut(**dict(r)) for r in rows]

    async def get_execution(self, execution_id: int) -> ServiceCallExecutionOut | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT e.id, e.task_id, t.name AS task_name, e.trigger_type, e.status,
                       e.dry_run, e.batch_size, e.total_items, e.successful_items,
                       e.failed_items, e.review_items, e.error_message,
                       e.started_at, e.finished_at
                FROM service_call_executions e
                JOIN service_call_tasks t ON t.id = e.task_id
                WHERE e.id = $1
                """,
                execution_id,
            )
        return ServiceCallExecutionOut(**dict(row)) if row else None

    async def list_execution_items(
        self, execution_id: int, status: str | None, limit: int, offset: int
    ) -> tuple[list[ServiceCallExecutionItemOut], int]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, sequence, source_key, payload_json, status,
                       attempt_count, http_status_code, sap_response, processed_at
                FROM service_call_execution_items
                WHERE execution_id = $1 AND ($2::text IS NULL OR status = $2)
                ORDER BY sequence
                LIMIT $3 OFFSET $4
                """,
                execution_id,
                status,
                limit,
                offset,
            )
            total = await conn.fetchval(
                """
                SELECT count(*) FROM service_call_execution_items
                WHERE execution_id = $1 AND ($2::text IS NULL OR status = $2)
                """,
                execution_id,
                status,
            )

        items = [
            ServiceCallExecutionItemOut(
                id=r["id"],
                sequence=r["sequence"],
                source_key=r["source_key"],
                payload_json=json.loads(r["payload_json"]),
                status=r["status"],
                attempt_count=r["attempt_count"],
                http_status_code=r["http_status_code"],
                sap_response=r["sap_response"],
                processed_at=r["processed_at"],
            )
            for r in rows
        ]
        return items, total


service_call_execution_repository = ServiceCallExecutionRepository()


def get_service_call_execution_repository() -> ServiceCallExecutionRepository:
    return service_call_execution_repository
