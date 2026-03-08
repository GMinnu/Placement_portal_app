"""
backend/run_celery_email_test.py

Small helper script to manually trigger Celery email-related tasks and verify
that the mail + Celery setup is working end to end.

Usage (from the backend directory):
    python -m backend.run_celery_email_test

Make sure that:
  - Redis / broker is running.
  - The celery worker service is running (e.g. `celery -A backend.tasks.celery_worker.celery worker` or via docker-compose).
  - MAIL_* settings in your Flask config are valid so emails can be sent.
"""

from __future__ import annotations

from typing import Any

from backend.extensions import celery


def trigger_task(task_name: str, *args: Any, **kwargs: Any) -> None:
    """
    Helper to enqueue a Celery task by its full dotted name.

    Example:
        trigger_task("backend.tasks.reminder_tasks.send_deadline_reminders")
    """
    result = celery.send_task(task_name, args=args, kwargs=kwargs)
    print(f"Enqueued task '{task_name}' with id: {result.id}")


def main() -> None:
    """
    Entry point to enqueue simple email-related Celery tasks for testing.

    Adjust the `task_to_run` and parameters below depending on what you want
    to verify:
      - Daily deadline reminders
      - Monthly admin report
    """
    # Example 1: trigger daily reminder emails task.
    task_to_run = "backend.tasks.reminder_tasks.send_deadline_reminders"

    # Example 2: to test monthly report email instead, comment the above line
    # and uncomment this one:
    # task_to_run = "backend.tasks.monthly_report_tasks.send_monthly_report"

    print("Using Celery broker:", celery.conf.broker_url)
    print("Using Celery backend:", celery.conf.result_backend)

    trigger_task(task_to_run)


if __name__ == "__main__":
    main()

