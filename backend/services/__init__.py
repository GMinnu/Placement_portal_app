"""
backend/services/__init__.py

Service package initializer.

This module imports the main service modules so they can be accessed via
`backend.services.*` and so that statements like `from backend.services import auth_service`
resolve correctly.
"""

from __future__ import annotations

from . import auth_service  # noqa: F401
from . import eligibility_service  # noqa: F401
from . import email_service  # noqa: F401
from . import offer_letter_service  # noqa: F401
from . import export_service  # noqa: F401

