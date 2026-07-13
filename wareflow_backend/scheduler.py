"""
scheduler.py
------------
Wires the Background System Processes (background_jobs.py) up to run
automatically, so nobody has to trigger them by hand in production.

Used by: app.py (started once, at process boot)
"""

from apscheduler.schedulers.background import BackgroundScheduler
from config import Config
import background_jobs as jobs

_scheduler = BackgroundScheduler()


def start_scheduler():
    _scheduler.add_job(
        jobs.low_stock_detection,
        "interval",
        minutes=Config.LOW_STOCK_CHECK_INTERVAL_MINUTES,
        id="low_stock_detection",
        replace_existing=True,
    )
    _scheduler.add_job(
        jobs.delay_detection,
        "interval",
        minutes=Config.DELAY_CHECK_INTERVAL_MINUTES,
        id="delay_detection",
        replace_existing=True,
    )
    # Batch completion + finished good generation run back-to-back, frequently,
    # since they're cheap checks and downstream pages depend on freshness.
    _scheduler.add_job(
        jobs.batch_completion,
        "interval",
        minutes=5,
        id="batch_completion",
        replace_existing=True,
    )
    _scheduler.add_job(
        jobs.finished_good_generation,
        "interval",
        minutes=5,
        id="finished_good_generation",
        replace_existing=True,
    )
    _scheduler.add_job(
        jobs.demand_prediction,
        "interval",
        hours=Config.DEMAND_FORECAST_INTERVAL_HOURS,
        id="demand_prediction",
        replace_existing=True,
    )

    _scheduler.start()
    return _scheduler


def shutdown_scheduler():
    if _scheduler.running:
        _scheduler.shutdown()
