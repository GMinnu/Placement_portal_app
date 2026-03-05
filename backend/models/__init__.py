"""
backend/models/__init__.py

SQLAlchemy model package initializer.

Importing all model classes here ensures SQLAlchemy registers them before
db.create_all() is executed in the Flask app factory.
"""

from __future__ import annotations

# Import order is not strictly required, but kept explicit for clarity.
from backend.models.user import User  # noqa: F401
from backend.models.student import StudentProfile  # noqa: F401
from backend.models.company import CompanyProfile  # noqa: F401
from backend.models.drive import PlacementDrive  # noqa: F401
from backend.models.application import Application  # noqa: F401
from backend.models.export_job import ExportJob  # noqa: F401

