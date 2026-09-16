from fastapi import APIRouter, HTTPException

from app.services.db_service import db_service
from app.schemas.inventory import SaveInventoryRequest


router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory"]
)


@router.post("/save")
async def save_inventory(payload: SaveInventoryRequest):

    try:

        await db_service.guardar_inventario_articulo(
            codigo_articulo=payload.codigo_articulo,
            nombre_articulo=payload.nombre_articulo,
            grupo=payload.grupo,
            unidad_venta=payload.unidad_venta,
            unidad_compra=payload.unidad_compra,
            almacen_predeterminado=payload.almacen_predeterminado,
            activo=payload.activo,
            bodegas=[b.model_dump() for b in payload.bodegas],
        )

        return {"ok": True}

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
