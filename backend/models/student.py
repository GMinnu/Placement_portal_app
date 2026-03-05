"""
backend/models/student.py

StudentProfile model storing academic and personal details for students.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from backend.extensions import db


class StudentProfile(db.Model):
    """
    Stores academic and personal details for students.

    Linked 1-to-1 with User (role='student').
    """

    __tablename__ = "student_profiles"

    # Integer primary key.
    id = db.Column(db.Integer, primary_key=True)

    # FK → User.id, unique, not null.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    # String(100) — student's full name.
    full_name = db.Column(db.String(100), nullable=False)

    # String(20), unique — e.g. "CS21B001".
    roll_number = db.Column(db.String(20), unique=True, nullable=False, index=True)

    # String(50) — e.g. "CSE", "ECE", "ME", "EE", "CE".
    branch = db.Column(db.String(50), nullable=False, index=True)

    # Integer — stored as year_of_passout for demo (e.g., 2027). Kept as year_of_study column for DB compatibility.
    year_of_study = db.Column(db.Integer, nullable=False, index=True)

    # Float — e.g. 8.5.
    cgpa = db.Column(db.Float, nullable=False, index=True)

    # String(15) — phone number.
    phone = db.Column(db.String(15), nullable=False)

    # String(256), nullable — relative path inside backend/uploads/.
    resume_path = db.Column(db.String(256), nullable=True)

    # DateTime, default utcnow.
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # DateTime, onupdate=utcnow.
    updated_at = db.Column(
        db.DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship: a student can have many applications.
    applications = db.relationship(
        "Application", backref="student", cascade="all, delete-orphan"
    )

    # Relationship: a student can have many export jobs.
    export_jobs = db.relationship(
        "ExportJob", backref="student", cascade="all, delete-orphan"
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the StudentProfile into a dictionary for API responses.

        Parameters:
            None

        Returns:
            Dict[str, Any]: Student profile data (excluding large binary content).
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "roll_number": self.roll_number,
            "branch": self.branch,
            # Backward-compatible keys: UI uses year_of_passout; DB column is year_of_study.
            "year_of_study": self.year_of_study,
            "year_of_passout": self.year_of_study,
            "cgpa": self.cgpa,
            "phone": self.phone,
            "resume_path": self.resume_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

