from app.schemas.tasks import TaskCreate, TaskOut, TaskReportOut, TaskSummary, TaskUpdate
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

    async def upsert_schedule(self, task_id: int, cron_expression: str) -> int:
        async with db_service.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM task_schedules WHERE task_id = $1",
                    task_id,
                )

                schedule_id = await conn.fetchval(
                    """
                    INSERT INTO task_schedules (task_id, cron_expression, is_active)
                    VALUES ($1, $2, TRUE)
                    RETURNING id
                    """,
                    task_id,
                    cron_expression,
                )

        return schedule_id

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
                SELECT s.task_id AS task_id, t.name AS task_name, s.cron_expression AS cron_expression
                FROM task_schedules s
                JOIN tasks t ON t.id = s.task_id
                WHERE s.is_active AND t.is_active
                """
            )

        return [dict(r) for r in rows]

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
