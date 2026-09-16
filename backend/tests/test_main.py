from fastapi.routing import iter_route_contexts

from app.main import app


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
