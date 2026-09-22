from fastapi import APIRouter, Depends, HTTPException

from app.schemas.currency_tasks import CurrencyExecutionOut, CurrencyTaskCreate, CurrencyTaskOut, CurrencyTaskUpdate
from app.services.currency_task_execution import execute_currency_task
from app.services.currency_task_repository import CurrencyTaskRepository, currency_task_repository
from app.services.scheduler_service import SchedulerService, get_scheduler_service

router = APIRouter(prefix="/api/currency-tasks", tags=["Currency Tasks"])


def get_currency_task_repository() -> CurrencyTaskRepository:
    return currency_task_repository


@router.get("", response_model=list[CurrencyTaskOut])
async def list_currency_tasks(repo: CurrencyTaskRepository = Depends(get_currency_task_repository)):
    return await repo.list_tasks()


@router.post("", response_model=CurrencyTaskOut, status_code=201)
async def create_currency_task(payload: CurrencyTaskCreate, repo: CurrencyTaskRepository = Depends(get_currency_task_repository), scheduler: SchedulerService = Depends(get_scheduler_service)):
    task_id = await repo.create_task(payload)
    scheduler.schedule_currency_task(task_id, payload.run_at)
    return await repo.get_task(task_id)


@router.put("/{task_id}", response_model=CurrencyTaskOut)
async def update_currency_task(task_id: int, payload: CurrencyTaskUpdate, repo: CurrencyTaskRepository = Depends(get_currency_task_repository), scheduler: SchedulerService = Depends(get_scheduler_service)):
    if await repo.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="Tarea de monedas no encontrada")
    await repo.update_task(task_id, payload)
    if payload.is_active:
        scheduler.schedule_currency_task(task_id, payload.run_at)
    else:
        scheduler.unschedule_currency_task(task_id)
    return await repo.get_task(task_id)


@router.delete("/{task_id}", status_code=204)
async def delete_currency_task(task_id: int, repo: CurrencyTaskRepository = Depends(get_currency_task_repository), scheduler: SchedulerService = Depends(get_scheduler_service)):
    if await repo.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="Tarea de monedas no encontrada")
    await repo.delete_task(task_id)
    scheduler.unschedule_currency_task(task_id)


@router.post("/{task_id}/run")
async def run_currency_task(task_id: int, repo: CurrencyTaskRepository = Depends(get_currency_task_repository)):
    if await repo.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="Tarea de monedas no encontrada")
    try:
        updated = await execute_currency_task(task_id, "manual")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo actualizar el cambio de moneda: {exc}") from exc
    return {"ok": True, "updated": updated}


@router.get("/executions")
async def list_currency_executions(
    status: str | None = None,
    repo: CurrencyTaskRepository = Depends(get_currency_task_repository),
):
    return await repo.list_executions(status)


@router.get("/executions/{execution_id}", response_model=CurrencyExecutionOut)
async def get_currency_execution(
    execution_id: int,
    repo: CurrencyTaskRepository = Depends(get_currency_task_repository),
):
    execution = await repo.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    return execution
