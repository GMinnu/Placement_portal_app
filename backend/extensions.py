"""
backend/extensions.py

Flask extension singletons for the IIT Madras Placement Portal backend.

This module MUST NOT create/bind a Flask app; it only instantiates extensions
so they can be initialized inside the Flask app factory (create_app()).
"""

from __future__ import annotations

from celery import Celery
from flask_caching import Cache
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy


# SQLAlchemy database instance (bound in create_app()).
db: SQLAlchemy = SQLAlchemy()

# JWT manager instance (bound in create_app()).
jwt: JWTManager = JWTManager()

# Flask-Mail instance (bound in create_app()).
mail: Mail = Mail()

# Flask-Caching instance backed by Redis (bound in create_app()).
cache: Cache = Cache()

# Celery instance (configured in backend/tasks/celery_worker.py).
celery: Celery = Celery("placement_portal")


def init_celery_from_flask_config(flask_config: dict) -> None:
    """
    Initialize Celery configuration from a Flask config mapping.

    Parameters:
        flask_config (dict): Flask app.config mapping containing Celery settings
            like CELERY_BROKER_URL and CELERY_RESULT_BACKEND.

    Returns:
        None. Updates the global Celery instance configuration in-place.
    """
    broker_url = flask_config.get("CELERY_BROKER_URL")
    result_backend = flask_config.get("CELERY_RESULT_BACKEND")

    if broker_url:
        celery.conf.broker_url = broker_url
    if result_backend:
        celery.conf.result_backend = result_backend

