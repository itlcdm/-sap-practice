from fastapi import APIRouter, HTTPException

from app.services.sap_service import sap_service


router = APIRouter(
    prefix="/api/items",
    tags=["Items"]
)


@router.get("/{item_code}")
async def get_item(item_code: str):

    try:

        data = await sap_service.get(
            f"Items('{item_code}')"
        )

        return data

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )