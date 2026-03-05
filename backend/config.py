"""
backend/config.py

Central configuration for the IIT Madras Placement Portal backend.

This module defines the Config class used by the Flask application factory and
Celery worker to consistently load environment variables and derive key paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv


class Config:
    """
    Configuration container for Flask and Celery.

    This class reads environment variables (optionally via a .env file),
    defines defaults aligned with docker-compose.yml, and provides absolute
    paths for backend folders (uploads/exports/offer_letters).
    """

    # Load environment variables from a local .env if present.
    load_dotenv()

    # Base directory for the backend package (placement_portal/backend).
    BACKEND_DIR: Path = Path(__file__).resolve().parent

    # Flask secret key used for session/cookies (even though API uses JWT).
    SECRET_KEY: str = os.getenv("SECRET_KEY", "iitm-placement-secret-2024")

    # JWT signing secret key.
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "iitm-jwt-secret-2024")

    # SQLAlchemy database URL; defaults to SQLite file in backend working directory.
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "sqlite:///placement_portal.db")

    # SQLAlchemy tracking modifications flag (kept False for performance).
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Redis connection URL used by Flask-Caching and Celery broker.
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Flask-Caching configuration (Redis backend).
    CACHE_TYPE: str = "RedisCache"
    CACHE_REDIS_URL: str = REDIS_URL

    # Mail (SMTP) configuration for Flask-Mail.
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS: bool = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME: str | None = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: str | None = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER: str | None = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # Admin email (recipient for monthly report and system notifications).
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@iitm.ac.in")

    # Filesystem folders for uploads/exports/offer letters.
    UPLOAD_FOLDER: str = str((BACKEND_DIR / "uploads").resolve())
    EXPORTS_FOLDER: str = str((BACKEND_DIR / "exports").resolve())
    OFFER_LETTERS_FOLDER: str = str((BACKEND_DIR / "offer_letters").resolve())

    # Maximum upload size (resume): 5 MB.
    MAX_CONTENT_LENGTH: int = 5 * 1024 * 1024

    # Celery configuration (Redis as broker; RPC backend is fine for small apps).
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

    @staticmethod
    def ensure_storage_directories() -> None:
        """
        Ensure required backend storage directories exist.

        Parameters:
            None

        Returns:
            None. Creates directories for uploads, exports, and offer letters if missing.
        """
        Path(Config.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(Config.EXPORTS_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(Config.OFFER_LETTERS_FOLDER).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def to_flask_config_dict() -> Dict[str, object]:
        """
        Convert Config into a Flask-compatible config mapping.

        Parameters:
            None

        Returns:
            Dict[str, object]: A dictionary suitable for app.config.from_mapping(...).
        """
        return {
            "SECRET_KEY": Config.SECRET_KEY,
            "JWT_SECRET_KEY": Config.JWT_SECRET_KEY,
            "SQLALCHEMY_DATABASE_URI": Config.SQLALCHEMY_DATABASE_URI,
            "SQLALCHEMY_TRACK_MODIFICATIONS": Config.SQLALCHEMY_TRACK_MODIFICATIONS,
            "CACHE_TYPE": Config.CACHE_TYPE,
            "CACHE_REDIS_URL": Config.CACHE_REDIS_URL,
            "MAIL_SERVER": Config.MAIL_SERVER,
            "MAIL_PORT": Config.MAIL_PORT,
            "MAIL_USE_TLS": Config.MAIL_USE_TLS,
            "MAIL_USERNAME": Config.MAIL_USERNAME,
            "MAIL_PASSWORD": Config.MAIL_PASSWORD,
            "MAIL_DEFAULT_SENDER": Config.MAIL_DEFAULT_SENDER,
            "ADMIN_EMAIL": Config.ADMIN_EMAIL,
            "UPLOAD_FOLDER": Config.UPLOAD_FOLDER,
            "EXPORTS_FOLDER": Config.EXPORTS_FOLDER,
            "OFFER_LETTERS_FOLDER": Config.OFFER_LETTERS_FOLDER,
            "MAX_CONTENT_LENGTH": Config.MAX_CONTENT_LENGTH,
        }

    @staticmethod
    def to_celery_config_dict() -> Dict[str, object]:
        """
        Convert Config into a Celery-compatible configuration mapping.

        Parameters:
            None

        Returns:
            Dict[str, object]: A dictionary for configuring a Celery app.
        """
        return {
            "broker_url": Config.CELERY_BROKER_URL,
            "result_backend": Config.CELERY_RESULT_BACKEND,
            "timezone": "Asia/Kolkata",
            "enable_utc": True,
        }

