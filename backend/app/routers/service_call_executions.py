from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.schemas.service_call_executions import ServiceCallExecutionItemOut, ServiceCallExecutionOut
from app.services.app_settings_repository import app_settings_repository
from app.services.service_call_execution_repository import (
    ServiceCallExecutionRepository,
    get_service_call_execution_repository,
)
from app.services.service_call_execution_service import continuar_carga

router = APIRouter(prefix="/api/service-call-executions", tags=["Service Call Executions"])


@router.get("", response_model=list[ServiceCallExecutionOut])
async def list_service_call_executions(
    task_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    repo: ServiceCallExecutionRepository = Depends(get_service_call_execution_repository),
):
    return await repo.list_executions(task_id, limit, offset)


@router.get("/{execution_id}", response_model=ServiceCallExecutionOut)
async def get_service_call_execution(
    execution_id: int,
    repo: ServiceCallExecutionRepository = Depends(get_service_call_execution_repository),
):
    execution = await repo.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    return execution


@router.get("/{execution_id}/items")
async def list_service_call_execution_items(
    execution_id: int,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    repo: ServiceCallExecutionRepository = Depends(get_service_call_execution_repository),
):
    items, total = await repo.list_execution_items(execution_id, status, limit, offset)
    return {"items": items, "total": total}


@router.post("/{execution_id}/retry-failed", response_model=ServiceCallExecutionOut)
async def retry_failed_items(
    execution_id: int,
    background_tasks: BackgroundTasks,
    repo: ServiceCallExecutionRepository = Depends(get_service_call_execution_repository),
):
    execution = await repo.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    if execution.status == "running":
        raise HTTPException(status_code=409, detail="La ejecución ya está en curso")

    app_settings = await app_settings_repository.get_settings()
    requeued = await repo.requeue_failed_items(execution_id, app_settings["max_retry_attempts"])
    if requeued == 0:
        return execution

    await repo.reopen_execution(execution_id)
    background_tasks.add_task(continuar_carga, execution_id, execution.task_id)

    return await repo.get_execution(execution_id)
