from app.services.scheduler_service import SchedulerService


async def test_schedule_task_sets_next_run_time():
    service = SchedulerService()
    service.start()

    try:
        service.schedule_task(1, "0 0 1 1 *")  # una vez al año

        assert service.get_next_run_time(1) is not None
    finally:
        service.shutdown()


async def test_unschedule_task_removes_job():
    service = SchedulerService()
    service.start()

    try:
        service.schedule_task(1, "0 0 1 1 *")
        service.unschedule_task(1)

        assert service.get_next_run_time(1) is None
    finally:
        service.shutdown()


async def test_get_next_run_time_none_when_never_scheduled():
    service = SchedulerService()
    service.start()

    try:
        assert service.get_next_run_time(999) is None
    finally:
        service.shutdown()
