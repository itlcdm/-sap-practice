from fastapi.routing import iter_route_contexts

import app.main as main
from app.main import app


def patch_lifespan_dependencies(monkeypatch, schedules=None, schedule_task=None):
    """Replace every external side effect of `lifespan` with an in-memory double.

    `lifespan` talks to Postgres and starts a real APScheduler, so the only way
    to exercise it in this suite (which has no live DB) is to stub the two
    singletons it uses. Returns the ordered list of calls it made.
    """
    calls = []

    async def fake_connect():
        calls.append("connect")

    async def fake_disconnect():
        calls.append("disconnect")

    async def fake_mark_stale_running_as_failed():
        calls.append("mark_stale_running_as_failed")

    async def fake_list_active_schedules():
        calls.append("list_active_schedules")
        return schedules or []

    def default_schedule_task(task_id, cron_expression):
        calls.append(("schedule_task", task_id, cron_expression))

    monkeypatch.setattr(main.db_service, "connect", fake_connect)
    monkeypatch.setattr(main.db_service, "disconnect", fake_disconnect)
    monkeypatch.setattr(
        main.task_repository, "mark_stale_running_as_failed", fake_mark_stale_running_as_failed
    )
    monkeypatch.setattr(main.task_repository, "list_active_schedules", fake_list_active_schedules)
    monkeypatch.setattr(
        main.scheduler_service, "schedule_task", schedule_task or default_schedule_task
    )
    monkeypatch.setattr(main.scheduler_service, "start", lambda: calls.append("start"))
    monkeypatch.setattr(main.scheduler_service, "shutdown", lambda: calls.append("shutdown"))

    return calls


def test_task_and_execution_routes_are_registered():
    # app.routes does not expose nested/included-router paths directly on this
    # FastAPI version (they are lazily wrapped in `_IncludedRouter` entries),
    # so we flatten via the public `iter_route_contexts` helper instead of
    # reading `route.path` directly off `app.routes`.
    paths = {ctx.path for ctx in iter_route_contexts(app.routes)}

    assert "/api/tasks" in paths
    assert "/api/tasks/{task_id}" in paths
    assert "/api/tasks/{task_id}/schedule" in paths
    assert "/api/tasks/{task_id}/run" in paths
    assert "/api/schedules" in paths
    assert "/api/executions" in paths
    assert "/api/executions/{execution_id}" in paths
    assert "/api/executions/{execution_id}/logs" in paths
    assert "/api/executions/{execution_id}/reports/{report_id}/download" in paths


async def test_lifespan_marks_stale_running_executions_before_starting_scheduler(monkeypatch):
    calls = patch_lifespan_dependencies(monkeypatch)

    async with main.lifespan(app):
        pass

    assert "mark_stale_running_as_failed" in calls
    assert calls.index("connect") < calls.index("mark_stale_running_as_failed")
    assert calls.index("mark_stale_running_as_failed") < calls.index("start")


async def test_lifespan_skips_schedule_with_invalid_cron_and_keeps_going(monkeypatch):
    def failing_schedule_task(task_id, cron_expression):
        if cron_expression == "99 8 * * *":
            raise ValueError("the last value (99) is higher than the maximum value (59)")
        scheduled.append(task_id)

    scheduled = []
    calls = patch_lifespan_dependencies(
        monkeypatch,
        schedules=[
            {"task_id": 1, "cron_expression": "99 8 * * *"},
            {"task_id": 2, "cron_expression": "0 8 * * *"},
        ],
        schedule_task=failing_schedule_task,
    )

    async with main.lifespan(app):
        pass

    # La fila inválida no tumba el arranque: la siguiente se registra igual.
    assert scheduled == [2]
    assert "start" in calls
