from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator

VALID_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class ServiceCallTaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company_id: int
    connection_name: str = "InventarioDb"
    source_view: str = Field(min_length=1, max_length=200)
    run_at: time = time(8, 0)
    schedule_type: Literal["weekly", "monthly"] = "weekly"
    run_days: list[str] = Field(default_factory=lambda: list(VALID_WEEKDAYS))
    run_day_of_month: int | None = Field(default=None, ge=1, le=28)
    mail_to: str = Field(min_length=1)
    mail_cc: str | None = None

    @model_validator(mode="after")
    def validar_programacion(self) -> "ServiceCallTaskCreate":
        if self.schedule_type == "weekly":
            normalized = [day.lower() for day in self.run_days]
            invalid = [day for day in normalized if day not in VALID_WEEKDAYS]
            if invalid:
                raise ValueError(f"Días inválidos: {', '.join(invalid)}")
            if not normalized:
                raise ValueError("Selecciona al menos un día de la semana")
            self.run_days = [day for day in VALID_WEEKDAYS if day in normalized]
            self.run_day_of_month = None
        else:
            if self.run_day_of_month is None:
                raise ValueError("Selecciona el día del mes (1 a 28)")
            self.run_days = []

        return self


class ServiceCallTaskUpdate(ServiceCallTaskCreate):
    is_active: bool = True


class ServiceCallTaskOut(BaseModel):
    id: int
    name: str
    company_id: int
    company_name: str
    connection_name: str
    source_view: str
    run_at: time
    schedule_type: Literal["weekly", "monthly"]
    run_days: list[str]
    run_day_of_month: int | None
    mail_to: str
    mail_cc: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
