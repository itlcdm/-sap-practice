from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.schemas.tasks import ExecutionDetailOut, ExecutionLogOut, ExecutionOut, ScheduleOut
from app.services.scheduler_service import SchedulerService, get_scheduler_service
from app.services.task_repository import TaskRepository, get_task_repository

router = APIRouter(prefix="/api", tags=["Executions"])


@router.get("/schedules", response_model=list[ScheduleOut])
async def list_schedules(
    repo: TaskRepository = Depends(get_task_repository),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    schedules = await repo.list_active_schedules()

    return [
        ScheduleOut(
            id=s["task_id"],
            task_id=s["task_id"],
            task_name=s["task_name"],
            schedule_type=s["schedule_type"],
            scheduled_at=s["scheduled_at"],
            cron_expression=s["cron_expression"],
            is_active=True,
            next_run_time=scheduler.get_next_run_time(s["task_id"]),
        )
        for s in schedules
    ]


@router.get("/executions", response_model=list[ExecutionOut])
async def list_executions(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    repo: TaskRepository = Depends(get_task_repository),
):
    return await repo.list_executions(status, limit, offset)


@router.get("/executions/{execution_id}", response_model=ExecutionDetailOut)
async def get_execution(execution_id: int, repo: TaskRepository = Depends(get_task_repository)):
    execution = await repo.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    return execution


@router.get("/executions/{execution_id}/logs", response_model=list[ExecutionLogOut])
async def get_execution_logs(execution_id: int, repo: TaskRepository = Depends(get_task_repository)):
    return await repo.list_execution_logs(execution_id)


@router.get("/executions/{execution_id}/reports/{report_id}/download")
async def download_execution_report(
    execution_id: int, report_id: int, repo: TaskRepository = Depends(get_task_repository)
):
    report = await repo.get_execution_report(execution_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # La fila puede apuntar a un archivo ya borrado o movido: sin esto
    # FileResponse falla con un 500 crudo en vez de un 404 limpio.
    if not Path(report["file_path"]).is_file():
        raise HTTPException(status_code=404, detail="Archivo no disponible en disco")

    return FileResponse(
        path=report["file_path"],
        filename=report["file_name"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
