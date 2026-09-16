import pytest
from pydantic import ValidationError

from app.schemas.tasks import TaskCreate, TaskReportIn


def _report(sp="ALCONSIT"):
    return TaskReportIn(
        stored_procedure=sp,
        excel_file_name="ALCONSIT.xlsx",
        sheet_name="ALCONSIT",
    )


def test_task_create_accepts_one_or_more_reports():
    task = TaskCreate(
        name="Inventario diario",
        connection_name="InventarioDb",
        mail_to="a@example.com",
        reports=[_report("ALCONSIT"), _report("ALCONIMS")],
    )

    assert len(task.reports) == 2


def test_task_create_rejects_empty_reports():
    with pytest.raises(ValidationError):
        TaskCreate(
            name="Inventario diario",
            connection_name="InventarioDb",
            mail_to="a@example.com",
            reports=[],
        )
