# Motor de tareas programadas — Diseño (Backend + API)

Fecha: 2026-09-16

## Contexto y alcance

La aplicación ya tiene una capa de navegación con 10 pantallas placeholder
(Dashboard, Catálogo de tareas, Crear/editar tarea, Programar tarea, Tareas
programadas, Ejecuciones en curso, Historial de ejecuciones, Detalle de
ejecución, Visualización de logs, Configuración). Este diseño cubre el
**primer sub-proyecto**: el motor de tareas en el backend (modelo de datos,
ejecución, programación por cron, API REST). El **segundo sub-proyecto**
(conectar esas 8 pantallas restantes a esta API) se diseña e implementa
después, una vez este backend esté funcionando.

El caso de uso concreto que dispara este trabajo: una tarea que corre uno o
más stored procedures contra una base SQL Server externa, genera un Excel
por cada uno, y envía todos los Excel adjuntos en un solo correo — ya sea a
demanda o en un horario recurrente.

Repo sin control de versiones (`git` no inicializado en este directorio), así
que este documento no se commitea; solo queda en disco como referencia.

## Modelo de datos (Postgres — BD propia de la app)

No existe herramienta de migraciones en el repo (los stored procedures de
Postgres ya usados, como `sp_guardar_inventario_articulo`, se administran a
mano). Seguimos el mismo patrón: un script SQL nuevo
(`backend/sql/002_tasks_schema.sql`) que se corre una vez contra la base.

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

Notas de diseño:

- `tasks` no se borra físicamente: se desactiva (`is_active = false`), igual
  que el patrón "Activo/Inactivo" que ya usa la vista de inventario. Esto
  evita romper el historial de ejecuciones (que referencia `task_id`).
- `task_schedules` permite varias filas por tarea a nivel de base, pero la
  API solo deja una activa a la vez por tarea (alcanza para "Programar
  tarea" como pantalla única; no cierra la puerta a más de una en el
  futuro).
- `execution_reports` guarda el nombre del stored procedure "congelado" al
  momento de ejecutar, para que el historial no cambie si luego editan la
  tarea.

## Configuración y secretos

Nuevas variables en `backend/.env` (mismo patrón que `SAP_*`/`DB_*` en
`app/config.py`):

```
TASK_SQL_CONNECTIONS={"InventarioDb": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.249.249.172;DATABASE=Inventario;UID=LuceeServer;PWD=<password>;TrustServerCertificate=yes;"}
TASK_OUTPUT_FOLDER=C:\output

MAIL_FROM=info@casamedic.com.pa
MAIL_SMTP_SERVER=smtp.office365.com
MAIL_SMTP_PORT=587
MAIL_USER=info@casamedic.com.pa
MAIL_PASSWORD=<password>
```

- `TASK_SQL_CONNECTIONS` es un JSON `{nombre: connection_string}`. Una tarea
  solo guarda el `connection_name` (p. ej. `"InventarioDb"`); la contraseña
  nunca pasa por la tabla `tasks` ni por la API.
- La cadena de conexión debe estar en **formato pyodbc** (con
  `DRIVER={...}`), no en el formato ADO.NET que trae el ejemplo original de
  C#. Arriba se muestra la conversión exacta del ejemplo que compartiste.
- `From`/`SmtpServer`/`SmtpPort`/`User`/`Password` del correo son globales
  para todo el sistema (organización, no por tarea). Por tarea solo se
  define `mail_to`, `mail_cc` opcional, y un `mail_subject_template`
  opcional (default: `"Reportes {task_name} - {timestamp}"`).
- Igual que en el ejemplo original, `MAIL_PASSWORD` admite quedar vacío si
  se prefiere pasarlo por variable de entorno del proceso en vez del
  archivo `.env`.

## Motor de ejecución

Nuevo `backend/app/services/task_execution_service.py`:

`ejecutar_tarea(task_id: int, trigger_type: Literal["manual","scheduled"]) -> int`
(devuelve el `execution_id`):

1. Verifica que no haya ya una ejecución `running` para esa tarea → si la
   hay, lanza un error de conflicto (409 en la capa API).
2. Inserta la fila en `task_executions` (`status='running'`).
3. Para cada `task_report` de la tarea, en orden (`position`):
   a. Ejecuta el stored procedure vía `pyodbc` (bloqueante, corrido con
      `asyncio.to_thread` para no bloquear el event loop de FastAPI).
   b. Si falla: registra `execution_logs` (level=error), marca la ejecución
      `failed` con `error_message`, **no** continúa con los demás reportes
      ni envía correo, y retorna.
   c. Si tiene éxito: genera el Excel con `openpyxl` en
      `TASK_OUTPUT_FOLDER`, nombrando el archivo
      `{excel_file_name_sin_extension}_{execution_id}.xlsx` (el
      `execution_id` ya garantiza unicidad, sin depender de timestamps).
      Inserta fila en `execution_reports` con `row_count`. Registra log
      info.
4. Si **todos** los reportes tuvieron éxito: envía un solo correo (SMTP,
   también en thread aparte) con todos los Excel adjuntos, usando
   `mail_to`/`mail_cc` de la tarea y el remitente/servidor globales. Marca
   la ejecución `success`. Si el envío de correo falla, marca `failed` con
   el error (los archivos ya generados quedan registrados igual).
5. Cierra la ejecución con `finished_at = now()`.

Esto replica el comportamiento del script de C# (aborta todo el proceso si
cualquier paso falla, un solo correo al final) pero con progreso visible
paso a paso vía `execution_logs`.

## Scheduler

`AsyncIOScheduler` de **APScheduler**, arrancado en el `lifespan` de
`main.py` junto al `db_service`:

- Al iniciar: lee de Postgres todas las `task_schedules` con `is_active =
  true` y registra un `CronTrigger` por cada una, apuntando a
  `ejecutar_tarea(task_id, trigger_type="scheduled")`.
- Crear/actualizar/borrar una programación vía API actualiza Postgres y,
  en el mismo request, añade/reemplaza/quita el job correspondiente en el
  scheduler en memoria — no hace falta reiniciar el backend.
- "Próxima ejecución" en la pantalla de Tareas programadas se lee
  directamente del job de APScheduler (`job.next_run_time`), sin depender
  de una librería aparte para parsear cron.

## API (FastAPI, prefijo `/api/tasks` y `/api/executions`)

- `GET /api/tasks` — lista (incluye si tiene programación activa)
- `POST /api/tasks` — crea tarea con sus `reports` y datos de correo
  anidados en un solo payload
- `GET /api/tasks/{id}` — detalle completo (para el formulario de edición)
- `PUT /api/tasks/{id}` — actualiza tarea (incluye `is_active`, así que
  activar/desactivar es solo un PUT con ese campo cambiado) + reemplaza su
  lista de reports
- `POST /api/tasks/{id}/schedule` — crea o reemplaza la programación cron
  de la tarea
- `DELETE /api/tasks/{id}/schedule` — quita la programación
- `GET /api/schedules` — todas las programaciones activas, con nombre de
  tarea y próxima ejecución
- `POST /api/tasks/{id}/run` — dispara ejecución manual → `{execution_id}`
  (409 si ya hay una corriendo)
- `GET /api/executions?status=running` — Ejecuciones en curso
- `GET /api/executions?status=history` (con paginación simple
  `limit`/`offset`) — Historial de ejecuciones
- `GET /api/executions/{id}` — detalle (tarea, estado, tiempos, reportes
  generados)
- `GET /api/executions/{id}/logs` — logs en orden cronológico
- `GET /api/executions/{id}/reports/{report_id}/download` — descarga el
  Excel generado (stream desde `TASK_OUTPUT_FOLDER`)

## Nuevas dependencias

`pyodbc`, `openpyxl`, `apscheduler` — se agregan a `backend/requirements.txt`.
Asume que la máquina donde corre el backend tiene instalado el "ODBC Driver
17 (o 18) for SQL Server".

## Fuera de alcance (por ahora)

- Conectar las 8 pantallas del frontend a esta API (sub-proyecto 2).
- Borrado físico de tareas, políticas de retención/limpieza de archivos o
  ejecuciones antiguas.
- Múltiples programaciones activas simultáneas para una misma tarea.
- Tipos de tarea distintos al de "SQL Server → Excel → correo" (el modelo
  de `task_reports` es genérico en nombre, pero la lógica de ejecución de
  este diseño solo implementa ese tipo).
