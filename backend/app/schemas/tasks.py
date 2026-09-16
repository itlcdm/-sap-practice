from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


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
    cron_expression: str


class ScheduleOut(BaseModel):
    id: int
    task_id: int
    task_name: str
    cron_expression: str
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
