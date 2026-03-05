"""
backend/routes/__init__.py

Route registration and shared route utilities (e.g., role guard decorator).
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict, Tuple, TypeVar

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity

from backend.models.user import User

F = TypeVar("F", bound=Callable[..., Any])


def role_required(required_role: str) -> Callable[[F], F]:
    """
    Decorator to enforce that the current JWT belongs to a user with the required role.

    Parameters:
        required_role (str): Role string that must match the JWT claim 'role'
            (exactly one of 'admin', 'company', 'student').

    Returns:
        Callable: Decorator that wraps a Flask route function and returns a JSON error response
        if role is not satisfied or user is inactive/blacklisted.
    """

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            claims = get_jwt()
            role = claims.get("role")
            user_id = get_jwt_identity()

            if role != required_role:
                return jsonify({"success": False, "error": "Access denied."}), 403

            user = User.query.get(int(user_id)) if user_id is not None else None
            if user is None:
                return jsonify({"success": False, "error": "User not found."}), 404
            if not user.is_active or user.is_blacklisted:
                return jsonify({"success": False, "error": "Account is inactive or blacklisted."}), 403

            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def register_routes(app) -> None:
    """
    Register all API blueprints on the Flask application.

    Parameters:
        app: Flask application instance.

    Returns:
        None. Attaches blueprints for auth, admin, company, and student routes.
    """
    from backend.routes.auth_routes import auth_bp
    from backend.routes.admin_routes import admin_bp
    from backend.routes.company_routes import company_bp
    from backend.routes.student_routes import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(student_bp)

