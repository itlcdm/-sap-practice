from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.task_execution_service import ejecutar_tarea


class SchedulerService:

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)

    def schedule_task(self, task_id: int, cron_expression: str) -> None:
        self.scheduler.add_job(
            ejecutar_tarea,
            trigger=CronTrigger.from_crontab(cron_expression),
            args=[task_id, "scheduled"],
            id=f"task-{task_id}",
            replace_existing=True,
        )

    def unschedule_task(self, task_id: int) -> None:
        job = self.scheduler.get_job(f"task-{task_id}")
        if job is not None:
            job.remove()

    def get_next_run_time(self, task_id: int) -> datetime | None:
        job = self.scheduler.get_job(f"task-{task_id}")
        return job.next_run_time if job else None


scheduler_service = SchedulerService()


def get_scheduler_service() -> SchedulerService:
    return scheduler_service
