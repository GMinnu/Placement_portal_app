"""
backend/app.py

Flask app factory for IIT Madras Placement Portal.

Responsibilities:
- create_app(): create and configure the Flask app instance
- initialize extensions (db, jwt, mail, cache)
- register blueprints
- create database tables programmatically
- create default admin user on first run
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template
from flask_jwt_extended import JWTManager

# Ensure project root (which contains the 'backend' package) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import Config
from backend.extensions import cache, db, init_celery_from_flask_config, jwt, mail
from backend.models import User  # ensures all models are imported/registered
from backend.routes import register_routes


def _create_default_admin() -> None:
    """
    Create the default admin user if it does not exist.

    Default credentials (as required by spec):
        Email: admin@iitm.ac.in
        Password: Admin@123

    Parameters:
        None.

    Returns:
        None. Creates and commits an admin user on first run.
    """
    admin_email = "admin@iitm.ac.in"
    existing = User.query.filter_by(email=admin_email).first()
    if existing is not None:
        return

    admin = User(email=admin_email, role="admin", is_active=True, is_blacklisted=False)
    admin.set_password("Admin@123")
    db.session.add(admin)
    db.session.commit()


def create_app() -> Flask:
    """
    Flask application factory.

    Parameters:
        None.

    Returns:
        Flask: Configured Flask application instance.
    """
    backend_dir = Path(__file__).resolve().parent
    project_root = backend_dir.parent

    app = Flask(
        __name__,
        template_folder=str((project_root / "frontend").resolve()),
        static_folder=str((project_root / "frontend").resolve()),
        static_url_path="/static",
    )

    # Load config and ensure required directories exist.
    app.config.from_mapping(Config.to_flask_config_dict())
    init_celery_from_flask_config(app.config)
    Config.ensure_storage_directories()

    # Initialize Flask extensions.
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    cache.init_app(app)

    # Register API blueprints.
    register_routes(app)

    # Home route serves the SPA entry point (Jinja2 used only here).
    @app.get("/")
    def index():
        """
        Route: GET /
        Auth: None (public)
        Description: Serve the Vue SPA entry point (frontend/index.html).

        Parameters:
            None.

        Returns:
            Flask response: Rendered HTML template.
        """
        return render_template("index.html")

    # Standard JSON error handlers for common failures.
    @app.errorhandler(404)
    def not_found(_e):
        """
        Error handler: 404 Not Found.

        Parameters:
            _e: Exception instance.

        Returns:
            Flask response: Standard error JSON.
        """
        return jsonify({"success": False, "error": "Not Found"}), 404

    @app.errorhandler(500)
    def internal_error(_e):
        """
        Error handler: 500 Internal Server Error.

        Parameters:
            _e: Exception instance.

        Returns:
            Flask response: Standard error JSON.
        """
        return jsonify({"success": False, "error": "Internal Server Error"}), 500

    # Create tables and default admin within app context.
    with app.app_context():
        db.create_all()
        _create_default_admin()

    return app


if __name__ == "__main__":
    """
    Entry point for local development without Docker.

    Parameters:
        None.

    Returns:
        None. Runs the Flask dev server.
    """
    flask_app = create_app()
    flask_app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_ENV") == "development")

