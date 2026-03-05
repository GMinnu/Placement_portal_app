"""
backend/routes/auth_routes.py

Blueprint: Authentication routes.
Role: Public + authenticated user info.
URL Prefix: /api/auth
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.services import auth_service
from backend.services.email_service import send_welcome_company, send_welcome_student


# Blueprint for /api/auth/* routes.
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register/student")
def register_student_route():
    """
    Route: POST /api/auth/register/student
    Auth: None (public)
    Description: Register a new student user and create their StudentProfile.

    Parameters:
        None (reads JSON body from request).

    Returns:
        Flask response: JSON with {success, data, message} or {success, error}.
    """
    try:
        data = request.get_json(force=True) or {}
        token, user_info, message = auth_service.register_student(data)
        send_welcome_student(user_info["student_profile"]["full_name"], user_info["user"]["email"])
        return jsonify({"success": True, "data": {"token": token, **user_info}, "message": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@auth_bp.post("/register/company")
def register_company_route():
    """
    Route: POST /api/auth/register/company
    Auth: None (public)
    Description: Register a new company user and create CompanyProfile (pending admin approval).

    Parameters:
        None (reads JSON body from request).

    Returns:
        Flask response: JSON with {success, data, message} or {success, error}.
    """
    try:
        data = request.get_json(force=True) or {}
        token, user_info, message = auth_service.register_company(data)
        send_welcome_company(user_info["company_profile"]["company_name"], user_info["company_profile"]["hr_email"])
        return jsonify({"success": True, "data": {"token": token, **user_info}, "message": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@auth_bp.post("/login")
def login_route():
    """
    Route: POST /api/auth/login
    Auth: None (public)
    Description: Login using email/password and return JWT token and user summary.

    Parameters:
        None (reads JSON body from request).

    Returns:
        Flask response: JSON with {success, data, message} or {success, error}.
    """
    try:
        data = request.get_json(force=True) or {}
        email = data.get("email")
        password = data.get("password")
        token, login_data, message = auth_service.login_user(email=email, password=password)
        return jsonify({"success": True, "data": login_data, "message": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@auth_bp.get("/me")
@jwt_required()
def me_route():
    """
    Route: GET /api/auth/me
    Auth: Bearer JWT (required)
    Description: Return current user info with role-specific profile data.

    Parameters:
        None (uses JWT identity).

    Returns:
        Flask response: JSON with {success, data, message} or {success, error}.
    """
    try:
        user_id = get_jwt_identity()
        payload = auth_service.get_current_user(int(user_id))
        return jsonify({"success": True, "data": payload, "message": "User fetched successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@auth_bp.post("/logout")
@jwt_required()
def logout_route():
    """
    Route: POST /api/auth/logout
    Auth: Bearer JWT (required)
    Description: Stateless logout endpoint (client clears token).

    Parameters:
        None.

    Returns:
        Flask response: JSON confirming logout.
    """
    _ = get_jwt_identity()
    return jsonify({"success": True, "data": {}, "message": "Logged out successfully."})

