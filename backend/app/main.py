from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.executions import router as executions_router
from app.routers.inventory import router as inventory_router
from app.routers.items import router as items_router
from app.routers.tasks import router as tasks_router
from app.routers.warehouses import router as warehouses_router
from app.services.db_service import db_service
from app.services.scheduler_service import scheduler_service
from app.services.task_repository import task_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_service.connect()

    schedules = await task_repository.list_active_schedules()
    for schedule in schedules:
        # Defensa en profundidad: una expresión cron inválida persistida antes
        # de que existiera el validador de ScheduleIn no debe tumbar el arranque
        # de toda la aplicación.
        try:
            scheduler_service.schedule_task(schedule["task_id"], schedule["cron_expression"])
        except Exception as exc:
            print(
                f"No se pudo programar la tarea {schedule['task_id']} "
                f"con la expresión cron '{schedule['cron_expression']}': {exc}"
            )
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
app.include_router(executions_router)
app.include_router(inventory_router)
app.include_router(items_router)
app.include_router(tasks_router)
app.include_router(warehouses_router)