import logging
import time

import httpx

from app.schemas.companies import CompanyCreate, CompanyOut, CompanyUpdate
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


class CompanyRepository:
    async def test_connection(self, company_id: int) -> None:
        started_at = time.perf_counter()
        logger.info("[EMPRESAS] Iniciando prueba de conexión: company_id=%s", company_id)

        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT service_layer_url, company_db, username, password
                FROM service_layer_companies WHERE id = $1 AND is_active
                """,
                company_id,
            )

        if row is None:
            logger.warning(
                "[EMPRESAS] Empresa no encontrada o inactiva: company_id=%s",
                company_id,
            )
            raise LookupError("Empresa no encontrada o inactiva")

        service_layer_url = row["service_layer_url"].rstrip("/")
        logger.info(
            "[EMPRESAS] Conectando al Service Layer: company_id=%s company_db=%s "
            "url=%s usuario=%s",
            company_id,
            row["company_db"],
            service_layer_url,
            row["username"],
        )

        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            response = await client.post(
                f"{service_layer_url}/Login",
                json={
                    "CompanyDB": row["company_db"],
                    "UserName": row["username"],
                    "Password": row["password"],
                },
            )
            response.raise_for_status()

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "[EMPRESAS] Conexión exitosa: company_id=%s company_db=%s "
            "status=%s duración_ms=%.0f",
            company_id,
            row["company_db"],
            response.status_code,
            elapsed_ms,
        )

    async def get_credentials(self, company_id: int) -> dict | None:
        """Uso interno de servicios de ejecución (nunca exponer vía API)."""
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT service_layer_url, company_db, username, password
                FROM service_layer_companies WHERE id = $1 AND is_active
                """,
                company_id,
            )
        return dict(row) if row else None

    async def list_companies(self) -> list[CompanyOut]:
        async with db_service.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, service_layer_url, company_db, username,
                       is_active, created_at, updated_at, password <> '' AS has_password
                FROM service_layer_companies
                ORDER BY name
                """
            )
        return [CompanyOut(**dict(row)) for row in rows]

    async def get_company(self, company_id: int) -> CompanyOut | None:
        async with db_service.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, service_layer_url, company_db, username,
                       is_active, created_at, updated_at, password <> '' AS has_password
                FROM service_layer_companies
                WHERE id = $1
                """,
                company_id,
            )
        return CompanyOut(**dict(row)) if row else None

    async def create_company(self, data: CompanyCreate) -> int:
        async with db_service.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO service_layer_companies
                    (name, service_layer_url, company_db, username, password)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                data.name,
                str(data.service_layer_url).rstrip("/"),
                data.company_db,
                data.username,
                data.password,
            )

    async def update_company(self, company_id: int, data: CompanyUpdate) -> None:
        async with db_service.pool.acquire() as conn:
            if data.password:
                await conn.execute(
                    """
                    UPDATE service_layer_companies
                    SET name = $2, service_layer_url = $3, company_db = $4,
                        username = $5, password = $6, is_active = $7, updated_at = now()
                    WHERE id = $1
                    """,
                    company_id,
                    data.name,
                    str(data.service_layer_url).rstrip("/"),
                    data.company_db,
                    data.username,
                    data.password,
                    data.is_active,
                )
            else:
                await conn.execute(
                    """
                    UPDATE service_layer_companies
                    SET name = $2, service_layer_url = $3, company_db = $4,
                        username = $5, is_active = $6, updated_at = now()
                    WHERE id = $1
                    """,
                    company_id,
                    data.name,
                    str(data.service_layer_url).rstrip("/"),
                    data.company_db,
                    data.username,
                    data.is_active,
                )

    async def delete_company(self, company_id: int) -> None:
        async with db_service.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM service_layer_companies WHERE id = $1", company_id
            )


company_repository = CompanyRepository()
