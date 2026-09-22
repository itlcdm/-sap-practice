from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

from app.services.task_execution_service import ejecutar_tarea
from app.services.task_repository import task_repository
from app.services.currency_task_execution import execute_currency_task
from app.services.service_call_execution_service import cargar_tarea as cargar_llamadas_servicio


async def _run_scheduled_task(task_id: int, schedule_type: str) -> None:
    await ejecutar_tarea(task_id, "scheduled")
    if schedule_type == "once":
        await task_repository.delete_schedule(task_id)


class SchedulerService:

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)

    def schedule_task(
        self,
        task_id: int,
        schedule_type: str,
        scheduled_at=None,
        cron_expression: str | None = None,
    ) -> None:
        trigger = (
            DateTrigger(run_date=scheduled_at)
            if schedule_type == "once"
            else CronTrigger.from_crontab(cron_expression)
        )
        self.scheduler.add_job(
            _run_scheduled_task,
            trigger=trigger,
            args=[task_id, schedule_type],
            id=f"task-{task_id}",
            replace_existing=True,
        )

    def unschedule_task(self, task_id: int) -> None:
        job = self.scheduler.get_job(f"task-{task_id}")
        if job is not None:
            job.remove()

    def schedule_currency_task(self, task_id: int, run_at) -> None:
        self.scheduler.add_job(
            execute_currency_task,
            trigger=CronTrigger(hour=run_at.hour, minute=run_at.minute),
            args=[task_id, "scheduled"],
            id=f"currency-task-{task_id}",
            replace_existing=True,
        )

    def unschedule_currency_task(self, task_id: int) -> None:
        job = self.scheduler.get_job(f"currency-task-{task_id}")
        if job is not None:
            job.remove()

    def schedule_service_call_task(
        self,
        task_id: int,
        schedule_type: str,
        run_days: list[str],
        run_day_of_month: int | None,
        run_at,
    ) -> None:
        if schedule_type == "monthly":
            trigger = CronTrigger(day=run_day_of_month, hour=run_at.hour, minute=run_at.minute)
        else:
            day_of_week = ",".join(run_days) if run_days else "mon,tue,wed,thu,fri,sat,sun"
            trigger = CronTrigger(day_of_week=day_of_week, hour=run_at.hour, minute=run_at.minute)

        self.scheduler.add_job(
            cargar_llamadas_servicio,
            trigger=trigger,
            args=[task_id, "scheduled"],
            id=f"service-call-task-{task_id}",
            replace_existing=True,
        )

    def unschedule_service_call_task(self, task_id: int) -> None:
        job = self.scheduler.get_job(f"service-call-task-{task_id}")
        if job is not None:
            job.remove()

    def get_next_run_time(self, task_id: int) -> datetime | None:
        job = self.scheduler.get_job(f"task-{task_id}")
        return job.next_run_time if job else None


scheduler_service = SchedulerService()


def get_scheduler_service() -> SchedulerService:
    return scheduler_service
