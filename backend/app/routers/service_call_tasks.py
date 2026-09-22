from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.schemas.service_call_executions import RunServiceCallTaskRequest, RunServiceCallTaskResponse
from app.schemas.service_call_tasks import (
    ServiceCallTaskCreate,
    ServiceCallTaskOut,
    ServiceCallTaskUpdate,
)
from app.services import sqlserver_client
from app.services.scheduler_service import SchedulerService, get_scheduler_service
from app.services.service_call_execution_service import TaskAlreadyRunningError, continuar_carga, iniciar_carga
from app.services.service_call_task_repository import (
    ServiceCallTaskRepository,
    service_call_task_repository,
)
from app.services.sql_connection_repository import sql_connection_repository

router = APIRouter(prefix="/api/service-call-tasks", tags=["Service Call Tasks"])


def get_service_call_task_repository() -> ServiceCallTaskRepository:
    return service_call_task_repository


@router.get("", response_model=list[ServiceCallTaskOut])
async def list_service_call_tasks(
    repo: ServiceCallTaskRepository = Depends(get_service_call_task_repository),
):
    return await repo.list_tasks()


@router.post("", response_model=ServiceCallTaskOut, status_code=201)
async def create_service_call_task(
    payload: ServiceCallTaskCreate,
    repo: ServiceCallTaskRepository = Depends(get_service_call_task_repository),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    task_id = await repo.create_task(payload)
    scheduler.schedule_service_call_task(
        task_id, payload.schedule_type, payload.run_days, payload.run_day_of_month, payload.run_at
    )
    return await repo.get_task(task_id)


@router.put("/{task_id}", response_model=ServiceCallTaskOut)
async def update_service_call_task(
    task_id: int,
    payload: ServiceCallTaskUpdate,
    repo: ServiceCallTaskRepository = Depends(get_service_call_task_repository),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    if await repo.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    await repo.update_task(task_id, payload)

    if payload.is_active:
        scheduler.schedule_service_call_task(
            task_id, payload.schedule_type, payload.run_days, payload.run_day_of_month, payload.run_at
        )
    else:
        scheduler.unschedule_service_call_task(task_id)

    return await repo.get_task(task_id)


@router.delete("/{task_id}", status_code=204)
async def delete_service_call_task(
    task_id: int,
    repo: ServiceCallTaskRepository = Depends(get_service_call_task_repository),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    if await repo.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    scheduler.unschedule_service_call_task(task_id)
    await repo.delete_task(task_id)


@router.get("/{task_id}/preview")
async def preview_service_call_task(
    task_id: int,
    repo: ServiceCallTaskRepository = Depends(get_service_call_task_repository),
):
    task = await repo.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    connection_string = await sql_connection_repository.get_connection_string(task.connection_name)
    if connection_string is None:
        raise HTTPException(
            status_code=400,
            detail=f"Conexión '{task.connection_name}' no configurada",
        )

    try:
        columns, rows, total_count = await sqlserver_client.fetch_view_rows(
            connection_string, task.source_view
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo consultar la vista '{task.source_view}': {exc}",
        ) from exc

    return {
        "columns": columns,
        "rows": [list(row) for row in rows],
        "total_count": total_count,
    }


@router.post("/{task_id}/run", response_model=RunServiceCallTaskResponse)
async def run_service_call_task(
    task_id: int,
    payload: RunServiceCallTaskRequest,
    background_tasks: BackgroundTasks,
    repo: ServiceCallTaskRepository = Depends(get_service_call_task_repository),
):
    if await repo.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    try:
        execution_id = await iniciar_carga(
            task_id, "manual", batch_size=payload.batch_size, dry_run=payload.dry_run
        )
    except TaskAlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    background_tasks.add_task(continuar_carga, execution_id, task_id)

    return RunServiceCallTaskResponse(execution_id=execution_id)
