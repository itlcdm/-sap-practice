from datetime import datetime

from app.schemas.tasks import (
    ExecutionDetailOut,
    ExecutionLogOut,
    ExecutionOut,
    ExecutionReportOut,
    TaskCreate,
    TaskOut,
    TaskReportOut,
    TaskSummary,
    TaskUpdate,
)
from app.services.db_service import db_service


class TaskRepository:

    async def create_task(self, data: TaskCreate) -> int:
        async with db_service.pool.acquire() as conn:
            async with conn.transaction():
                task_id = await conn.fetchval(
                    """
                    INSERT INTO tasks (name, description, connection_name, mail_to, mail_cc, mail_subject_template)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                    """,
                    data.name,
                    data.description,
                    data.connection_name,
                    data.mail_to,
                    data.mail_cc,
                    data.mail_subject_template,
                )

                await self._insert_reports(conn, task_id, data.reports)

        return task_id

    async def get_task(self, task_id: int) -> TaskOut | None:
        async with db_service.pool.acquire() as conn:
            task_row = await conn.fetchrow(
                """
                SELECT id, name, description, connection_name, mail_to, mail_cc,
                       mail_subject_template, is_active, created_at, updated_at
                FROM tasks WHERE id = $1
                """,
                task_id,
            )

            if task_row is None:
                return None

            report_rows = await conn.fetch(
                """
                SELECT id, position, stored_procedure, excel_file_name, sheet_name
                FROM task_reports WHERE task_id = $1 ORDER BY position
                """,
                task_id,
            )

        return TaskOut(
            id=task_row["id"],
            name=task_row["name"],
            description=task_row["description"],
            connection_name=task_row["connection_name"],
            mail_to=task_row["mail_to"],
            mail_cc=task_row["mail_cc"],
            mail_subject_template=task_row["mail_subject_template"],
            is_active=task_row["is_active"],
            created_at=task_row["created_at"],
            updated_at=task_row["updated_at"],
            reports=[
                TaskReportOut(
                    id=r["id"],
                    position=r["position"],
                    stored_procedure=r["stored_procedure"],
                    excel_file_name=r["excel_file_name"],
                    sheet_name=r["sheet_name"],
                )
                for r in report_rows
            ],
        )

    async def list_tasks(self) -> list[TaskSummary]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.id, t.name, t.description, t.is_active,
                       EXISTS (
                           SELECT 1 FROM task_schedules s
                           WHERE s.task_id = t.id AND s.is_active
                       ) AS has_schedule
                FROM tasks t
                ORDER BY t.name
                """
            )

        return [
            TaskSummary(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                is_active=r["is_active"],
                has_schedule=r["has_schedule"],
            )
            for r in rows
        ]

    async def update_task(self, task_id: int, data: TaskUpdate) -> None:
        async with db_service.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE tasks
                    SET name = $2, description = $3, connection_name = $4,
                        mail_to = $5, mail_cc = $6, mail_subject_template = $7,
                        is_active = $8, updated_at = now()
                    WHERE id = $1
                    """,
                    task_id,
                    data.name,
                    data.description,
                    data.connection_name,
                    data.mail_to,
                    data.mail_cc,
                    data.mail_subject_template,
                    data.is_active,
                )

                await conn.execute(
                    "DELETE FROM task_reports WHERE task_id = $1",
                    task_id,
                )

                await self._insert_reports(conn, task_id, data.reports)

    async def delete_task(self, task_id: int) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute("DELETE FROM tasks WHERE id = $1", task_id)

    async def upsert_schedule(
        self,
        task_id: int,
        schedule_type: str,
        scheduled_at: datetime | None,
        cron_expression: str | None,
    ) -> int:
        async with db_service.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM task_schedules WHERE task_id = $1",
                    task_id,
                )

                schedule_id = await conn.fetchval(
                    """
                    INSERT INTO task_schedules (
                        task_id, schedule_type, scheduled_at, cron_expression, is_active
                    )
                    VALUES ($1, $2, $3, $4, TRUE)
                    RETURNING id
                    """,
                    task_id,
                    schedule_type,
                    scheduled_at,
                    cron_expression,
                )

        return schedule_id

    async def get_schedule(self, task_id: int) -> dict | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT schedule_type, scheduled_at, cron_expression
                FROM task_schedules WHERE task_id = $1 AND is_active
                """,
                task_id,
            )
        return dict(row) if row else None

    async def delete_schedule(self, task_id: int) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM task_schedules WHERE task_id = $1",
                task_id,
            )

    async def list_active_schedules(self) -> list[dict]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                  SELECT s.task_id AS task_id, t.name AS task_name,
                      s.schedule_type, s.scheduled_at, s.cron_expression
                FROM task_schedules s
                JOIN tasks t ON t.id = s.task_id
                WHERE s.is_active AND t.is_active
                """
            )

        return [dict(r) for r in rows]

    async def create_execution(self, task_id: int, trigger_type: str) -> int:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO task_executions (task_id, trigger_type, status)
                VALUES ($1, $2, 'running')
                RETURNING id
                """,
                task_id,
                trigger_type,
            )

    async def get_running_execution(self, task_id: int) -> int | None:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT id FROM task_executions WHERE task_id = $1 AND status = 'running' LIMIT 1",
                task_id,
            )

    async def mark_stale_running_as_failed(self) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE task_executions
                SET status = 'failed',
                    error_message = 'Interrumpida por reinicio del servidor',
                    finished_at = now()
                WHERE status = 'running'
                """
            )

    async def finish_execution(self, execution_id: int, status: str, error_message: str | None) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE task_executions
                SET status = $2, error_message = $3, finished_at = now()
                WHERE id = $1
                """,
                execution_id,
                status,
                error_message,
            )

    async def add_execution_report(
        self, execution_id: int, stored_procedure: str, file_name: str, file_path: str, row_count: int
    ) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO execution_reports (execution_id, stored_procedure, file_name, file_path, row_count)
                VALUES ($1, $2, $3, $4, $5)
                """,
                execution_id,
                stored_procedure,
                file_name,
                file_path,
                row_count,
            )

    async def add_execution_log(self, execution_id: int, level: str, message: str) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO execution_logs (execution_id, level, message) VALUES ($1, $2, $3)",
                execution_id,
                level,
                message,
            )

    async def list_executions(self, status: str | None, limit: int, offset: int) -> list[ExecutionOut]:
        status_filter = "history" if status == "history" else status

        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT e.id, e.task_id, t.name AS task_name, e.trigger_type, e.status,
                       e.started_at, e.finished_at, e.error_message
                FROM task_executions e
                JOIN tasks t ON t.id = e.task_id
                WHERE (
                    $1::text IS NULL
                    OR ($1::text = 'history' AND e.status IN ('success', 'failed'))
                    OR ($1::text <> 'history' AND e.status = $1)
                )
                ORDER BY e.started_at DESC
                LIMIT $2 OFFSET $3
                """,
                status_filter,
                limit,
                offset,
            )

        return [ExecutionOut(**dict(r)) for r in rows]

    async def get_execution(self, execution_id: int) -> ExecutionDetailOut | None:
        async with db_service.pool.acquire() as conn:
            execution_row = await conn.fetchrow(
                """
                SELECT e.id, e.task_id, t.name AS task_name, e.trigger_type, e.status,
                       e.started_at, e.finished_at, e.error_message
                FROM task_executions e
                JOIN tasks t ON t.id = e.task_id
                WHERE e.id = $1
                """,
                execution_id,
            )

            if execution_row is None:
                return None

            report_rows = await conn.fetch(
                """
                SELECT id, stored_procedure, file_name, row_count
                FROM execution_reports WHERE execution_id = $1 ORDER BY id
                """,
                execution_id,
            )

        return ExecutionDetailOut(
            **dict(execution_row),
            reports=[ExecutionReportOut(**dict(r)) for r in report_rows],
        )

    async def list_execution_logs(self, execution_id: int) -> list[ExecutionLogOut]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, timestamp, level, message
                FROM execution_logs WHERE execution_id = $1 ORDER BY timestamp
                """,
                execution_id,
            )

        return [ExecutionLogOut(**dict(r)) for r in rows]

    async def get_execution_report(self, execution_id: int, report_id: int) -> dict | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, file_name, file_path
                FROM execution_reports WHERE execution_id = $1 AND id = $2
                """,
                execution_id,
                report_id,
            )

        return dict(row) if row else None

    @staticmethod
    async def _insert_reports(conn, task_id: int, reports) -> None:
        for position, report in enumerate(reports):
            await conn.execute(
                """
                INSERT INTO task_reports (task_id, position, stored_procedure, excel_file_name, sheet_name)
                VALUES ($1, $2, $3, $4, $5)
                """,
                task_id,
                position,
                report.stored_procedure,
                report.excel_file_name,
                report.sheet_name,
            )


task_repository = TaskRepository()


def get_task_repository() -> TaskRepository:
    return task_repository
