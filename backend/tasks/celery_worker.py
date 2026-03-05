"""
backend/tasks/celery_worker.py

Creates the Celery app instance and configures Beat schedule.
Beat schedule:
  - 'daily-reminders': runs send_deadline_reminders every day at 8:00 AM
  - 'monthly-report':  runs send_monthly_report on the 1st of every month at 7:00 AM
"""

from __future__ import annotations

from celery.schedules import crontab

from backend.config import Config
from backend.extensions import celery


def configure_celery() -> None:
    """
    Configure the global Celery instance using application configuration and beat schedule.

    Parameters:
        None.

    Returns:
        None. Updates the global Celery configuration in-place.
    """
    celery.conf.update(Config.to_celery_config_dict())

    celery.conf.beat_schedule = {
        "daily-reminders": {
            "task": "backend.tasks.reminder_tasks.send_deadline_reminders",
            "schedule": crontab(hour=8, minute=0),
        },
        "monthly-report": {
            "task": "backend.tasks.monthly_report_tasks.send_monthly_report",
            "schedule": crontab(day_of_month=1, hour=7, minute=0),
        },
    }


def make_celery_with_flask_context():
    """
    Bind Celery task execution to a Flask application context.

    This ensures tasks can use SQLAlchemy models, Flask-Mail, and configuration safely.

    Parameters:
        None.

    Returns:
        Celery: Configured Celery instance with task base wrapped in Flask app context.
    """
    from backend.app import create_app

    flask_app = create_app()
    configure_celery()

    class ContextTask(celery.Task):
        """
        Celery Task base that runs inside Flask app context.
        """

        def __call__(self, *args, **kwargs):
            """
            Execute the task within the Flask application context.

            Parameters:
                *args: Positional args passed to the task.
                **kwargs: Keyword args passed to the task.

            Returns:
                Any: Task return value.
            """
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# Initialize Celery configuration at import time for worker startup.
configure_celery()
celery = make_celery_with_flask_context()

