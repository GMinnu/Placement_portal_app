"""
backend/models/application.py

Application model tracking each student's application to a placement drive.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from backend.extensions import db


class Application(db.Model):
    """
    Tracks each student's application to a placement drive.

    Unique constraint on (student_id, drive_id) prevents duplicate applications.
    """

    __tablename__ = "applications"

    # Integer primary key.
    id = db.Column(db.Integer, primary_key=True)

    # FK → StudentProfile.id, not null.
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True)

    # FK → PlacementDrive.id, not null.
    drive_id = db.Column(db.Integer, db.ForeignKey("placement_drives.id"), nullable=False, index=True)

    # DateTime, default utcnow.
    applied_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # String(20) — 'applied', 'shortlisted', 'selected', 'rejected'.
    status = db.Column(db.String(20), nullable=False, default="applied", index=True)

    # String(256), nullable — set when student is shortlisted.
    offer_letter_path = db.Column(db.String(256), nullable=True)

    # DateTime, onupdate=utcnow.
    updated_at = db.Column(
        db.DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("student_id", "drive_id", name="uq_application_student_drive"),
    )

    def to_dict(self, include_drive: bool = False, include_student: bool = False) -> Dict[str, Any]:
        """
        Serialize the Application into a dictionary for API responses.

        Parameters:
            include_drive (bool): If True, includes nested drive summary.
            include_student (bool): If True, includes nested student summary.

        Returns:
            Dict[str, Any]: Application data with optional nested summaries.
        """
        payload: Dict[str, Any] = {
            "id": self.id,
            "student_id": self.student_id,
            "drive_id": self.drive_id,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "status": self.status,
            "offer_letter_path": self.offer_letter_path,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_drive and getattr(self, "drive", None) is not None:
            company = getattr(self.drive, "company", None)
            payload["drive"] = {
                "id": self.drive.id,
                "job_title": self.drive.job_title,
                "package_lpa": self.drive.package_lpa,
                "status": self.drive.status,
                "application_deadline": self.drive.application_deadline.isoformat()
                if self.drive.application_deadline
                else None,
                "company": {
                    "id": company.id,
                    "company_name": company.company_name,
                }
                if company is not None
                else None,
            }

        if include_student and getattr(self, "student", None) is not None:
            resume_filename = (
                Path(self.student.resume_path).name
                if getattr(self.student, "resume_path", None)
                else None
            )
            payload["student"] = {
                "id": self.student.id,
                "full_name": self.student.full_name,
                "roll_number": self.student.roll_number,
                "branch": self.student.branch,
                "cgpa": self.student.cgpa,
                "year_of_study": self.student.year_of_study,
                "resume_filename": resume_filename,
            }
            payload["student"]["resume_url"] = (
                f"/api/company/applications/{self.id}/resume" if resume_filename else None
            )

        return payload

