"""
backend/tasks/reminder_tasks.py

Celery task: send daily deadline reminder emails.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Set

from sqlalchemy.orm import joinedload

from backend.extensions import celery, db
from backend.models.application import Application
from backend.models.drive import PlacementDrive
from backend.models.student import StudentProfile
from backend.services.eligibility_service import check_eligibility
from backend.services.email_service import send_deadline_reminder


@celery.task(name="backend.tasks.reminder_tasks.send_deadline_reminders")
def send_deadline_reminders() -> dict:
    """
    Runs daily at 8:00 AM via Celery Beat.
    Finds all approved drives with deadline within next 3 days.
    For each such drive, finds eligible students who haven't applied yet.
    Sends an HTML reminder email to each such student.
    Email subject: "Reminder: {job_title} at {company_name} — Deadline in X days"

    Parameters:
        None.

    Returns:
        dict: Summary containing counts of drives processed and emails attempted.
    """
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=3)

    drives: List[PlacementDrive] = (
        PlacementDrive.query.options(joinedload(PlacementDrive.company))
        .filter(
            PlacementDrive.status == "approved",
            PlacementDrive.application_deadline >= now,
            PlacementDrive.application_deadline <= window_end,
        )
        .all()
    )

    students: List[StudentProfile] = StudentProfile.query.options(joinedload(StudentProfile.user)).all()
    emails_sent = 0

    for drive in drives:
        if drive.company is None:
            continue

        applied_student_ids: Set[int] = {
            int(sid)
            for (sid,) in db.session.query(Application.student_id)
            .filter(Application.drive_id == drive.id)
            .all()
        }

        deadline_dt = drive.application_deadline
        if deadline_dt is None:
            continue

        days_left = max(0, (deadline_dt.replace(tzinfo=timezone.utc) - now).days)
        deadline_display = deadline_dt.strftime("%d %b %Y, %I:%M %p")

        for student in students:
            if student.user is None:
                continue
            if not student.user.is_active or student.user.is_blacklisted:
                continue
            if student.id in applied_student_ids:
                continue

            is_ok, _reason = check_eligibility(student, drive)
            if not is_ok:
                continue

            send_deadline_reminder(
                student_name=student.full_name,
                student_email=student.user.email,
                job_title=drive.job_title,
                company_name=drive.company.company_name,
                days_left=days_left,
                deadline=deadline_display,
            )
            emails_sent += 1

    return {"drives_in_window": len(drives), "emails_sent": emails_sent}

