from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.companies import router as companies_router
from app.routers.currency_tasks import router as currency_tasks_router
from app.routers.executions import router as executions_router
from app.routers.inventory import router as inventory_router
from app.routers.items import router as items_router
from app.routers.service_call_executions import router as service_call_executions_router
from app.routers.service_call_tasks import router as service_call_tasks_router
from app.routers.settings import router as settings_router
from app.routers.tasks import router as tasks_router
from app.routers.warehouses import router as warehouses_router
from app.services.db_service import db_service
from app.services.scheduler_service import scheduler_service
from app.services.task_repository import task_repository
from app.services.currency_task_repository import currency_task_repository
from app.services.service_call_task_repository import service_call_task_repository
from app.services.service_call_execution_repository import service_call_execution_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_service.connect()

    # Al arrancar el proceso nada puede seguir realmente "running": cualquier
    # fila en ese estado quedó huérfana de un proceso anterior y, con el índice
    # único parcial idx_task_executions_one_running_per_task, bloquearía para
    # siempre toda nueva ejecución (manual o programada) de esa tarea.
    await task_repository.mark_stale_running_as_failed()

    schedules = await task_repository.list_active_schedules()
    for schedule in schedules:
        # Defensa en profundidad: una expresión cron inválida persistida antes
        # de que existiera el validador de ScheduleIn no debe tumbar el arranque
        # de toda la aplicación.
        try:
            scheduler_service.schedule_task(
                schedule["task_id"],
                schedule["schedule_type"],
                schedule["scheduled_at"],
                schedule["cron_expression"],
            )
        except Exception as exc:
            print(
                f"No se pudo programar la tarea {schedule['task_id']} "
                f"con la expresión cron '{schedule['cron_expression']}': {exc}"
            )
    currency_tasks = await currency_task_repository.list_active_task_configs()
    for currency_task in currency_tasks:
        scheduler_service.schedule_currency_task(currency_task["id"], currency_task["run_at"])

    # Mismo saneamiento que arriba, para las cargas de llamadas de servicio.
    await service_call_execution_repository.mark_stale_running_as_failed()

    service_call_tasks = await service_call_task_repository.list_tasks()
    for service_call_task in service_call_tasks:
        if not service_call_task.is_active:
            continue
        try:
            scheduler_service.schedule_service_call_task(
                service_call_task.id,
                service_call_task.schedule_type,
                service_call_task.run_days,
                service_call_task.run_day_of_month,
                service_call_task.run_at,
            )
        except Exception as exc:
            print(f"No se pudo programar la tarea de llamadas de servicio {service_call_task.id}: {exc}")

    scheduler_service.start()

    yield

    scheduler_service.shutdown()
    await db_service.disconnect()


app = FastAPI(
    title="SAP Practice API",
    version="1.0.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_origin_regex=r"https://.*\.devtunnels\.ms",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "SAP Practice API funcionando"
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok"
    }


app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(currency_tasks_router)
app.include_router(executions_router)
app.include_router(inventory_router)
app.include_router(items_router)
app.include_router(service_call_executions_router)
app.include_router(service_call_tasks_router)
app.include_router(settings_router)
app.include_router(tasks_router)
app.include_router(warehouses_router)