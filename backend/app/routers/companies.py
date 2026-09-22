import logging

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.companies import CompanyCreate, CompanyOut, CompanyUpdate
from app.services.company_repository import CompanyRepository, company_repository

router = APIRouter(prefix="/api/companies", tags=["Companies"])
logger = logging.getLogger(__name__)


def get_company_repository() -> CompanyRepository:
    return company_repository


@router.get("", response_model=list[CompanyOut])
async def list_companies(repo: CompanyRepository = Depends(get_company_repository)):
    return await repo.list_companies()


@router.post("", response_model=CompanyOut, status_code=201)
async def create_company(
    payload: CompanyCreate,
    repo: CompanyRepository = Depends(get_company_repository),
):
    try:
        company_id = await repo.create_company(payload)
    except Exception as exc:
        if "duplicate key" in str(exc).lower() or "unique" in str(exc).lower():
            raise HTTPException(status_code=409, detail="La base de datos ya está registrada") from exc
        raise
    company = await repo.get_company(company_id)
    return company


@router.put("/{company_id}", response_model=CompanyOut)
async def update_company(
    company_id: int,
    payload: CompanyUpdate,
    repo: CompanyRepository = Depends(get_company_repository),
):
    if await repo.get_company(company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    await repo.update_company(company_id, payload)
    return await repo.get_company(company_id)


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: int,
    repo: CompanyRepository = Depends(get_company_repository),
):
    if await repo.get_company(company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    await repo.delete_company(company_id)


@router.post("/{company_id}/test-connection")
async def test_company_connection(
    company_id: int,
    repo: CompanyRepository = Depends(get_company_repository),
):
    logger.info("[EMPRESAS] Solicitud HTTP para probar conexión: company_id=%s", company_id)
    try:
        await repo.test_connection(company_id)
    except LookupError as exc:
        logger.warning("[EMPRESAS] Prueba rechazada: company_id=%s motivo=%s", company_id, exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[EMPRESAS] Falló la prueba de conexión: company_id=%s", company_id)
        raise HTTPException(status_code=502, detail=f"No se pudo conectar al Service Layer: {exc}") from exc
    logger.info("[EMPRESAS] Respuesta exitosa de prueba: company_id=%s", company_id)
    return {"ok": True, "message": "Conexión exitosa"}
