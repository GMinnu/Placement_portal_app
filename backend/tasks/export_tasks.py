"""
backend/tasks/export_tasks.py

Celery task: async CSV export, update ExportJob status.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.extensions import celery, db
from backend.models.export_job import ExportJob
from backend.services.export_service import build_csv_for_student


@celery.task(name="backend.tasks.export_tasks.generate_csv_export")
def generate_csv_export(export_job_id: int) -> dict:
    """
    Triggered when student clicks "Export Applications".
    Fetches ExportJob by id, sets status='pending'.
    Queries all applications for the student with:
      Student ID, Student Name, Roll Number, Company Name,
      Job Title, Package LPA, Application Date, Status
    Writes CSV to backend/exports/student_<student_id>_<timestamp>.csv
    Updates ExportJob: status='done', file_path=<path>, completed_at=now
    If any error: status='failed'

    Parameters:
        export_job_id (int): ExportJob primary key id.

    Returns:
        dict: Summary containing export_job_id and final status.
    """
    job = ExportJob.query.get(int(export_job_id))
    if job is None:
        return {"export_job_id": export_job_id, "status": "failed", "error": "ExportJob not found."}

    try:
        job.status = "pending"
        db.session.commit()

        rel_path = build_csv_for_student(job.student_id)
        job.status = "done"
        job.file_path = rel_path
        job.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return {"export_job_id": job.id, "status": job.status, "file_path": job.file_path}
    except Exception as e:
        job.status = "failed"
        job.file_path = None
        job.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return {"export_job_id": job.id, "status": job.status, "error": str(e)}

