from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunServiceCallTaskRequest(BaseModel):
    batch_size: int | None = Field(default=None, ge=1, le=50)
    dry_run: bool = False


class RunServiceCallTaskResponse(BaseModel):
    execution_id: int


class ServiceCallExecutionOut(BaseModel):
    id: int
    task_id: int
    task_name: str
    trigger_type: Literal["manual", "scheduled"]
    status: Literal["running", "completed", "completed_with_errors", "failed"]
    dry_run: bool
    batch_size: int
    total_items: int
    successful_items: int
    failed_items: int
    review_items: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class ServiceCallExecutionItemOut(BaseModel):
    id: int
    sequence: int
    source_key: str
    payload_json: dict[str, Any]
    status: Literal["pending", "processing", "succeeded", "failed", "needs_review"]
    attempt_count: int
    http_status_code: int | None
    sap_response: str | None
    processed_at: datetime | None
