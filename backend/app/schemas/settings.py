from datetime import datetime

from pydantic import BaseModel, Field


class AppSettingsOut(BaseModel):
    timezone_offset_hours: int
    default_batch_size: int
    max_retry_attempts: int
    updated_at: datetime


class AppSettingsUpdate(BaseModel):
    timezone_offset_hours: int = Field(ge=-12, le=14)
    default_batch_size: int = Field(ge=1, le=50)
    max_retry_attempts: int = Field(ge=1, le=20)


class MailSettingsOut(BaseModel):
    smtp_server: str
    smtp_port: int
    mail_user: str
    mail_from: str
    password_configured: bool


class MailSettingsUpdate(BaseModel):
    smtp_server: str = Field(min_length=1)
    smtp_port: int = Field(ge=1, le=65535)
    mail_user: str = Field(min_length=1)
    mail_from: str = Field(min_length=1)
    mail_password: str | None = None


class TestEmailRequest(BaseModel):
    to: str = Field(min_length=3)


class PostgresSettingsOut(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password_configured: bool


class AuthInfoOut(BaseModel):
    enabled: bool
    note: str
