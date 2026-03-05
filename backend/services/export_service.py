"""
backend/services/export_service.py

CSV export builder for student applications.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from sqlalchemy.orm import joinedload

from backend.config import Config
from backend.models.application import Application
from backend.models.student import StudentProfile
from backend.models.drive import PlacementDrive


def build_csv_for_student(student_id: int) -> str:
    """
    Build a CSV file containing all applications for the given student.

    CSV Columns:
      Student ID, Student Name, Roll Number, Company Name,
      Job Title, Package LPA, Application Date, Status

    Parameters:
        student_id (int): StudentProfile primary key id.

    Returns:
        str: Relative file path to the generated CSV under backend/exports/.
    """
    student = StudentProfile.query.get(int(student_id))
    if student is None:
        raise ValueError("Student not found.")

    applications: List[Application] = (
        Application.query.options(
            joinedload(Application.drive).joinedload(PlacementDrive.company),
            joinedload(Application.student),
        )
        .filter_by(student_id=student.id)
        .order_by(Application.applied_at.desc())
        .all()
    )

    Config.ensure_storage_directories()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"student_{student.id}_{timestamp}.csv"
    output_path = Path(Config.EXPORTS_FOLDER) / filename

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Student ID",
                "Student Name",
                "Roll Number",
                "Company Name",
                "Job Title",
                "Package LPA",
                "Application Date",
                "Status",
            ]
        )

        for app in applications:
            drive = app.drive
            company = getattr(drive, "company", None) if drive else None
            writer.writerow(
                [
                    student.id,
                    student.full_name,
                    student.roll_number,
                    company.company_name if company else "",
                    drive.job_title if drive else "",
                    drive.package_lpa if drive else "",
                    app.applied_at.isoformat() if app.applied_at else "",
                    app.status,
                ]
            )

    return f"exports/{filename}"

