"""
backend/routes/company_routes.py

Blueprint: Company-only routes.
Role: company
URL Prefix: /api/company
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from backend.extensions import db
from backend.models.application import Application
from backend.models.company import CompanyProfile
from backend.models.drive import PlacementDrive
from backend.models.student import StudentProfile
from backend.models.user import User
from backend.routes import role_required
from backend.services.email_service import (
    send_email,
    send_rejection_notification,
    send_selection_notification,
    send_shortlist_notification,
)
from backend.services.offer_letter_service import generate_offer_letter


# Blueprint for /api/company/* routes.
company_bp = Blueprint("company", __name__, url_prefix="/api/company")


def _ok(data: Dict[str, Any], message: str):
    """
    Build a standardized success JSON response.

    Parameters:
        data (Dict[str, Any]): Response payload.
        message (str): Human-readable message.

    Returns:
        Flask response: JSON response with {success:true,data,message}.
    """
    return jsonify({"success": True, "data": data, "message": message})


def _bad(error: str, status_code: int = 400):
    """
    Build a standardized error JSON response.

    Parameters:
        error (str): Error message.
        status_code (int): HTTP status code.

    Returns:
        Flask response: JSON response with {success:false,error}.
    """
    return jsonify({"success": False, "error": error}), status_code


def _get_company_for_current_user() -> CompanyProfile:
    """
    Fetch the CompanyProfile for the currently authenticated company user.

    Parameters:
        None (uses JWT identity).

    Returns:
        CompanyProfile: CompanyProfile associated with the current user.
    """
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id)) if user_id is not None else None
    if user is None or user.company_profile is None:
        raise ValueError("Company profile not found.")
    return user.company_profile


@company_bp.get("/dashboard")
@jwt_required()
@role_required("company")
def company_dashboard():
    """
    Route: GET /api/company/dashboard
    Auth: Bearer JWT (required)
    Role: company
    Description: Return company profile and drives list with applicant counts.

    Parameters:
        None.

    Returns:
        Flask response: JSON with company_profile and drives.
    """
    try:
        company = _get_company_for_current_user()
        drives = (
            PlacementDrive.query.filter_by(company_id=company.id)
            .order_by(PlacementDrive.created_at.desc())
            .all()
        )
        drive_ids = [d.id for d in drives]
        counts = {}
        if drive_ids:
            rows = (
                db.session.query(Application.drive_id, func.count(Application.id))
                .filter(Application.drive_id.in_(drive_ids))
                .group_by(Application.drive_id)
                .all()
            )
            counts = {int(did): int(cnt) for did, cnt in rows}

        drives_payload = []
        for d in drives:
            item = d.to_dict(include_company=False)
            item["applicant_count"] = counts.get(d.id, 0)
            drives_payload.append(item)

        return _ok({"company_profile": company.to_dict(), "drives": drives_payload}, "Company dashboard loaded.")
    except Exception as e:
        return _bad(str(e), 400)


@company_bp.get("/profile")
@jwt_required()
@role_required("company")
def get_company_profile():
    """
    Route: GET /api/company/profile
    Auth: Bearer JWT (required)
    Role: company
    Description: Return CompanyProfile details for current company user.

    Parameters:
        None.

    Returns:
        Flask response: JSON with company profile.
    """
    try:
        company = _get_company_for_current_user()
        return _ok({"company_profile": company.to_dict()}, "Company profile loaded.")
    except Exception as e:
        return _bad(str(e), 400)


@company_bp.put("/profile")
@jwt_required()
@role_required("company")
def update_company_profile():
    """
    Route: PUT /api/company/profile
    Auth: Bearer JWT (required)
    Role: company
    Description: Update CompanyProfile fields (company_name, hr_name, hr_email, website, description).

    Parameters:
        None (reads JSON body from request).

    Returns:
        Flask response: JSON with updated company profile.
    """
    try:
        company = _get_company_for_current_user()
        body = request.get_json(force=True) or {}

        for field in ["company_name", "hr_name", "hr_email", "website", "description"]:
            if field in body:
                value = body.get(field)
                if field in ["company_name", "hr_name", "hr_email"] and not str(value or "").strip():
                    return _bad(f"{field} cannot be empty.", 400)
                setattr(company, field, str(value).strip() if value is not None else None)

        if company.hr_email:
            company.hr_email = company.hr_email.lower()
        if company.website:
            company.website = company.website or None
        if company.description:
            company.description = company.description or None

        db.session.commit()
        return _ok({"company_profile": company.to_dict()}, "Company profile updated.")
    except Exception as e:
        return _bad(str(e), 400)


@company_bp.post("/drives")
@jwt_required()
@role_required("company")
def create_drive():
    """
    Route: POST /api/company/drives
    Auth: Bearer JWT (required)
    Role: company
    Description: Create a new PlacementDrive (only if company is approved).

    Parameters:
        None (reads JSON body from request).

    Returns:
        Flask response: JSON with created drive.
    """
    try:
        company = _get_company_for_current_user()
        if company.approval_status != "approved":
            return _bad("Company is not approved by admin.", 403)

        body = request.get_json(force=True) or {}
        # Accept either eligible_passout_year or eligible_year; store in existing DB column (eligible_year).
        eligible_year_raw = body.get("eligible_passout_year", body.get("eligible_year"))
        required = ["job_title", "job_description", "eligible_branches", "min_cgpa", "package_lpa", "application_deadline"]
        missing = [f for f in required if f not in body or body.get(f) in (None, "", [])]
        if missing:
            return _bad(f"Missing required fields: {', '.join(missing)}", 400)
        if eligible_year_raw in (None, "", []):
            return _bad("Missing required field: eligible_passout_year", 400)

        deadline_raw = str(body["application_deadline"]).strip()
        try:
            deadline = datetime.fromisoformat(deadline_raw)
        except Exception:
            return _bad("application_deadline must be an ISO datetime string.", 400)

        drive = PlacementDrive(
            company_id=company.id,
            job_title=str(body["job_title"]).strip(),
            job_description=str(body["job_description"]).strip(),
            eligible_branches=str(body["eligible_branches"]).strip(),
            min_cgpa=float(body["min_cgpa"]),
            eligible_year=int(eligible_year_raw),
            package_lpa=float(body["package_lpa"]),
            application_deadline=deadline,
            status="pending",
            rejection_reason=None,
        )
        db.session.add(drive)
        db.session.commit()

        return _ok({"drive": drive.to_dict(include_company=True)}, "Drive created and submitted for approval.")
    except Exception as e:
        return _bad(str(e), 400)


@company_bp.get("/drives")
@jwt_required()
@role_required("company")
def list_company_drives():
    """
    Route: GET /api/company/drives
    Auth: Bearer JWT (required)
    Role: company
    Description: List all drives created by the current company.

    Parameters:
        None.

    Returns:
        Flask response: JSON list of drives.
    """
    try:
        company = _get_company_for_current_user()
        drives = (
            PlacementDrive.query.filter_by(company_id=company.id)
            .order_by(PlacementDrive.created_at.desc())
            .all()
        )
        return _ok({"drives": [d.to_dict(include_company=False) for d in drives]}, "Company drives loaded.")
    except Exception as e:
        return _bad(str(e), 400)


@company_bp.get("/drives/<int:drive_id>")
@jwt_required()
@role_required("company")
def get_drive(drive_id: int):
    """
    Route: GET /api/company/drives/<id>
    Auth: Bearer JWT (required)
    Role: company
    Description: Get a specific drive created by the current company.

    Parameters:
        drive_id (int): PlacementDrive id from URL path.

    Returns:
        Flask response: JSON with drive details.
    """
    try:
        company = _get_company_for_current_user()
        drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first()
        if drive is None:
            return _bad("Drive not found.", 404)
        return _ok({"drive": drive.to_dict(include_company=False)}, "Drive loaded.")
    except Exception as e:
        return _bad(str(e), 400)


@company_bp.put("/drives/<int:drive_id>")
@jwt_required()
@role_required("company")
def update_drive(drive_id: int):
    """
    Route: PUT /api/company/drives/<id>
    Auth: Bearer JWT (required)
    Role: company
    Description: Update a drive (only allowed if drive status is still 'pending').

    Parameters:
        drive_id (int): PlacementDrive id from URL path.

    Returns:
        Flask response: JSON with updated drive.
    """
    try:
        company = _get_company_for_current_user()
        drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first()
        if drive is None:
            return _bad("Drive not found.", 404)
        if drive.status != "pending":
            return _bad("Only pending drives can be updated.", 403)

        body = request.get_json(force=True) or {}
        updatable = ["job_title", "job_description", "eligible_branches", "min_cgpa", "eligible_year", "package_lpa", "application_deadline"]
        for field in updatable:
            if field in body:
                if field == "application_deadline":
                    deadline_raw = str(body[field]).strip()
                    try:
                        setattr(drive, field, datetime.fromisoformat(deadline_raw))
                    except Exception:
                        return _bad("application_deadline must be an ISO datetime string.", 400)
                elif field in ["min_cgpa", "package_lpa"]:
                    setattr(drive, field, float(body[field]))
                elif field == "eligible_year":
                    setattr(drive, field, int(body[field]))
                else:
                    setattr(drive, field, str(body[field]).strip())

        db.session.commit()
        return _ok({"drive": drive.to_dict(include_company=False)}, "Drive updated successfully.")
    except Exception as e:
        return _bad(str(e), 400)


@company_bp.get("/drives/<int:drive_id>/applications")
@jwt_required()
@role_required("company")
def list_drive_applications(drive_id: int):
    """
    Route: GET /api/company/drives/<id>/applications
    Auth: Bearer JWT (required)
    Role: company
    Description: List all applications for the given drive with StudentProfile details.

    Parameters:
        drive_id (int): PlacementDrive id from URL path.

    Returns:
        Flask response: JSON list of applications.
    """
    try:
        company = _get_company_for_current_user()
        drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first()
        if drive is None:
            return _bad("Drive not found.", 404)

        apps = (
            Application.query.options(joinedload(Application.student))
            .filter_by(drive_id=drive.id)
            .order_by(Application.applied_at.desc())
            .all()
        )
        payload = [a.to_dict(include_student=True) for a in apps]
        return _ok({"applications": payload}, "Drive applications loaded.")
    except Exception as e:
        return _bad(str(e), 400)


def _get_application_for_company(application_id: int) -> Application:
    """
    Fetch an Application ensuring it belongs to a drive owned by the current company.

    Parameters:
        application_id (int): Application id.

    Returns:
        Application: Application record with drive, company, and student loaded.
    """
    company = _get_company_for_current_user()
    application = (
        Application.query.options(
            joinedload(Application.student).joinedload(StudentProfile.user),
            joinedload(Application.drive).joinedload(PlacementDrive.company),
        )
        .filter(Application.id == int(application_id))
        .first()
    )
    if application is None or application.drive is None or application.drive.company_id != company.id:
        raise ValueError("Application not found.")
    return application


@company_bp.post("/applications/<int:application_id>/shortlist")
@jwt_required()
@role_required("company")
def shortlist_application(application_id: int):
    """
    Route: POST /api/company/applications/<id>/shortlist
    Auth: Bearer JWT (required)
    Role: company
    Description: Shortlist an application, generate offer letter, and notify student.

    Parameters:
        application_id (int): Application id.

    Returns:
        Flask response: JSON with updated application.
    """
    try:
        application = _get_application_for_company(application_id)
        application.status = "shortlisted"
        offer_path = generate_offer_letter(application.id)
        application.offer_letter_path = offer_path
        db.session.commit()

        student_user = application.student.user if application.student else None
        if student_user is not None:
            send_shortlist_notification(
                application.student.full_name,
                student_user.email,
                application.drive.company.company_name,
                application.drive.job_title,
            )
        return _ok({"application": application.to_dict(include_drive=True, include_student=True)}, "Application shortlisted.")
    except Exception as e:
        return _bad(str(e), 400)


@company_bp.post("/applications/<int:application_id>/select")
@jwt_required()
@role_required("company")
def select_application(application_id: int):
    """
    Route: POST /api/company/applications/<id>/select
    Auth: Bearer JWT (required)
    Role: company
    Description: Mark an application as selected and notify the student.

    Parameters:
        application_id (int): Application id.

    Returns:
        Flask response: JSON with updated application.
    """
    try:
        application = _get_application_for_company(application_id)
        application.status = "selected"
        db.session.commit()

        student_user = application.student.user if application.student else None
        if student_user is not None:
            send_selection_notification(
                application.student.full_name,
                student_user.email,
                application.drive.company.company_name,
                application.drive.job_title,
                float(application.drive.package_lpa),
            )
        return _ok({"application": application.to_dict(include_drive=True, include_student=True)}, "Application selected.")
    except Exception as e:
        return _bad(str(e), 400)


@company_bp.post("/applications/<int:application_id>/reject")
@jwt_required()
@role_required("company")
def reject_application(application_id: int):
    """
    Route: POST /api/company/applications/<id>/reject
    Auth: Bearer JWT (required)
    Role: company
    Description: Mark an application as rejected and notify the student.

    Parameters:
        application_id (int): Application id.

    Returns:
        Flask response: JSON with updated application.
    """
    try:
        application = _get_application_for_company(application_id)
        application.status = "rejected"
        db.session.commit()

        student_user = application.student.user if application.student else None
        if student_user is not None:
            send_rejection_notification(
                application.student.full_name,
                student_user.email,
                application.drive.company.company_name,
                application.drive.job_title,
            )
        return _ok({"application": application.to_dict(include_drive=True, include_student=True)}, "Application rejected.")
    except Exception as e:
        return _bad(str(e), 400)

