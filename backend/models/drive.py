"""
backend/models/drive.py

PlacementDrive model representing a recruitment drive created by a company.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from backend.extensions import db


class PlacementDrive(db.Model):
    """
    Represents a single recruitment drive created by a company.

    Must be approved by admin before students can see and apply.
    """

    __tablename__ = "placement_drives"

    # Integer primary key.
    id = db.Column(db.Integer, primary_key=True)

    # FK → CompanyProfile.id, not null.
    company_id = db.Column(db.Integer, db.ForeignKey("company_profiles.id"), nullable=False, index=True)

    # String(100) — e.g. "Software Engineer".
    job_title = db.Column(db.String(100), nullable=False, index=True)

    # Text — job description.
    job_description = db.Column(db.Text, nullable=False)

    # String(200) — comma-separated, e.g. "CSE,ECE,EE".
    eligible_branches = db.Column(db.String(200), nullable=False)

    # Float — minimum CGPA to apply, e.g. 7.0.
    min_cgpa = db.Column(db.Float, nullable=False)

    # Integer — eligible passout year (e.g., 2027). Kept as eligible_year column for DB compatibility.
    eligible_year = db.Column(db.Integer, nullable=False)

    # Float — CTC in LPA, e.g. 12.5.
    package_lpa = db.Column(db.Float, nullable=False)

    # DateTime — last date to apply.
    application_deadline = db.Column(db.DateTime, nullable=False, index=True)

    # String(20) — 'pending', 'approved', 'closed' (and 'rejected' when admin rejects).
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    # String(300), nullable — filled when admin rejects.
    rejection_reason = db.Column(db.String(300), nullable=True)

    # DateTime, default utcnow.
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship: a drive can have many applications.
    applications = db.relationship(
        "Application", backref="drive", cascade="all, delete-orphan"
    )

    def to_dict(self, include_company: bool = False) -> Dict[str, Any]:
        """
        Serialize the PlacementDrive into a dictionary for API responses.

        Parameters:
            include_company (bool): If True, includes nested company profile summary.

        Returns:
            Dict[str, Any]: Placement drive data, with ISO formatted datetimes.
        """
        payload: Dict[str, Any] = {
            "id": self.id,
            "company_id": self.company_id,
            "job_title": self.job_title,
            "job_description": self.job_description,
            "eligible_branches": self.eligible_branches,
            "min_cgpa": self.min_cgpa,
            # Backward-compatible keys: UI uses eligible_passout_year; DB column is eligible_year.
            "eligible_year": self.eligible_year,
            "eligible_passout_year": self.eligible_year,
            "package_lpa": self.package_lpa,
            "application_deadline": self.application_deadline.isoformat() if self.application_deadline else None,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_company and getattr(self, "company", None) is not None:
            payload["company"] = {
                "id": self.company.id,
                "company_name": self.company.company_name,
                "hr_name": self.company.hr_name,
                "hr_email": self.company.hr_email,
                "approval_status": self.company.approval_status,
            }

        return payload

