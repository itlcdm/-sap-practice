from datetime import datetime

from pydantic import BaseModel, Field


class SqlConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    driver: str = Field(default="ODBC Driver 17 for SQL Server", min_length=1)
    server: str = Field(min_length=1)
    database: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    extra_params: str = "TrustServerCertificate=yes;"


class SqlConnectionUpdate(BaseModel):
    driver: str = Field(default="ODBC Driver 17 for SQL Server", min_length=1)
    server: str = Field(min_length=1)
    database: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str | None = None
    extra_params: str = "TrustServerCertificate=yes;"


class SqlConnectionOut(BaseModel):
    id: int
    name: str
    driver: str
    server: str
    database: str
    username: str
    password_configured: bool
    extra_params: str
    created_at: datetime
    updated_at: datetime
