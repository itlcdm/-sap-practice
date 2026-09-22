from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CurrencyTaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company_id: int
    local_currency: str = Field(default="USD", min_length=3, max_length=3)
    target_currencies: list[str] = Field(min_length=1)
    rate_api_url: str = "https://v6.exchangerate-api.com/v6/7351996bac331d17f404e7ff/pair"
    run_at: time = time(8, 0)
    mail_to: str = Field(min_length=1)
    mail_cc: str | None = None

    @field_validator("local_currency")
    @classmethod
    def normalize_local_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("target_currencies")
    @classmethod
    def normalize_targets(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.upper() for value in values if value.strip()))


class CurrencyTaskUpdate(CurrencyTaskCreate):
    is_active: bool = True


class CurrencyTaskOut(BaseModel):
    id: int
    name: str
    company_id: int
    company_name: str
    company_db: str
    local_currency: str
    target_currencies: list[str]
    rate_api_url: str
    run_at: time
    mail_to: str
    mail_cc: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CurrencyExecutionOut(BaseModel):
    id: int
    currency_task_id: int
    task_name: str
    company_name: str
    trigger_type: Literal["manual", "scheduled"]
    status: Literal["running", "success", "failed"]
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None
    updated_rates: list[str] = []
