from fastapi import APIRouter, HTTPException

from app.services.sap_service import sap_service


router = APIRouter(
    prefix="/api/warehouses",
    tags=["Warehouses"]
)


@router.get("")
async def list_warehouses():

    try:

        data = await sap_service.get(
            "Warehouses?$select=WarehouseCode,WarehouseName"
        )

        return data.get("value", [])

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
