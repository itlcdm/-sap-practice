from datetime import datetime
from typing import Literal

from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, field_validator, model_validator


class TaskReportIn(BaseModel):
    stored_procedure: str
    excel_file_name: str
    sheet_name: str


class TaskReportOut(TaskReportIn):
    id: int
    position: int


class TaskCreate(BaseModel):
    name: str
    description: str | None = None
    connection_name: str
    mail_to: str
    mail_cc: str | None = None
    mail_subject_template: str | None = None
    reports: list[TaskReportIn]

    @field_validator("reports")
    @classmethod
    def validar_reports_no_vacio(cls, value: list[TaskReportIn]) -> list[TaskReportIn]:
        if not value:
            raise ValueError("La tarea debe tener al menos un reporte")
        return value


class TaskUpdate(TaskCreate):
    is_active: bool = True


class TaskOut(BaseModel):
    id: int
    name: str
    description: str | None
    connection_name: str
    mail_to: str
    mail_cc: str | None
    mail_subject_template: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    reports: list[TaskReportOut]


class TaskSummary(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    has_schedule: bool


class ScheduleIn(BaseModel):
    schedule_type: Literal["once", "recurring"] = "recurring"
    scheduled_at: datetime | None = None
    cron_expression: str | None = None

    @field_validator("cron_expression")
    @classmethod
    def validar_cron_expression(cls, value: str | None) -> str | None:
        if value is None:
            return value
        # Se valida con el mismo parser que usa el scheduler
        # (SchedulerService.schedule_task), para que una expresión inválida
        # nunca llegue a persistirse en Postgres: pydantic convierte este
        # ValueError en un 422 antes de tocar el repositorio.
        try:
            CronTrigger.from_crontab(value)
        except ValueError as exc:
            raise ValueError(f"Expresión cron inválida ('{value}'): {exc}") from exc
        return value

    @field_validator("scheduled_at")
    @classmethod
    def validar_fecha_futura(cls, value: datetime | None) -> datetime | None:
        if value is not None and value <= datetime.now(value.tzinfo):
            raise ValueError("La fecha de ejecución debe estar en el futuro")
        return value

    @model_validator(mode="after")
    def validar_tipo(self):
        if self.schedule_type == "once" and self.scheduled_at is None:
            raise ValueError("Una ejecución única requiere una fecha")
        if self.schedule_type == "recurring" and not self.cron_expression:
            raise ValueError("Una ejecución recurrente requiere una expresión cron")
        return self


class ScheduleOut(BaseModel):
    id: int
    task_id: int
    task_name: str
    schedule_type: Literal["once", "recurring"]
    scheduled_at: datetime | None
    cron_expression: str | None
    is_active: bool
    next_run_time: datetime | None


class ExecutionOut(BaseModel):
    id: int
    task_id: int
    task_name: str
    trigger_type: Literal["manual", "scheduled"]
    status: Literal["running", "success", "failed"]
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None


class ExecutionReportOut(BaseModel):
    id: int
    stored_procedure: str
    file_name: str
    row_count: int | None


class ExecutionDetailOut(ExecutionOut):
    reports: list[ExecutionReportOut]


class ExecutionLogOut(BaseModel):
    id: int
    timestamp: datetime
    level: Literal["info", "warning", "error"]
    message: str


class RunTaskResponse(BaseModel):
    execution_id: int
