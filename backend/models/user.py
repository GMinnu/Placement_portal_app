"""
backend/models/user.py

Unified User model for all roles (admin, company, student).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db


class User(db.Model):
    """
    Stores login credentials for ALL roles (admin, company, student).

    Role is differentiated by the 'role' field — never create separate login tables.
    """

    __tablename__ = "users"

    # Integer primary key.
    id = db.Column(db.Integer, primary_key=True)

    # String(120), unique, not null — used as username for login.
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # String(256) — Werkzeug hashed password, NEVER store plaintext.
    password_hash = db.Column(db.String(256), nullable=False)

    # String(20) — exactly one of: 'admin', 'company', 'student'.
    role = db.Column(db.String(20), nullable=False, index=True)

    # Boolean, default True — set False to deactivate/blacklist.
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Boolean, default False — admin can blacklist users.
    is_blacklisted = db.Column(db.Boolean, nullable=False, default=False)

    # DateTime, default utcnow.
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # 1-to-1 relationship to StudentProfile (only for role='student').
    student_profile = db.relationship(
        "StudentProfile", backref="user", uselist=False, cascade="all, delete-orphan"
    )

    # 1-to-1 relationship to CompanyProfile (only for role='company').
    company_profile = db.relationship(
        "CompanyProfile", backref="user", uselist=False, cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """
        Hash and set the user's password.

        Parameters:
            password (str): Plaintext password provided during registration/password change.

        Returns:
            None. Updates the password_hash field with a secure hash.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """
        Verify a plaintext password against this user's stored hash.

        Parameters:
            password (str): Plaintext password to verify.

        Returns:
            bool: True if password matches the stored hash, else False.
        """
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the User into a safe dictionary for API responses.

        Parameters:
            None

        Returns:
            Dict[str, Any]: User data excluding sensitive fields like password_hash.
        """
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "is_blacklisted": self.is_blacklisted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

