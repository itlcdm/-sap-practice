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


def _fetch_view_sync(
    connection_string: str, source_view: str, limit: int
) -> tuple[list[str], list[tuple], int]:
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT TOP {int(limit)} * FROM {source_view}")

        columns = [col[0] for col in cursor.description]
        rows = [tuple(row) for row in cursor.fetchall()]

        cursor.execute(f"SELECT COUNT(*) FROM {source_view}")
        total_count = cursor.fetchone()[0]

        return columns, rows, total_count


async def fetch_view_rows(
    connection_string: str, source_view: str, limit: int = 200
) -> tuple[list[str], list[tuple], int]:
    return await asyncio.to_thread(_fetch_view_sync, connection_string, source_view, limit)


SERVICE_CALL_SOURCE_COLUMNS = [
    "cliente_codigo",
    "contrato_codigo",
    "asunto",
    "articulo_codigo",
    "numero_serie_fabricante",
    "origen",
    "status_equipo",
    "tipo_servicio",
    "orden_compra",
    "fecha_planificada",
]


def _fetch_service_call_source_rows_sync(connection_string: str, source_view: str) -> list[tuple]:
    columns_sql = ", ".join(SERVICE_CALL_SOURCE_COLUMNS)

    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {columns_sql} FROM {source_view}")

        return [tuple(row) for row in cursor.fetchall()]


async def fetch_service_call_source_rows(connection_string: str, source_view: str) -> list[tuple]:
    """Lee las filas de la vista de origen con las mismas 10 columnas fijas que usaba
    el proyecto LCDM.ServiceCalls original (ServiceCallSourceReader)."""
    return await asyncio.to_thread(_fetch_service_call_source_rows_sync, connection_string, source_view)
