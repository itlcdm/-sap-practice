# Motor de tareas (Backend) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el motor de tareas programadas del backend: modelo de datos en Postgres, ejecución (SQL Server → Excel → correo), programación por cron con APScheduler, y la API REST completa que consumirán las pantallas ya existentes en el frontend.

**Architecture:** Capas separadas y testeables de forma aislada: `TaskRepository` (acceso a Postgres vía `asyncpg`, mismo pool que `db_service`), `sqlserver_client`/`excel_export`/`mail_service` (integraciones externas, cada una mockeable), `task_execution_service` (orquestación, inyecta las anteriores por parámetro), `scheduler_service` (wrapper de APScheduler), y dos routers FastAPI (`tasks`, `executions`) que exponen todo vía HTTP usando `Depends` para poder sobreescribir dependencias en tests.

**Tech Stack:** FastAPI, asyncpg (ya en uso), pyodbc, openpyxl, APScheduler, pytest + pytest-asyncio, smtplib (stdlib).

**Spec:** `docs/superpowers/specs/2026-09-16-task-engine-design.md`

## Global Constraints

- Las contraseñas (SQL Server, SMTP) viven solo en `backend/.env`, nunca en la tabla `tasks` ni en respuestas de la API.
- `TASK_SQL_CONNECTIONS` es un JSON `{nombre: connection_string}`; la connection string debe estar en formato pyodbc (`DRIVER={ODBC Driver 17 for SQL Server};...`), no en formato ADO.NET.
- Si una tarea ya tiene una ejecución `running`, un nuevo disparo (manual o programado) debe fallar con un error claro, nunca correr en paralelo.
- Si cualquier reporte de una tarea falla, se aborta el resto de reportes y **no** se envía correo; la ejecución completa queda `failed`.
- Nombre de archivo de cada Excel generado: `{excel_file_name_sin_extension}_{execution_id}.xlsx` (el `execution_id` garantiza unicidad).
- Ningún endpoint nuevo requiere autenticación (igual que `items`/`warehouses`/`inventory` existentes — la app no tiene auth real de backend todavía).
- Todas las consultas a Postgres usan `asyncpg` parametrizado (`$1`, `$2`, ...), nunca f-strings con datos de entrada.

---

## Task 1: Herramientas de test y dependencias nuevas

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/tests/test_smoke.py`

**Interfaces:**
- Produces: entorno de test (`pytest`) funcionando desde `backend/`, y las libs `pyodbc`, `openpyxl`, `apscheduler` instaladas para las tareas siguientes.

- [ ] **Step 1: Agregar las dependencias nuevas a `requirements.txt`**

Añadir al final de `backend/requirements.txt`:

```
apscheduler==3.10.4
openpyxl==3.1.5
pyodbc==5.2.0
pytest==8.3.4
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Instalar dependencias**

Run: `cd backend && .venv\Scripts\python.exe -m pip install -r requirements.txt`
Expected: instala sin errores (si `pyodbc` falla por falta de compilador/driver en la máquina, anotarlo y continuar — no bloquea el resto del plan, que se puede seguir escribiendo/testeando con `pyodbc.connect` mockeado).

- [ ] **Step 3: Configurar pytest**

Crear `backend/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
```

- [ ] **Step 4: Escribir un test smoke que falle antes de existir nada**

Crear `backend/tests/test_smoke.py`:

```python
def test_smoke():
    assert 1 + 1 == 2
```

- [ ] **Step 5: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest -v`
Expected: `1 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/pytest.ini backend/tests/test_smoke.py
git commit -m "test: set up pytest for backend"
```

(Si el directorio no tiene `git` inicializado, omitir el commit y continuar — el resto de tareas también terminan en un paso de commit que se puede saltar de la misma forma.)

---

## Task 2: Script SQL del esquema de tareas

**Files:**
- Create: `backend/sql/002_tasks_schema.sql`
- Create: `backend/tests/test_sql_schema.py`

**Interfaces:**
- Produces: el archivo `.sql` que se debe correr manualmente contra la base Postgres de la app (mismo patrón que las SP ya existentes, administradas a mano).

- [ ] **Step 1: Escribir el test que verifica el contenido del script**

Crear `backend/tests/test_sql_schema.py`:

```python
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent / "sql" / "002_tasks_schema.sql"


def test_schema_file_exists():
    assert SCHEMA_PATH.exists()


def test_schema_defines_expected_tables():
    content = SCHEMA_PATH.read_text(encoding="utf-8")

    for table in [
        "tasks",
        "task_reports",
        "task_schedules",
        "task_executions",
        "execution_reports",
        "execution_logs",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in content


def test_schema_has_foreign_keys_to_tasks():
    content = SCHEMA_PATH.read_text(encoding="utf-8")

    assert "REFERENCES tasks(id) ON DELETE CASCADE" in content
    assert "REFERENCES task_executions(id) ON DELETE CASCADE" in content
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_sql_schema.py -v`
Expected: FAIL (`sql/002_tasks_schema.sql` no existe)

- [ ] **Step 3: Crear el script SQL**

Crear `backend/sql/002_tasks_schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    connection_name TEXT NOT NULL,
    mail_to TEXT NOT NULL,
    mail_cc TEXT,
    mail_subject_template TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS task_reports (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    stored_procedure TEXT NOT NULL,
    excel_file_name TEXT NOT NULL,
    sheet_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_schedules (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    cron_expression TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS task_executions (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('manual', 'scheduled')),
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')) DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS execution_reports (
    id BIGSERIAL PRIMARY KEY,
    execution_id BIGINT NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    stored_procedure TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    row_count INTEGER
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id BIGSERIAL PRIMARY KEY,
    execution_id BIGINT NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now(),
    level TEXT NOT NULL CHECK (level IN ('info', 'warning', 'error')) DEFAULT 'info',
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_task_reports_task_id ON task_reports(task_id);
CREATE INDEX IF NOT EXISTS idx_task_schedules_task_id ON task_schedules(task_id);
CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON task_executions(task_id);
CREATE INDEX IF NOT EXISTS idx_task_executions_status ON task_executions(status);
CREATE INDEX IF NOT EXISTS idx_execution_reports_execution_id ON execution_reports(execution_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_execution_id ON execution_logs(execution_id);
```

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_sql_schema.py -v`
Expected: `3 passed`

- [ ] **Step 5: Verificación manual (no automatizable sin una BD real)**

Correr el script una vez contra la Postgres configurada en `backend/.env` (`DB_HOST`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`), por ejemplo con `psql` o cualquier cliente SQL. Confirmar que las 6 tablas quedan creadas sin error.

- [ ] **Step 6: Commit**

```bash
git add backend/sql/002_tasks_schema.sql backend/tests/test_sql_schema.py
git commit -m "feat: add task engine database schema"
```

---

## Task 3: Configuración (`app/config.py`)

**Files:**
- Modify: `backend/app/config.py`
- Create: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `Settings.task_sql_connections: dict[str, str]`, `Settings.task_output_folder: str`, `Settings.mail_from/mail_smtp_server/mail_smtp_port/mail_user/mail_password: str/int`.

- [ ] **Step 1: Escribir el test (falla porque los campos no existen)**

Crear `backend/tests/test_config.py`:

```python
from app.config import Settings

BASE_KWARGS = dict(
    sap_url="https://sap.example.com",
    sap_company_db="TEST",
    sap_username="user",
    sap_password="pass",
    admin_email="admin@example.com",
    admin_password="pass",
    db_host="localhost",
    db_name="test",
    db_user="test",
    db_password="test",
    mail_from="info@example.com",
    mail_smtp_server="smtp.example.com",
    mail_user="info@example.com",
    mail_password="pass",
)


def test_task_sql_connections_parses_json_from_env(monkeypatch):
    monkeypatch.setenv(
        "TASK_SQL_CONNECTIONS",
        '{"InventarioDb": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=x;"}',
    )

    settings = Settings(_env_file=None, **BASE_KWARGS)

    assert settings.task_sql_connections == {
        "InventarioDb": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=x;"
    }


def test_task_output_folder_defaults_to_output(monkeypatch):
    monkeypatch.delenv("TASK_OUTPUT_FOLDER", raising=False)

    settings = Settings(_env_file=None, **BASE_KWARGS)

    assert settings.task_output_folder == "output"


def test_mail_smtp_port_defaults_to_587(monkeypatch):
    monkeypatch.delenv("MAIL_SMTP_PORT", raising=False)

    settings = Settings(_env_file=None, **BASE_KWARGS)

    assert settings.mail_smtp_port == 587
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: FAIL (`Settings` no acepta `mail_from`, etc.)

- [ ] **Step 3: Extender `Settings`**

En `backend/app/config.py`, agregar los campos nuevos a la clase `Settings` (después de `db_password: str`):

```python
    task_sql_connections: dict[str, str] = {}
    task_output_folder: str = "output"

    mail_from: str
    mail_smtp_server: str
    mail_smtp_port: int = 587
    mail_user: str
    mail_password: str
```

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: `3 passed`

- [ ] **Step 5: Actualizar el `.env` real del proyecto**

Agregar a `backend/.env` (no se versiona en el plan por seguridad, pero es un paso obligatorio para poder levantar el backend):

```
TASK_SQL_CONNECTIONS={"InventarioDb": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.249.249.172;DATABASE=Inventario;UID=LuceeServer;PWD=<password real>;TrustServerCertificate=yes;"}
TASK_OUTPUT_FOLDER=C:\output

MAIL_FROM=info@casamedic.com.pa
MAIL_SMTP_SERVER=smtp.office365.com
MAIL_SMTP_PORT=587
MAIL_USER=info@casamedic.com.pa
MAIL_PASSWORD=<password real>
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat: add task engine settings (sql connections, output folder, mail)"
```

---

## Task 4: Esquemas Pydantic (`app/schemas/tasks.py`)

**Files:**
- Create: `backend/app/schemas/tasks.py`
- Create: `backend/tests/test_schemas_tasks.py`

**Interfaces:**
- Produces: `TaskReportIn`, `TaskReportOut`, `TaskCreate`, `TaskUpdate`, `TaskOut`, `TaskSummary`, `ScheduleIn`, `ScheduleOut`, `ExecutionOut`, `ExecutionReportOut`, `ExecutionDetailOut`, `ExecutionLogOut`, `RunTaskResponse` — usados por `task_repository`, `task_execution_service` y los routers en tareas siguientes.

- [ ] **Step 1: Escribir el test**

Crear `backend/tests/test_schemas_tasks.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.tasks import TaskCreate, TaskReportIn


def _report(sp="ALCONSIT"):
    return TaskReportIn(
        stored_procedure=sp,
        excel_file_name="ALCONSIT.xlsx",
        sheet_name="ALCONSIT",
    )


def test_task_create_accepts_one_or_more_reports():
    task = TaskCreate(
        name="Inventario diario",
        connection_name="InventarioDb",
        mail_to="a@example.com",
        reports=[_report("ALCONSIT"), _report("ALCONIMS")],
    )

    assert len(task.reports) == 2


def test_task_create_rejects_empty_reports():
    with pytest.raises(ValidationError):
        TaskCreate(
            name="Inventario diario",
            connection_name="InventarioDb",
            mail_to="a@example.com",
            reports=[],
        )
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_schemas_tasks.py -v`
Expected: FAIL (`app.schemas.tasks` no existe)

- [ ] **Step 3: Crear los esquemas**

Crear `backend/app/schemas/tasks.py`:

```python
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
```

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_schemas_tasks.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/tasks.py backend/tests/test_schemas_tasks.py
git commit -m "feat: add pydantic schemas for tasks/schedules/executions"
```

---

## Task 5: `TaskRepository` — tareas y reportes

**Files:**
- Create: `backend/app/services/task_repository.py`
- Create: `backend/tests/services/test_task_repository.py`

**Interfaces:**
- Consumes: `TaskCreate`, `TaskUpdate`, `TaskOut`, `TaskReportOut`, `TaskSummary` (Task 4); `db_service.pool` (`app/services/db_service.py`, ya existente).
- Produces: clase `TaskRepository` con `create_task`, `get_task`, `list_tasks`, `update_task`; singleton `task_repository`; `get_task_repository()` (dependency provider para FastAPI).

- [ ] **Step 1: Escribir los fakes de test y el primer test (falla)**

Crear `backend/tests/services/test_task_repository.py`:

```python
from app.schemas.tasks import TaskCreate, TaskReportIn, TaskUpdate
from app.services import db_service as db_service_module
from app.services.task_repository import TaskRepository


class _NoOpTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConnection:
    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []
        self.fetchval_results: list = []
        self.fetchrow_results: list = []
        self.fetch_results: list = []

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchval(self, query, *args):
        self.executed.append((query, args))
        return self.fetchval_results.pop(0) if self.fetchval_results else None

    async def fetchrow(self, query, *args):
        self.executed.append((query, args))
        return self.fetchrow_results.pop(0) if self.fetchrow_results else None

    async def fetch(self, query, *args):
        self.executed.append((query, args))
        return self.fetch_results.pop(0) if self.fetch_results else []

    def transaction(self):
        return _NoOpTransaction()


class FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return FakeAcquire(self._conn)


def use_fake_pool(monkeypatch) -> FakeConnection:
    conn = FakeConnection()
    monkeypatch.setattr(db_service_module.db_service, "pool", FakePool(conn))
    return conn


async def test_create_task_inserts_task_and_reports(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchval_results = [7]

    repo = TaskRepository()
    task_id = await repo.create_task(
        TaskCreate(
            name="Inventario diario",
            connection_name="InventarioDb",
            mail_to="a@example.com",
            reports=[
                TaskReportIn(
                    stored_procedure="ALCONSIT",
                    excel_file_name="ALCONSIT.xlsx",
                    sheet_name="ALCONSIT",
                ),
                TaskReportIn(
                    stored_procedure="ALCONIMS",
                    excel_file_name="ALCONIMS.xlsx",
                    sheet_name="ALCONIMS",
                ),
            ],
        )
    )

    assert task_id == 7

    insert_task_calls = [c for c in conn.executed if "INSERT INTO tasks" in c[0]]
    insert_report_calls = [c for c in conn.executed if "INSERT INTO task_reports" in c[0]]
    assert len(insert_task_calls) == 0  # el INSERT de tasks usa fetchval, no execute
    assert len(insert_report_calls) == 2
    assert insert_report_calls[0][1][1] == 0  # position del primer reporte
    assert insert_report_calls[1][1][1] == 1  # position del segundo reporte
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_task_repository.py -v`
Expected: FAIL (`app.services.task_repository` no existe)

- [ ] **Step 3: Implementar `create_task`, `get_task`, `list_tasks`, `update_task`**

Crear `backend/app/services/task_repository.py`:

```python
from app.schemas.tasks import TaskCreate, TaskOut, TaskReportOut, TaskSummary, TaskUpdate
from app.services.db_service import db_service


class TaskRepository:

    async def create_task(self, data: TaskCreate) -> int:
        async with db_service.pool.acquire() as conn:
            async with conn.transaction():
                task_id = await conn.fetchval(
                    """
                    INSERT INTO tasks (name, description, connection_name, mail_to, mail_cc, mail_subject_template)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                    """,
                    data.name,
                    data.description,
                    data.connection_name,
                    data.mail_to,
                    data.mail_cc,
                    data.mail_subject_template,
                )

                await self._insert_reports(conn, task_id, data.reports)

        return task_id

    async def get_task(self, task_id: int) -> TaskOut | None:
        async with db_service.pool.acquire() as conn:
            task_row = await conn.fetchrow(
                """
                SELECT id, name, description, connection_name, mail_to, mail_cc,
                       mail_subject_template, is_active, created_at, updated_at
                FROM tasks WHERE id = $1
                """,
                task_id,
            )

            if task_row is None:
                return None

            report_rows = await conn.fetch(
                """
                SELECT id, position, stored_procedure, excel_file_name, sheet_name
                FROM task_reports WHERE task_id = $1 ORDER BY position
                """,
                task_id,
            )

        return TaskOut(
            id=task_row["id"],
            name=task_row["name"],
            description=task_row["description"],
            connection_name=task_row["connection_name"],
            mail_to=task_row["mail_to"],
            mail_cc=task_row["mail_cc"],
            mail_subject_template=task_row["mail_subject_template"],
            is_active=task_row["is_active"],
            created_at=task_row["created_at"],
            updated_at=task_row["updated_at"],
            reports=[
                TaskReportOut(
                    id=r["id"],
                    position=r["position"],
                    stored_procedure=r["stored_procedure"],
                    excel_file_name=r["excel_file_name"],
                    sheet_name=r["sheet_name"],
                )
                for r in report_rows
            ],
        )

    async def list_tasks(self) -> list[TaskSummary]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.id, t.name, t.description, t.is_active,
                       EXISTS (
                           SELECT 1 FROM task_schedules s
                           WHERE s.task_id = t.id AND s.is_active
                       ) AS has_schedule
                FROM tasks t
                ORDER BY t.name
                """
            )

        return [
            TaskSummary(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                is_active=r["is_active"],
                has_schedule=r["has_schedule"],
            )
            for r in rows
        ]

    async def update_task(self, task_id: int, data: TaskUpdate) -> None:
        async with db_service.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE tasks
                    SET name = $2, description = $3, connection_name = $4,
                        mail_to = $5, mail_cc = $6, mail_subject_template = $7,
                        is_active = $8, updated_at = now()
                    WHERE id = $1
                    """,
                    task_id,
                    data.name,
                    data.description,
                    data.connection_name,
                    data.mail_to,
                    data.mail_cc,
                    data.mail_subject_template,
                    data.is_active,
                )

                await conn.execute(
                    "DELETE FROM task_reports WHERE task_id = $1",
                    task_id,
                )

                await self._insert_reports(conn, task_id, data.reports)

    @staticmethod
    async def _insert_reports(conn, task_id: int, reports) -> None:
        for position, report in enumerate(reports):
            await conn.execute(
                """
                INSERT INTO task_reports (task_id, position, stored_procedure, excel_file_name, sheet_name)
                VALUES ($1, $2, $3, $4, $5)
                """,
                task_id,
                position,
                report.stored_procedure,
                report.excel_file_name,
                report.sheet_name,
            )


task_repository = TaskRepository()


def get_task_repository() -> TaskRepository:
    return task_repository
```

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_task_repository.py -v`
Expected: `1 passed`

- [ ] **Step 5: Agregar tests para `get_task`, `list_tasks` y `update_task`, y correrlos**

Añadir al mismo archivo de test:

```python
async def test_get_task_returns_none_when_missing(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [None]

    repo = TaskRepository()
    result = await repo.get_task(999)

    assert result is None


async def test_get_task_returns_task_with_reports(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [
        {
            "id": 1,
            "name": "Inventario diario",
            "description": None,
            "connection_name": "InventarioDb",
            "mail_to": "a@example.com",
            "mail_cc": None,
            "mail_subject_template": None,
            "is_active": True,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    conn.fetch_results = [
        [
            {
                "id": 10,
                "position": 0,
                "stored_procedure": "ALCONSIT",
                "excel_file_name": "ALCONSIT.xlsx",
                "sheet_name": "ALCONSIT",
            }
        ]
    ]

    repo = TaskRepository()
    task = await repo.get_task(1)

    assert task.id == 1
    assert task.reports[0].stored_procedure == "ALCONSIT"


async def test_list_tasks_maps_rows(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetch_results = [
        [
            {"id": 1, "name": "Inventario diario", "description": None, "is_active": True, "has_schedule": True}
        ]
    ]

    repo = TaskRepository()
    tasks = await repo.list_tasks()

    assert tasks[0].name == "Inventario diario"
    assert tasks[0].has_schedule is True


async def test_update_task_replaces_reports(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.update_task(
        1,
        TaskUpdate(
            name="Inventario diario",
            connection_name="InventarioDb",
            mail_to="a@example.com",
            is_active=False,
            reports=[
                TaskReportIn(
                    stored_procedure="ALCONSIT",
                    excel_file_name="ALCONSIT.xlsx",
                    sheet_name="ALCONSIT",
                )
            ],
        ),
    )

    update_calls = [c for c in conn.executed if "UPDATE tasks" in c[0]]
    delete_calls = [c for c in conn.executed if "DELETE FROM task_reports" in c[0]]
    insert_calls = [c for c in conn.executed if "INSERT INTO task_reports" in c[0]]

    assert len(update_calls) == 1
    assert update_calls[0][1][-1] is False  # is_active = False
    assert len(delete_calls) == 1
    assert len(insert_calls) == 1
```

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_task_repository.py -v`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/task_repository.py backend/tests/services/test_task_repository.py
git commit -m "feat: add TaskRepository CRUD for tasks and reports"
```

---

## Task 6: `TaskRepository` — programaciones (schedules)

**Files:**
- Modify: `backend/app/services/task_repository.py`
- Modify: `backend/tests/services/test_task_repository.py`

**Interfaces:**
- Produces: `TaskRepository.upsert_schedule(task_id, cron_expression) -> int`, `.delete_schedule(task_id) -> None`, `.list_active_schedules() -> list[dict]` (cada dict: `task_id`, `task_name`, `cron_expression`).

- [ ] **Step 0: Agregar seguimiento de lecturas al fixture `FakeConnection`**

Task 5 dejó `FakeConnection.executed` registrando solo llamadas a `execute()`
(un fix necesario para que su propio primer test pasara, ya que `create_task`
inserta vía `fetchval`, no `execute`). El test de esta tarea necesita
verificar una llamada `fetchval` (el INSERT de `upsert_schedule`), así que
agregar una lista paralela `fetched` que registre `fetchval`/`fetchrow`/`fetch`
por separado (sin tocar `executed`). En `backend/tests/services/test_task_repository.py`,
dentro de la clase `FakeConnection`, cambiar:

```python
    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []
        self.fetchval_results: list = []
        self.fetchrow_results: list = []
        self.fetch_results: list = []

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchval(self, query, *args):
        return self.fetchval_results.pop(0) if self.fetchval_results else None

    async def fetchrow(self, query, *args):
        return self.fetchrow_results.pop(0) if self.fetchrow_results else None

    async def fetch(self, query, *args):
        return self.fetch_results.pop(0) if self.fetch_results else []
```

por:

```python
    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []
        self.fetched: list[tuple[str, tuple]] = []
        self.fetchval_results: list = []
        self.fetchrow_results: list = []
        self.fetch_results: list = []

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchval(self, query, *args):
        self.fetched.append((query, args))
        return self.fetchval_results.pop(0) if self.fetchval_results else None

    async def fetchrow(self, query, *args):
        self.fetched.append((query, args))
        return self.fetchrow_results.pop(0) if self.fetchrow_results else None

    async def fetch(self, query, *args):
        self.fetched.append((query, args))
        return self.fetch_results.pop(0) if self.fetch_results else []
```

Run the existing suite (`pytest tests/services/test_task_repository.py -v`)
right after this change to confirm all of Task 5's tests still pass
unchanged (none of them inspect `.fetched`, so this should be a no-op for
them).

- [ ] **Step 1: Escribir los tests (fallan: los métodos no existen)**

Añadir a `backend/tests/services/test_task_repository.py`:

```python
async def test_upsert_schedule_replaces_existing(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchval_results = [5]

    repo = TaskRepository()
    schedule_id = await repo.upsert_schedule(1, "0 8 * * *")

    assert schedule_id == 5
    delete_calls = [c for c in conn.executed if "DELETE FROM task_schedules" in c[0]]
    insert_calls = [c for c in conn.fetched if "INSERT INTO task_schedules" in c[0]]
    assert len(delete_calls) == 1
    assert len(insert_calls) == 1
    assert insert_calls[0][1] == (1, "0 8 * * *")


async def test_delete_schedule_deletes_by_task_id(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.delete_schedule(1)

    delete_calls = [c for c in conn.executed if "DELETE FROM task_schedules" in c[0]]
    assert delete_calls == [("DELETE FROM task_schedules WHERE task_id = $1", (1,))]


async def test_list_active_schedules_joins_task_name(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetch_results = [
        [{"task_id": 1, "task_name": "Inventario diario", "cron_expression": "0 8 * * *"}]
    ]

    repo = TaskRepository()
    schedules = await repo.list_active_schedules()

    assert schedules == [
        {"task_id": 1, "task_name": "Inventario diario", "cron_expression": "0 8 * * *"}
    ]
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_task_repository.py -v`
Expected: FAIL (`AttributeError: 'TaskRepository' object has no attribute 'upsert_schedule'`)

- [ ] **Step 3: Implementar los métodos**

Agregar a la clase `TaskRepository` en `backend/app/services/task_repository.py` (antes de `_insert_reports`):

```python
    async def upsert_schedule(self, task_id: int, cron_expression: str) -> int:
        async with db_service.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM task_schedules WHERE task_id = $1",
                    task_id,
                )

                schedule_id = await conn.fetchval(
                    """
                    INSERT INTO task_schedules (task_id, cron_expression, is_active)
                    VALUES ($1, $2, TRUE)
                    RETURNING id
                    """,
                    task_id,
                    cron_expression,
                )

        return schedule_id

    async def delete_schedule(self, task_id: int) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM task_schedules WHERE task_id = $1",
                task_id,
            )

    async def list_active_schedules(self) -> list[dict]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.task_id AS task_id, t.name AS task_name, s.cron_expression AS cron_expression
                FROM task_schedules s
                JOIN tasks t ON t.id = s.task_id
                WHERE s.is_active AND t.is_active
                """
            )

        return [dict(r) for r in rows]
```

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_task_repository.py -v`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/task_repository.py backend/tests/services/test_task_repository.py
git commit -m "feat: add TaskRepository schedule methods"
```

---

## Task 7: `TaskRepository` — ejecuciones y logs

**Files:**
- Modify: `backend/app/services/task_repository.py`
- Modify: `backend/tests/services/test_task_repository.py`

**Interfaces:**
- Produces: `create_execution`, `get_running_execution`, `finish_execution`, `add_execution_report`, `add_execution_log`, `list_executions`, `get_execution`, `list_execution_logs`, `get_execution_report` — usados por `task_execution_service` (Task 12) y los routers (Tasks 13/14).

- [ ] **Step 1: Escribir los tests**

Añadir a `backend/tests/services/test_task_repository.py`:

```python
async def test_create_execution_returns_id(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchval_results = [42]

    repo = TaskRepository()
    execution_id = await repo.create_execution(1, "manual")

    assert execution_id == 42
    assert conn.fetched[0][1] == (1, "manual")


async def test_get_running_execution_returns_id_or_none(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchval_results = [None]

    repo = TaskRepository()
    result = await repo.get_running_execution(1)

    assert result is None


async def test_finish_execution_updates_status(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.finish_execution(42, "failed", "boom")

    assert conn.executed[0][1] == (42, "failed", "boom")


async def test_add_execution_report_inserts_row(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.add_execution_report(42, "ALCONSIT", "ALCONSIT_42.xlsx", "/output/ALCONSIT_42.xlsx", 100)

    assert conn.executed[0][1] == (42, "ALCONSIT", "ALCONSIT_42.xlsx", "/output/ALCONSIT_42.xlsx", 100)


async def test_add_execution_log_inserts_row(monkeypatch):
    conn = use_fake_pool(monkeypatch)

    repo = TaskRepository()
    await repo.add_execution_log(42, "info", "Ejecutando ALCONSIT")

    assert conn.executed[0][1] == (42, "info", "Ejecutando ALCONSIT")


async def test_list_executions_maps_rows(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetch_results = [
        [
            {
                "id": 42,
                "task_id": 1,
                "task_name": "Inventario diario",
                "trigger_type": "manual",
                "status": "running",
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": None,
                "error_message": None,
            }
        ]
    ]

    repo = TaskRepository()
    executions = await repo.list_executions(status="running", limit=50, offset=0)

    assert executions[0].id == 42
    assert executions[0].status == "running"


async def test_get_execution_returns_none_when_missing(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [None]

    repo = TaskRepository()
    result = await repo.get_execution(999)

    assert result is None


async def test_get_execution_returns_detail_with_reports(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [
        {
            "id": 42,
            "task_id": 1,
            "task_name": "Inventario diario",
            "trigger_type": "manual",
            "status": "success",
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:05:00+00:00",
            "error_message": None,
        }
    ]
    conn.fetch_results = [
        [{"id": 1, "stored_procedure": "ALCONSIT", "file_name": "ALCONSIT_42.xlsx", "row_count": 100}]
    ]

    repo = TaskRepository()
    execution = await repo.get_execution(42)

    assert execution.id == 42
    assert execution.reports[0].file_name == "ALCONSIT_42.xlsx"


async def test_list_execution_logs_maps_rows(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetch_results = [
        [{"id": 1, "timestamp": "2026-01-01T00:00:00+00:00", "level": "info", "message": "Ejecutando ALCONSIT"}]
    ]

    repo = TaskRepository()
    logs = await repo.list_execution_logs(42)

    assert logs[0].message == "Ejecutando ALCONSIT"


async def test_get_execution_report_returns_file_info(monkeypatch):
    conn = use_fake_pool(monkeypatch)
    conn.fetchrow_results = [
        {"id": 1, "file_name": "ALCONSIT_42.xlsx", "file_path": "/output/ALCONSIT_42.xlsx"}
    ]

    repo = TaskRepository()
    report = await repo.get_execution_report(42, 1)

    assert report["file_path"] == "/output/ALCONSIT_42.xlsx"
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_task_repository.py -v`
Expected: FAIL (métodos no existen)

- [ ] **Step 3: Implementar los métodos**

Agregar a `backend/app/services/task_repository.py`, importando también los esquemas necesarios (actualizar el `import` inicial):

```python
from app.schemas.tasks import (
    ExecutionDetailOut,
    ExecutionLogOut,
    ExecutionOut,
    ExecutionReportOut,
    TaskCreate,
    TaskOut,
    TaskReportOut,
    TaskSummary,
    TaskUpdate,
)
```

Y agregar estos métodos a la clase (antes de `_insert_reports`):

```python
    async def create_execution(self, task_id: int, trigger_type: str) -> int:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO task_executions (task_id, trigger_type, status)
                VALUES ($1, $2, 'running')
                RETURNING id
                """,
                task_id,
                trigger_type,
            )

    async def get_running_execution(self, task_id: int) -> int | None:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT id FROM task_executions WHERE task_id = $1 AND status = 'running' LIMIT 1",
                task_id,
            )

    async def finish_execution(self, execution_id: int, status: str, error_message: str | None) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE task_executions
                SET status = $2, error_message = $3, finished_at = now()
                WHERE id = $1
                """,
                execution_id,
                status,
                error_message,
            )

    async def add_execution_report(
        self, execution_id: int, stored_procedure: str, file_name: str, file_path: str, row_count: int
    ) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO execution_reports (execution_id, stored_procedure, file_name, file_path, row_count)
                VALUES ($1, $2, $3, $4, $5)
                """,
                execution_id,
                stored_procedure,
                file_name,
                file_path,
                row_count,
            )

    async def add_execution_log(self, execution_id: int, level: str, message: str) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO execution_logs (execution_id, level, message) VALUES ($1, $2, $3)",
                execution_id,
                level,
                message,
            )

    async def list_executions(self, status: str | None, limit: int, offset: int) -> list[ExecutionOut]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT e.id, e.task_id, t.name AS task_name, e.trigger_type, e.status,
                       e.started_at, e.finished_at, e.error_message
                FROM task_executions e
                JOIN tasks t ON t.id = e.task_id
                WHERE ($1::text IS NULL OR e.status = $1)
                ORDER BY e.started_at DESC
                LIMIT $2 OFFSET $3
                """,
                status,
                limit,
                offset,
            )

        return [ExecutionOut(**dict(r)) for r in rows]

    async def get_execution(self, execution_id: int) -> ExecutionDetailOut | None:
        async with db_service.pool.acquire() as conn:
            execution_row = await conn.fetchrow(
                """
                SELECT e.id, e.task_id, t.name AS task_name, e.trigger_type, e.status,
                       e.started_at, e.finished_at, e.error_message
                FROM task_executions e
                JOIN tasks t ON t.id = e.task_id
                WHERE e.id = $1
                """,
                execution_id,
            )

            if execution_row is None:
                return None

            report_rows = await conn.fetch(
                """
                SELECT id, stored_procedure, file_name, row_count
                FROM execution_reports WHERE execution_id = $1 ORDER BY id
                """,
                execution_id,
            )

        return ExecutionDetailOut(
            **dict(execution_row),
            reports=[ExecutionReportOut(**dict(r)) for r in report_rows],
        )

    async def list_execution_logs(self, execution_id: int) -> list[ExecutionLogOut]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, timestamp, level, message
                FROM execution_logs WHERE execution_id = $1 ORDER BY timestamp
                """,
                execution_id,
            )

        return [ExecutionLogOut(**dict(r)) for r in rows]

    async def get_execution_report(self, execution_id: int, report_id: int) -> dict | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, file_name, file_path
                FROM execution_reports WHERE execution_id = $1 AND id = $2
                """,
                execution_id,
                report_id,
            )

        return dict(row) if row else None
```

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_task_repository.py -v`
Expected: `18 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/task_repository.py backend/tests/services/test_task_repository.py
git commit -m "feat: add TaskRepository execution and log methods"
```

---

## Task 8: Cliente SQL Server (`sqlserver_client.py`)

**Files:**
- Create: `backend/app/services/sqlserver_client.py`
- Create: `backend/tests/services/test_sqlserver_client.py`

**Interfaces:**
- Produces: `async def fetch_stored_procedure_rows(connection_string: str, stored_procedure: str) -> tuple[list[str], list[tuple]]`.

- [ ] **Step 1: Escribir el test**

Crear `backend/tests/services/test_sqlserver_client.py`:

```python
from unittest.mock import MagicMock

from app.services import sqlserver_client


async def test_fetch_stored_procedure_rows_returns_columns_and_rows(monkeypatch):
    fake_cursor = MagicMock()
    fake_cursor.description = [("ItemCode",), ("Stock",)]
    fake_cursor.fetchall.return_value = [("A00001", 10), ("A00002", 5)]

    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    fake_conn.__exit__.return_value = False
    fake_conn.cursor.return_value = fake_cursor

    connect_calls = []

    def fake_connect(connection_string):
        connect_calls.append(connection_string)
        return fake_conn

    monkeypatch.setattr(sqlserver_client.pyodbc, "connect", fake_connect)

    columns, rows = await sqlserver_client.fetch_stored_procedure_rows("DRIVER=x;", "ALCONSIT")

    assert columns == ["ItemCode", "Stock"]
    assert rows == [("A00001", 10), ("A00002", 5)]
    assert connect_calls == ["DRIVER=x;"]
    fake_cursor.execute.assert_called_once_with("{CALL ALCONSIT}")
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_sqlserver_client.py -v`
Expected: FAIL (`app.services.sqlserver_client` no existe)

- [ ] **Step 3: Implementar**

Crear `backend/app/services/sqlserver_client.py`:

```python
import asyncio

import pyodbc


def _fetch_sync(connection_string: str, stored_procedure: str) -> tuple[list[str], list[tuple]]:
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute(f"{{CALL {stored_procedure}}}")

        columns = [col[0] for col in cursor.description]
        rows = [tuple(row) for row in cursor.fetchall()]

        return columns, rows


async def fetch_stored_procedure_rows(
    connection_string: str, stored_procedure: str
) -> tuple[list[str], list[tuple]]:
    return await asyncio.to_thread(_fetch_sync, connection_string, stored_procedure)
```

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_sqlserver_client.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/sqlserver_client.py backend/tests/services/test_sqlserver_client.py
git commit -m "feat: add SQL Server stored procedure client"
```

---

## Task 9: Generación de Excel (`excel_export.py`)

**Files:**
- Create: `backend/app/services/excel_export.py`
- Create: `backend/tests/services/test_excel_export.py`

**Interfaces:**
- Produces: `def generar_excel(columns: list[str], rows: list[tuple], sheet_name: str, file_path: str) -> int`.

- [ ] **Step 1: Escribir el test**

Crear `backend/tests/services/test_excel_export.py`:

```python
from openpyxl import load_workbook

from app.services.excel_export import generar_excel


def test_generar_excel_writes_header_and_rows(tmp_path):
    file_path = tmp_path / "reporte.xlsx"

    row_count = generar_excel(
        columns=["ItemCode", "ItemName", "Stock"],
        rows=[("A00001", "Producto 1", 10), ("A00002", "Producto 2", 5)],
        sheet_name="ALCONSIT",
        file_path=str(file_path),
    )

    assert row_count == 2

    workbook = load_workbook(file_path)
    sheet = workbook["ALCONSIT"]

    assert [c.value for c in sheet[1]] == ["ItemCode", "ItemName", "Stock"]
    assert [c.value for c in sheet[2]] == ["A00001", "Producto 1", 10]
    assert [c.value for c in sheet[3]] == ["A00002", "Producto 2", 5]


def test_generar_excel_forces_text_format_on_itemcode_column(tmp_path):
    file_path = tmp_path / "reporte.xlsx"

    generar_excel(
        columns=["ItemCode", "Stock"],
        rows=[("00123", 10)],
        sheet_name="ALCONSIT",
        file_path=str(file_path),
    )

    workbook = load_workbook(file_path)
    sheet = workbook["ALCONSIT"]

    assert sheet["A2"].number_format == "@"
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_excel_export.py -v`
Expected: FAIL (`app.services.excel_export` no existe)

- [ ] **Step 3: Implementar**

Crear `backend/app/services/excel_export.py`:

```python
import os

from openpyxl import Workbook


def generar_excel(columns: list[str], rows: list[tuple], sheet_name: str, file_path: str) -> int:
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name[:31]

    sheet.append(columns)
    for row in rows:
        sheet.append(list(row))

    item_code_index = next(
        (i for i, name in enumerate(columns) if name.lower() == "itemcode"),
        None,
    )

    if item_code_index is not None:
        column_letter = sheet.cell(row=1, column=item_code_index + 1).column_letter
        for row_number in range(2, sheet.max_row + 1):
            sheet[f"{column_letter}{row_number}"].number_format = "@"

    workbook.freeze_panes = "A2"
    workbook.save(file_path)

    return len(rows)
```

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_excel_export.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/excel_export.py backend/tests/services/test_excel_export.py
git commit -m "feat: add Excel export service"
```

---

## Task 10: Envío de correo (`mail_service.py`)

**Files:**
- Create: `backend/app/services/mail_service.py`
- Create: `backend/tests/services/test_mail_service.py`

**Interfaces:**
- Consumes: `settings.mail_from/mail_smtp_server/mail_smtp_port/mail_user/mail_password` (Task 3).
- Produces: `async def enviar_correo_con_adjuntos(to: str, cc: str | None, subject: str, body: str, attachments: list[str]) -> None`.

- [ ] **Step 1: Escribir el test**

Crear `backend/tests/services/test_mail_service.py`:

```python
from unittest.mock import MagicMock

from app.services import mail_service


async def test_enviar_correo_con_adjuntos_uses_smtp_and_attaches_files(monkeypatch, tmp_path):
    attachment = tmp_path / "reporte.xlsx"
    attachment.write_bytes(b"contenido de prueba")

    fake_server = MagicMock()
    fake_server.__enter__.return_value = fake_server
    fake_server.__exit__.return_value = False

    smtp_calls = []

    def fake_smtp(host, port):
        smtp_calls.append((host, port))
        return fake_server

    monkeypatch.setattr(mail_service.smtplib, "SMTP", fake_smtp)
    monkeypatch.setattr(mail_service.settings, "mail_from", "info@example.com")
    monkeypatch.setattr(mail_service.settings, "mail_smtp_server", "smtp.example.com")
    monkeypatch.setattr(mail_service.settings, "mail_smtp_port", 587)
    monkeypatch.setattr(mail_service.settings, "mail_user", "info@example.com")
    monkeypatch.setattr(mail_service.settings, "mail_password", "secret")

    await mail_service.enviar_correo_con_adjuntos(
        to="a@example.com, b@example.com",
        cc="c@example.com",
        subject="Reportes de prueba",
        body="cuerpo",
        attachments=[str(attachment)],
    )

    assert smtp_calls == [("smtp.example.com", 587)]
    fake_server.starttls.assert_called_once()
    fake_server.login.assert_called_once_with("info@example.com", "secret")

    send_call = fake_server.send_message.call_args
    message = send_call.args[0]
    assert message["Subject"] == "Reportes de prueba"
    assert message["To"] == "a@example.com, b@example.com"
    assert message["Cc"] == "c@example.com"
    assert send_call.kwargs["to_addrs"] == ["a@example.com", "b@example.com", "c@example.com"]
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_mail_service.py -v`
Expected: FAIL (`app.services.mail_service` no existe)

- [ ] **Step 3: Implementar**

Crear `backend/app/services/mail_service.py`:

```python
import asyncio
import smtplib
from email.message import EmailMessage

from app.config import settings


def _send_sync(to: str, cc: str | None, subject: str, body: str, attachments: list[str]) -> None:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    if cc:
        message["Cc"] = cc
    message["Subject"] = subject
    message.set_content(body)

    for path in attachments:
        with open(path, "rb") as f:
            data = f.read()

        file_name = path.replace("\\", "/").rsplit("/", 1)[-1]
        message.add_attachment(
            data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=file_name,
        )

    recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
    if cc:
        recipients += [addr.strip() for addr in cc.split(",") if addr.strip()]

    with smtplib.SMTP(settings.mail_smtp_server, settings.mail_smtp_port) as server:
        server.starttls()
        server.login(settings.mail_user, settings.mail_password)
        server.send_message(message, to_addrs=recipients)


async def enviar_correo_con_adjuntos(
    to: str, cc: str | None, subject: str, body: str, attachments: list[str]
) -> None:
    await asyncio.to_thread(_send_sync, to, cc, subject, body, attachments)
```

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_mail_service.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mail_service.py backend/tests/services/test_mail_service.py
git commit -m "feat: add mail service with attachments"
```

---

## Task 11: Scheduler (`scheduler_service.py`)

**Files:**
- Create: `backend/app/services/scheduler_service.py`
- Create: `backend/tests/services/test_scheduler_service.py`

**Interfaces:**
- Produces: clase `SchedulerService` con `start()`, `shutdown()`, `schedule_task(task_id, cron_expression)`, `unschedule_task(task_id)`, `get_next_run_time(task_id) -> datetime | None`; singleton `scheduler_service`; `get_scheduler_service()`.

- [ ] **Step 1: Escribir el test**

Crear `backend/tests/services/test_scheduler_service.py`:

```python
from app.services.scheduler_service import SchedulerService


async def test_schedule_task_sets_next_run_time():
    service = SchedulerService()
    service.start()

    try:
        service.schedule_task(1, "0 0 1 1 *")  # una vez al año

        assert service.get_next_run_time(1) is not None
    finally:
        service.shutdown()


async def test_unschedule_task_removes_job():
    service = SchedulerService()
    service.start()

    try:
        service.schedule_task(1, "0 0 1 1 *")
        service.unschedule_task(1)

        assert service.get_next_run_time(1) is None
    finally:
        service.shutdown()


async def test_get_next_run_time_none_when_never_scheduled():
    service = SchedulerService()
    service.start()

    try:
        assert service.get_next_run_time(999) is None
    finally:
        service.shutdown()
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_scheduler_service.py -v`
Expected: FAIL (`app.services.scheduler_service` no existe)

- [ ] **Step 3: Implementar**

Crear `backend/app/services/scheduler_service.py`:

```python
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
```

Nota: este archivo importa `ejecutar_tarea` de `task_execution_service`, que se crea recién en la Task 12. Para que este test pase antes de esa tarea, la Task 12 debe completarse primero **o** este import debe resolverse — seguir el plan en orden (Task 12 antes de correr los tests de esta tarea) evita el problema. Si se ejecuta fuera de orden, crear primero un `task_execution_service.py` mínimo con una función `async def ejecutar_tarea(task_id, trigger_type): ...` (`pass`) como stub temporal, y completarla en la Task 12.

- [ ] **Step 4: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_scheduler_service.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/scheduler_service.py backend/tests/services/test_scheduler_service.py
git commit -m "feat: add APScheduler wrapper for task schedules"
```

---

## Task 12: Orquestación de ejecución (`task_execution_service.py`)

**Files:**
- Create: `backend/app/services/task_execution_service.py`
- Create: `backend/tests/services/test_task_execution_service.py`

**Interfaces:**
- Consumes: `TaskRepository` (Tasks 5/6/7), `sqlserver_client.fetch_stored_procedure_rows` (Task 8), `excel_export.generar_excel` (Task 9), `mail_service.enviar_correo_con_adjuntos` (Task 10), `settings.task_sql_connections/task_output_folder` (Task 3).
- Produces: `class TaskAlreadyRunningError(Exception)`; `async def iniciar_ejecucion(task_id, trigger_type, *, repo=None) -> int`; `async def continuar_ejecucion(execution_id, task_id, *, repo=None, sql_client=sqlserver_client, excel=excel_export, mailer=mail_service) -> None`; `async def ejecutar_tarea(task_id, trigger_type, *, repo=None, sql_client=sqlserver_client, excel=excel_export, mailer=mail_service) -> int` (usada por el scheduler, Task 11).

- [ ] **Step 1: Escribir un stub mínimo para no romper la Task 11**

Si la Task 11 ya está hecha y depende de este módulo, crear primero un stub en `backend/app/services/task_execution_service.py`:

```python
async def ejecutar_tarea(task_id: int, trigger_type: str) -> int:
    raise NotImplementedError
```

(Este stub se reemplaza por la implementación completa más abajo; si se sigue el plan en orden, este paso puede omitirse y se escribe directamente la versión completa.)

- [ ] **Step 2: Escribir los tests**

Crear `backend/tests/services/test_task_execution_service.py`:

```python
from unittest.mock import AsyncMock

import pytest

from app.services.task_execution_service import (
    TaskAlreadyRunningError,
    continuar_ejecucion,
    ejecutar_tarea,
    iniciar_ejecucion,
)


class FakeReport:
    def __init__(self, stored_procedure, excel_file_name, sheet_name):
        self.stored_procedure = stored_procedure
        self.excel_file_name = excel_file_name
        self.sheet_name = sheet_name


class FakeTask:
    def __init__(self, reports):
        self.name = "Inventario diario"
        self.connection_name = "InventarioDb"
        self.mail_to = "a@example.com"
        self.mail_cc = None
        self.mail_subject_template = None
        self.reports = reports


def make_repo(task, running_execution_id=None, new_execution_id=100):
    repo = AsyncMock()
    repo.get_running_execution.return_value = running_execution_id
    repo.get_task.return_value = task
    repo.create_execution.return_value = new_execution_id
    return repo


async def test_iniciar_ejecucion_raises_when_already_running():
    repo = make_repo(task=None, running_execution_id=55)

    with pytest.raises(TaskAlreadyRunningError):
        await iniciar_ejecucion(1, "manual", repo=repo)

    repo.create_execution.assert_not_called()


async def test_iniciar_ejecucion_creates_execution_when_free():
    repo = make_repo(task=None, running_execution_id=None, new_execution_id=100)

    execution_id = await iniciar_ejecucion(1, "manual", repo=repo)

    assert execution_id == 100
    repo.create_execution.assert_called_once_with(1, "manual")


async def test_continuar_ejecucion_success_generates_files_and_sends_one_email(monkeypatch):
    task = FakeTask(
        reports=[
            FakeReport("ALCONSIT", "ALCONSIT.xlsx", "ALCONSIT"),
            FakeReport("ALCONIMS", "ALCONIMS.xlsx", "ALCONIMS"),
        ]
    )
    repo = make_repo(task=task)

    sql_client = AsyncMock()
    sql_client.fetch_stored_procedure_rows.return_value = (["ItemCode"], [("A1",)])

    excel = AsyncMock()
    excel.generar_excel = AsyncMock(return_value=1)

    mailer = AsyncMock()

    monkeypatch.setattr(
        "app.services.task_execution_service.settings.task_sql_connections",
        {"InventarioDb": "DRIVER=x;"},
    )
    monkeypatch.setattr(
        "app.services.task_execution_service.settings.task_output_folder", "output"
    )

    await continuar_ejecucion(100, 1, repo=repo, sql_client=sql_client, excel=excel, mailer=mailer)

    assert sql_client.fetch_stored_procedure_rows.call_count == 2
    assert excel.generar_excel.call_count == 2
    mailer.enviar_correo_con_adjuntos.assert_called_once()
    repo.finish_execution.assert_called_once_with(100, "success", None)


async def test_continuar_ejecucion_stops_and_marks_failed_on_report_error(monkeypatch):
    task = FakeTask(
        reports=[
            FakeReport("ALCONSIT", "ALCONSIT.xlsx", "ALCONSIT"),
            FakeReport("ALCONIMS", "ALCONIMS.xlsx", "ALCONIMS"),
        ]
    )
    repo = make_repo(task=task)

    sql_client = AsyncMock()
    sql_client.fetch_stored_procedure_rows.side_effect = RuntimeError("SP falló")

    excel = AsyncMock()
    mailer = AsyncMock()

    monkeypatch.setattr(
        "app.services.task_execution_service.settings.task_sql_connections",
        {"InventarioDb": "DRIVER=x;"},
    )

    await continuar_ejecucion(100, 1, repo=repo, sql_client=sql_client, excel=excel, mailer=mailer)

    assert sql_client.fetch_stored_procedure_rows.call_count == 1
    excel.generar_excel.assert_not_called()
    mailer.enviar_correo_con_adjuntos.assert_not_called()
    repo.finish_execution.assert_called_once_with(100, "failed", "SP falló")


async def test_continuar_ejecucion_fails_when_connection_name_unknown():
    task = FakeTask(reports=[FakeReport("ALCONSIT", "ALCONSIT.xlsx", "ALCONSIT")])
    repo = make_repo(task=task)

    sql_client = AsyncMock()
    excel = AsyncMock()
    mailer = AsyncMock()

    await continuar_ejecucion(100, 1, repo=repo, sql_client=sql_client, excel=excel, mailer=mailer)

    sql_client.fetch_stored_procedure_rows.assert_not_called()
    status, error = repo.finish_execution.call_args.args[1], repo.finish_execution.call_args.args[2]
    assert status == "failed"
    assert "InventarioDb" in error


async def test_ejecutar_tarea_calls_iniciar_and_continuar():
    task = FakeTask(reports=[FakeReport("ALCONSIT", "ALCONSIT.xlsx", "ALCONSIT")])
    repo = make_repo(task=task, new_execution_id=200)

    sql_client = AsyncMock()
    sql_client.fetch_stored_procedure_rows.return_value = (["ItemCode"], [("A1",)])
    excel = AsyncMock()
    excel.generar_excel = AsyncMock(return_value=1)
    mailer = AsyncMock()

    import app.services.task_execution_service as module

    module.settings.task_sql_connections = {"InventarioDb": "DRIVER=x;"}

    execution_id = await ejecutar_tarea(
        1, "scheduled", repo=repo, sql_client=sql_client, excel=excel, mailer=mailer
    )

    assert execution_id == 200
    repo.create_execution.assert_called_once_with(1, "scheduled")
    mailer.enviar_correo_con_adjuntos.assert_called_once()
```

- [ ] **Step 3: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_task_execution_service.py -v`
Expected: FAIL (funciones no implementadas / no existen)

- [ ] **Step 4: Implementar**

Crear (o reemplazar el stub de) `backend/app/services/task_execution_service.py`:

```python
from datetime import datetime

from app.config import settings
from app.services import excel_export, mail_service, sqlserver_client
from app.services.task_repository import TaskRepository, task_repository


class TaskAlreadyRunningError(Exception):
    pass


def _default_repo(repo: TaskRepository | None) -> TaskRepository:
    return repo or task_repository


async def iniciar_ejecucion(
    task_id: int, trigger_type: str, *, repo: TaskRepository | None = None
) -> int:
    repo = _default_repo(repo)

    if await repo.get_running_execution(task_id) is not None:
        raise TaskAlreadyRunningError(
            f"La tarea {task_id} ya tiene una ejecución en curso"
        )

    return await repo.create_execution(task_id, trigger_type)


async def continuar_ejecucion(
    execution_id: int,
    task_id: int,
    *,
    repo: TaskRepository | None = None,
    sql_client=sqlserver_client,
    excel=excel_export,
    mailer=mail_service,
) -> None:
    repo = _default_repo(repo)
    task = await repo.get_task(task_id)

    connection_string = settings.task_sql_connections.get(task.connection_name)
    if connection_string is None:
        message = f"Conexión '{task.connection_name}' no configurada"
        await repo.add_execution_log(execution_id, "error", message)
        await repo.finish_execution(execution_id, "failed", message)
        return

    generated_files = []

    for report in task.reports:
        await repo.add_execution_log(
            execution_id, "info", f"Ejecutando {report.stored_procedure}"
        )

        try:
            columns, rows = await sql_client.fetch_stored_procedure_rows(
                connection_string, report.stored_procedure
            )
        except Exception as exc:
            message = str(exc)
            await repo.add_execution_log(
                execution_id, "error", f"Error ejecutando {report.stored_procedure}: {message}"
            )
            await repo.finish_execution(execution_id, "failed", message)
            return

        base_name = report.excel_file_name.rsplit(".", 1)[0]
        file_name = f"{base_name}_{execution_id}.xlsx"
        file_path = f"{settings.task_output_folder.rstrip(chr(92)).rstrip('/')}/{file_name}"

        row_count = excel.generar_excel(columns, rows, report.sheet_name, file_path)
        generated_files.append(file_path)

        await repo.add_execution_report(
            execution_id, report.stored_procedure, file_name, file_path, row_count
        )
        await repo.add_execution_log(
            execution_id, "info", f"Excel generado: {file_name} ({row_count} filas)"
        )

    subject_template = task.mail_subject_template or "Reportes {task_name} - {timestamp}"
    subject = subject_template.format(
        task_name=task.name, timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    try:
        await mailer.enviar_correo_con_adjuntos(
            to=task.mail_to,
            cc=task.mail_cc,
            subject=subject,
            body=f"Adjunto se envían los reportes generados por la tarea '{task.name}'.",
            attachments=generated_files,
        )
    except Exception as exc:
        message = str(exc)
        await repo.add_execution_log(execution_id, "error", f"Error enviando correo: {message}")
        await repo.finish_execution(execution_id, "failed", message)
        return

    await repo.add_execution_log(execution_id, "info", "Correo enviado correctamente")
    await repo.finish_execution(execution_id, "success", None)


async def ejecutar_tarea(
    task_id: int,
    trigger_type: str,
    *,
    repo: TaskRepository | None = None,
    sql_client=sqlserver_client,
    excel=excel_export,
    mailer=mail_service,
) -> int:
    repo = _default_repo(repo)

    execution_id = await iniciar_ejecucion(task_id, trigger_type, repo=repo)
    await continuar_ejecucion(
        execution_id, task_id, repo=repo, sql_client=sql_client, excel=excel, mailer=mailer
    )

    return execution_id
```

Nota sobre `excel.generar_excel`: se llama de forma síncrona y directa (`row_count = excel.generar_excel(...)`, sin `await`), tal como está en el bloque de arriba — así es como lo esperan los tests de este plan (en producción `excel` es el módulo real de la Task 9, cuya función es síncrona; en los tests se inyecta un doble con el mismo nombre de método). Bloquea el event loop brevemente durante la generación del Excel, lo cual es aceptable para el volumen de filas de estos reportes; si en el futuro se necesita paralelismo real, envolver la llamada con `asyncio.to_thread` sería el siguiente paso, pero no forma parte de este plan.

- [ ] **Step 5: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/services/test_task_execution_service.py -v`
Expected: `6 passed`

- [ ] **Step 6: Correr toda la suite de tests hasta ahora**

Run: `cd backend && .venv\Scripts\python.exe -m pytest -v`
Expected: todos los tests pasan (incluida la Task 11, que dependía de este módulo)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/task_execution_service.py backend/tests/services/test_task_execution_service.py
git commit -m "feat: add task execution orchestration service"
```

---

## Task 13: Router de tareas (`app/routers/tasks.py`)

**Files:**
- Create: `backend/app/routers/tasks.py`
- Create: `backend/tests/routers/test_tasks_router.py`

**Interfaces:**
- Consumes: `get_task_repository` (Task 5-7), `get_scheduler_service` (Task 11), `iniciar_ejecucion`/`continuar_ejecucion`/`TaskAlreadyRunningError` (Task 12), esquemas de Task 4.
- Produces: `router` (FastAPI `APIRouter`, prefijo `/api/tasks`) con `GET/POST /`, `GET/PUT /{task_id}`, `POST/DELETE /{task_id}/schedule`, `POST /{task_id}/run`.

- [ ] **Step 1: Escribir los tests**

Crear `backend/tests/routers/test_tasks_router.py`:

```python
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.services.task_repository import get_task_repository
from app.services.scheduler_service import get_scheduler_service
import app.routers.tasks as tasks_router_module


def make_client(repo, scheduler=None):
    app.dependency_overrides[get_task_repository] = lambda: repo
    if scheduler is not None:
        app.dependency_overrides[get_scheduler_service] = lambda: scheduler
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_list_tasks_returns_summaries():
    repo = AsyncMock()
    repo.list_tasks.return_value = []
    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert response.json() == []
    next(gen, None)


def test_get_task_404_when_missing():
    repo = AsyncMock()
    repo.get_task.return_value = None
    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/tasks/999")

    assert response.status_code == 404
    next(gen, None)


def test_run_task_returns_409_when_already_running(monkeypatch):
    repo = AsyncMock()
    repo.get_task.return_value = object()
    repo.get_running_execution.return_value = 55

    gen = make_client(repo)
    client = next(gen)

    response = client.post("/api/tasks/1/run")

    assert response.status_code == 409
    next(gen, None)


def test_run_task_returns_execution_id_and_schedules_background_work(monkeypatch):
    repo = AsyncMock()
    repo.get_task.return_value = object()
    repo.get_running_execution.return_value = None
    repo.create_execution.return_value = 321

    continuar_calls = []

    async def fake_continuar(execution_id, task_id, **kwargs):
        continuar_calls.append((execution_id, task_id))

    monkeypatch.setattr(tasks_router_module, "continuar_ejecucion", fake_continuar)

    gen = make_client(repo)
    client = next(gen)

    response = client.post("/api/tasks/1/run")

    assert response.status_code == 200
    assert response.json() == {"execution_id": 321}
    assert continuar_calls == [(321, 1)]
    next(gen, None)


def test_create_schedule_registers_job_and_returns_next_run_time():
    repo = AsyncMock()
    repo.get_task.return_value = type("T", (), {"name": "Inventario diario"})()

    scheduler = AsyncMock()
    scheduler.get_next_run_time.return_value = None

    gen = make_client(repo, scheduler=scheduler)
    client = next(gen)

    response = client.post("/api/tasks/1/schedule", json={"cron_expression": "0 8 * * *"})

    assert response.status_code == 200
    scheduler.schedule_task.assert_called_once_with(1, "0 8 * * *")
    next(gen, None)
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/routers/test_tasks_router.py -v`
Expected: FAIL (`app.routers.tasks` no existe / `app.main` no lo incluye todavía)

- [ ] **Step 3: Implementar el router**

Crear `backend/app/routers/tasks.py`:

```python
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
    task_id: int, payload: TaskUpdate, repo: TaskRepository = Depends(get_task_repository)
):
    existing = await repo.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    await repo.update_task(task_id, payload)
    return await repo.get_task(task_id)


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

    await repo.upsert_schedule(task_id, payload.cron_expression)
    scheduler.schedule_task(task_id, payload.cron_expression)

    return ScheduleOut(
        id=task_id,
        task_id=task_id,
        task_name=task.name,
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
        raise HTTPException(status_code=409, detail=str(exc))

    background_tasks.add_task(continuar_ejecucion, execution_id, task_id, repo=repo)

    return RunTaskResponse(execution_id=execution_id)
```

- [ ] **Step 4: Incluir el router en `main.py` (necesario para que el `TestClient` encuentre las rutas)**

En `backend/app/main.py`, agregar el import y el `include_router` (junto a los existentes):

```python
from app.routers.tasks import router as tasks_router
```

```python
app.include_router(tasks_router)
```

- [ ] **Step 5: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/routers/test_tasks_router.py -v`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/tasks.py backend/app/main.py backend/tests/routers/test_tasks_router.py
git commit -m "feat: add tasks router (CRUD, schedule, manual run)"
```

---

## Task 14: Router de ejecuciones y programaciones (`app/routers/executions.py`)

**Files:**
- Create: `backend/app/routers/executions.py`
- Create: `backend/tests/routers/test_executions_router.py`

**Interfaces:**
- Consumes: `get_task_repository`, `get_scheduler_service`.
- Produces: `router` (FastAPI `APIRouter`, prefijo `/api`) con `GET /schedules`, `GET /executions`, `GET /executions/{id}`, `GET /executions/{id}/logs`, `GET /executions/{id}/reports/{report_id}/download`.

- [ ] **Step 1: Escribir los tests**

Crear `backend/tests/routers/test_executions_router.py`:

```python
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.services.scheduler_service import get_scheduler_service
from app.services.task_repository import get_task_repository


def make_client(repo, scheduler=None):
    app.dependency_overrides[get_task_repository] = lambda: repo
    if scheduler is not None:
        app.dependency_overrides[get_scheduler_service] = lambda: scheduler
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_list_schedules_includes_next_run_time():
    repo = AsyncMock()
    repo.list_active_schedules.return_value = [
        {"task_id": 1, "task_name": "Inventario diario", "cron_expression": "0 8 * * *"}
    ]

    scheduler = AsyncMock()
    scheduler.get_next_run_time.return_value = None

    gen = make_client(repo, scheduler=scheduler)
    client = next(gen)

    response = client.get("/api/schedules")

    assert response.status_code == 200
    assert response.json()[0]["task_name"] == "Inventario diario"
    next(gen, None)


def test_get_execution_404_when_missing():
    repo = AsyncMock()
    repo.get_execution.return_value = None
    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/executions/999")

    assert response.status_code == 404
    next(gen, None)


def test_download_report_404_when_missing():
    repo = AsyncMock()
    repo.get_execution_report.return_value = None
    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/executions/1/reports/1/download")

    assert response.status_code == 404
    next(gen, None)


def test_download_report_returns_file(tmp_path):
    file_path = tmp_path / "reporte.xlsx"
    file_path.write_bytes(b"contenido")

    repo = AsyncMock()
    repo.get_execution_report.return_value = {
        "id": 1,
        "file_name": "reporte.xlsx",
        "file_path": str(file_path),
    }

    gen = make_client(repo)
    client = next(gen)

    response = client.get("/api/executions/1/reports/1/download")

    assert response.status_code == 200
    assert response.content == b"contenido"
    next(gen, None)
```

- [ ] **Step 2: Correr pytest y confirmar que falla**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/routers/test_executions_router.py -v`
Expected: FAIL (`app.routers.executions` no existe)

- [ ] **Step 3: Implementar el router**

Crear `backend/app/routers/executions.py`:

```python
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

    return FileResponse(
        path=report["file_path"],
        filename=report["file_name"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
```

- [ ] **Step 4: Incluir el router en `main.py`**

En `backend/app/main.py`:

```python
from app.routers.executions import router as executions_router
```

```python
app.include_router(executions_router)
```

- [ ] **Step 5: Correr pytest y confirmar que pasa**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/routers/test_executions_router.py -v`
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/executions.py backend/app/main.py backend/tests/routers/test_executions_router.py
git commit -m "feat: add executions and schedules router"
```

---

## Task 15: Arranque del scheduler en `main.py` y verificación final

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_main.py`

**Interfaces:**
- Produces: al iniciar la app, todas las `task_schedules` activas quedan registradas en `scheduler_service`; al apagar, el scheduler se detiene limpiamente.

- [ ] **Step 1: Escribir el test de rutas registradas**

Crear `backend/tests/test_main.py`:

```python
from app.main import app


def test_task_and_execution_routes_are_registered():
    paths = {route.path for route in app.routes}

    assert "/api/tasks" in paths
    assert "/api/tasks/{task_id}" in paths
    assert "/api/tasks/{task_id}/schedule" in paths
    assert "/api/tasks/{task_id}/run" in paths
    assert "/api/schedules" in paths
    assert "/api/executions" in paths
    assert "/api/executions/{execution_id}" in paths
    assert "/api/executions/{execution_id}/logs" in paths
    assert "/api/executions/{execution_id}/reports/{report_id}/download" in paths
```

- [ ] **Step 2: Correr pytest y confirmar que falla o pasa parcialmente**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_main.py -v`
Expected: si las Tasks 13/14 ya incluyeron los routers, esto ya debería pasar — este test queda como prueba de regresión permanente, no hay nada que implementar aquí más que confirmar.

- [ ] **Step 3: Conectar el scheduler al lifespan**

En `backend/app/main.py`, agregar los imports:

```python
from app.services.scheduler_service import scheduler_service
from app.services.task_repository import task_repository
```

Y actualizar `lifespan`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_service.connect()

    schedules = await task_repository.list_active_schedules()
    for schedule in schedules:
        scheduler_service.schedule_task(schedule["task_id"], schedule["cron_expression"])
    scheduler_service.start()

    yield

    scheduler_service.shutdown()
    await db_service.disconnect()
```

- [ ] **Step 4: Correr toda la suite de tests**

Run: `cd backend && .venv\Scripts\python.exe -m pytest -v`
Expected: todos los tests pasan (el `lifespan` actualizado no se ejecuta en estos tests porque ninguno usa `with TestClient(app) as client`, así que no requiere una Postgres real conectada).

- [ ] **Step 5: Verificación manual end-to-end**

Con la base de datos (Task 2) ya migrada y `backend/.env` completo (Task 3):

```bash
cd backend && .venv\Scripts\uvicorn.exe app.main:app --reload
```

Con el servidor arriba:
1. `POST /api/tasks` con un body de ejemplo (nombre, `connection_name: "InventarioDb"`, `mail_to`, y los dos reportes ALCONSIT/ALCONIMS) → confirmar `201` y que devuelve el `id`.
2. `POST /api/tasks/{id}/run` → confirmar `200` con un `execution_id`, y que en `TASK_OUTPUT_FOLDER` aparecen los `.xlsx` y llega el correo.
3. `GET /api/executions/{execution_id}` → confirmar `status: "success"` y los reportes generados.
4. `POST /api/tasks/{id}/schedule` con un cron corto (para probar) → confirmar que `GET /api/schedules` muestra `next_run_time`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_main.py
git commit -m "feat: start task scheduler on backend startup"
```

---

## Self-Review

**Cobertura del spec:** modelo de datos (Tasks 2, 5-7), configuración/secretos (Task 3), motor de ejecución (Tasks 8-10, 12), scheduler (Task 11), API completa (Tasks 13-14), arranque (Task 15). El único punto del spec explícitamente fuera de alcance (conectar el frontend) queda para el siguiente plan, como se acordó.

**Placeholders:** ninguno — cada paso tiene código completo y comandos exactos.

**Consistencia de tipos:** `TaskRepository`, `SchedulerService`, `TaskAlreadyRunningError`, `iniciar_ejecucion`/`continuar_ejecucion`/`ejecutar_tarea`, y los esquemas de Task 4 se usan con el mismo nombre y firma en todas las tareas donde aparecen (routers, scheduler, tests).

**Orden de dependencia entre Tasks 11 y 12:** `scheduler_service.py` (Task 11) importa `ejecutar_tarea` de `task_execution_service.py` (Task 12). El plan nota explícitamente este orden en la Task 11 y da un stub de contingencia si se ejecutan fuera de secuencia.
