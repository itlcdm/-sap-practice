import json

import asyncpg

from app.config import settings


class DBService:

    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def guardar_inventario_articulo(
        self,
        codigo_articulo: str,
        nombre_articulo: str,
        grupo: str,
        unidad_venta: str,
        unidad_compra: str,
        almacen_predeterminado: str,
        activo: bool,
        bodegas: list[dict],
    ):

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CALL sp_guardar_inventario_articulo(
                    $1, $2, $3, $4, $5, $6, $7, $8::jsonb
                )
                """,
                codigo_articulo,
                nombre_articulo,
                grupo,
                unidad_venta,
                unidad_compra,
                almacen_predeterminado,
                activo,
                json.dumps(bodegas),
            )


db_service = DBService()
