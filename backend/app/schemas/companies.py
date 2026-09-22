from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    service_layer_url: HttpUrl
    company_db: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)


class CompanyUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    service_layer_url: HttpUrl
    company_db: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=1, max_length=100)
    password: str | None = None
    is_active: bool = True


class CompanyOut(BaseModel):
    id: int
    name: str
    service_layer_url: str
    company_db: str
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    has_password: bool
