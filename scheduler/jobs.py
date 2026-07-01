from __future__ import annotations

from typing import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger


def start_scheduler(job: Callable[[], None], cron: str, timezone: str) -> None:
    scheduler = BlockingScheduler(timezone=timezone)
    scheduler.add_job(job, CronTrigger.from_crontab(cron, timezone=timezone), id="daily-analysis", replace_existing=True)
    print(f"Scheduler started. Cron: {cron}, timezone: {timezone}")
    scheduler.start()
