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
