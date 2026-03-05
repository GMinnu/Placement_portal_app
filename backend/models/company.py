"""
backend/models/company.py

CompanyProfile model storing company details and approval status.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from backend.extensions import db


class CompanyProfile(db.Model):
    """
    Stores details of companies that register on the platform.

    Linked 1-to-1 with User (role='company').
    Company cannot create drives until admin sets approval_status='approved'.
    """

    __tablename__ = "company_profiles"

    # Integer primary key.
    id = db.Column(db.Integer, primary_key=True)

    # FK → User.id, unique, not null.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    # String(100) — company name.
    company_name = db.Column(db.String(100), nullable=False, index=True)

    # String(100) — HR contact person's name.
    hr_name = db.Column(db.String(100), nullable=False, index=True)

    # String(120) — HR email for notifications.
    hr_email = db.Column(db.String(120), nullable=False)

    # String(200), nullable — company website URL.
    website = db.Column(db.String(200), nullable=True)

    # Text, nullable — about the company.
    description = db.Column(db.Text, nullable=True)

    # String(20) — 'pending', 'approved', 'rejected'.
    approval_status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    # String(300), nullable — filled when admin rejects.
    rejection_reason = db.Column(db.String(300), nullable=True)

    # DateTime, default utcnow.
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship: a company can create many placement drives.
    drives = db.relationship(
        "PlacementDrive", backref="company", cascade="all, delete-orphan"
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the CompanyProfile into a dictionary for API responses.

        Parameters:
            None

        Returns:
            Dict[str, Any]: Company profile data.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "hr_name": self.hr_name,
            "hr_email": self.hr_email,
            "website": self.website,
            "description": self.description,
            "approval_status": self.approval_status,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

