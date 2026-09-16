import pytest
from pydantic import ValidationError

from app.schemas.tasks import ScheduleIn, TaskCreate, TaskReportIn


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


def test_schedule_in_accepts_valid_cron_expression():
    schedule = ScheduleIn(cron_expression="0 8 * * *")

    assert schedule.cron_expression == "0 8 * * *"


def test_schedule_in_rejects_out_of_range_cron_value():
    with pytest.raises(ValidationError):
        ScheduleIn(cron_expression="99 8 * * *")


def test_schedule_in_rejects_cron_with_wrong_field_count():
    with pytest.raises(ValidationError):
        ScheduleIn(cron_expression="0 8 *")
