from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.schemas.tasks import RunTaskResponse, ScheduleIn, ScheduleOut, TaskCreate, TaskOut, TaskSummary, TaskUpdate
from app.services.scheduler_service import SchedulerService, get_scheduler_service
from app.services.task_execution_service import TaskAlreadyRunningError, continuar_ejecucion, iniciar_ejecucion
from app.services.task_repository import TaskRepository, get_task_repository

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskSummary])
async def list_tasks(repo: TaskRepository = Depends(get_task_repository)):
    return await repo.list_tasks()


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(payload: TaskCreate, repo: TaskRepository = Depends(get_task_repository)):
    task_id = await repo.create_task(payload)
    return await repo.get_task(task_id)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, repo: TaskRepository = Depends(get_task_repository)):
    task = await repo.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    repo: TaskRepository = Depends(get_task_repository),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    existing = await repo.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    await repo.update_task(task_id, payload)

    # El scheduler vive en memoria: sin esto una tarea desactivada seguiría
    # disparando (y enviando correo) hasta reiniciar el backend.
    if payload.is_active:
        schedule = await repo.get_schedule(task_id)
        if schedule is not None:
            scheduler.schedule_task(task_id, **schedule)
    else:
        scheduler.unschedule_task(task_id)

    return await repo.get_task(task_id)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    repo: TaskRepository = Depends(get_task_repository),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    existing = await repo.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    scheduler.unschedule_task(task_id)
    await repo.delete_task(task_id)


@router.post("/{task_id}/schedule", response_model=ScheduleOut)
async def create_schedule(
    task_id: int,
    payload: ScheduleIn,
    repo: TaskRepository = Depends(get_task_repository),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    task = await repo.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    payload.validar_tipo()
    await repo.upsert_schedule(
        task_id,
        payload.schedule_type,
        payload.scheduled_at,
        payload.cron_expression,
    )
    scheduler.schedule_task(
        task_id,
        payload.schedule_type,
        payload.scheduled_at,
        payload.cron_expression,
    )

    return ScheduleOut(
        id=task_id,
        task_id=task_id,
        task_name=task.name,
        schedule_type=payload.schedule_type,
        scheduled_at=payload.scheduled_at,
        cron_expression=payload.cron_expression,
        is_active=True,
        next_run_time=scheduler.get_next_run_time(task_id),
    )


@router.delete("/{task_id}/schedule", status_code=204)
async def delete_schedule(
    task_id: int,
    repo: TaskRepository = Depends(get_task_repository),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    await repo.delete_schedule(task_id)
    scheduler.unschedule_task(task_id)


@router.post("/{task_id}/run", response_model=RunTaskResponse)
async def run_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    repo: TaskRepository = Depends(get_task_repository),
):
    task = await repo.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    try:
        execution_id = await iniciar_ejecucion(task_id, "manual", repo=repo)
    except TaskAlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    background_tasks.add_task(continuar_ejecucion, execution_id, task_id, repo=repo)

    return RunTaskResponse(execution_id=execution_id)
