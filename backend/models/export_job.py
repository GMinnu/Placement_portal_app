"""
backend/models/export_job.py

ExportJob model tracking async CSV export status for a student.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from backend.extensions import db


class ExportJob(db.Model):
    """
    Tracks the state of an async CSV export request made by a student.

    Frontend polls this to know when the file is ready to download.
    """

    __tablename__ = "export_jobs"

    # Integer primary key.
    id = db.Column(db.Integer, primary_key=True)

    # FK → StudentProfile.id, not null.
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True)

    # String(20) — 'pending', 'done', 'failed'.
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    # String(256), nullable — set when done.
    file_path = db.Column(db.String(256), nullable=True)

    # DateTime, default utcnow.
    requested_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # DateTime, nullable — set when done or failed.
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the ExportJob into a dictionary for API responses.

        Parameters:
            None

        Returns:
            Dict[str, Any]: Export job status and file path (if available).
        """
        return {
            "id": self.id,
            "student_id": self.student_id,
            "status": self.status,
            "file_path": self.file_path,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

