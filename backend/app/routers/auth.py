from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas.auth import LoginRequest


router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)


@router.post("/login")
async def login(credentials: LoginRequest):

    if (
        credentials.email != settings.admin_email
        or credentials.password != settings.admin_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos"
        )

    return {"ok": True}
