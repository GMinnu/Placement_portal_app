"""
backend/routes/admin_routes.py

Blueprint: Admin-only routes.
Role: admin
URL Prefix: /api/admin
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from backend.extensions import cache, db
from backend.models.application import Application
from backend.models.company import CompanyProfile
from backend.models.drive import PlacementDrive
from backend.models.student import StudentProfile
from backend.models.user import User
from backend.routes import role_required
from backend.services.email_service import (
    send_company_approved,
    send_company_rejected,
    send_drive_approved,
    send_drive_rejected,
)


# Blueprint for /api/admin/* routes.
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


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


@admin_bp.get("/dashboard")
@jwt_required()
@role_required("admin")
@cache.cached(timeout=300, key_prefix="admin_dashboard")
def admin_dashboard():
    """
    Route: GET /api/admin/dashboard
    Auth: Bearer JWT (required)
    Role: admin
    Description: Return dashboard metrics and recent activity (cached 5 minutes).

    Parameters:
        None.

    Returns:
        Flask response: JSON with totals and recent lists.
    """
    total_students = StudentProfile.query.count()
    total_companies = CompanyProfile.query.count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()

    recent_drives = (
        PlacementDrive.query.options(joinedload(PlacementDrive.company))
        .order_by(PlacementDrive.created_at.desc())
        .limit(5)
        .all()
    )
    recent_applications = (
        Application.query.options(
            joinedload(Application.student),
            joinedload(Application.drive).joinedload(PlacementDrive.company),
        )
        .order_by(Application.applied_at.desc())
        .limit(5)
        .all()
    )

    return _ok(
        {
            "total_students": total_students,
            "total_companies": total_companies,
            "total_drives": total_drives,
            "total_applications": total_applications,
            "recent_drives": [d.to_dict(include_company=True) for d in recent_drives],
            "recent_applications": [a.to_dict(include_drive=True, include_student=True) for a in recent_applications],
        },
        "Admin dashboard loaded.",
    )


@admin_bp.get("/companies")
@jwt_required()
@role_required("admin")
def list_companies():
    """
    Route: GET /api/admin/companies?search=<q>
    Auth: Bearer JWT (required)
    Role: admin
    Description: List companies with user info; supports search by company_name/hr_name.

    Parameters:
        None (reads query string).

    Returns:
        Flask response: JSON list of companies.
    """
    q = (request.args.get("search") or "").strip()
    query = CompanyProfile.query.options(joinedload(CompanyProfile.user))
    if q:
        like = f"%{q}%"
        query = query.filter(
            (CompanyProfile.company_name.ilike(like)) | (CompanyProfile.hr_name.ilike(like))
        )
    companies = query.order_by(CompanyProfile.created_at.desc()).all()
    payload = []
    for c in companies:
        item = c.to_dict()
        item["user"] = c.user.to_dict() if c.user else None
        payload.append(item)
    return _ok({"companies": payload}, "Companies fetched successfully.")


@admin_bp.post("/companies/<int:company_id>/approve")
@jwt_required()
@role_required("admin")
def approve_company(company_id: int):
    """
    Route: POST /api/admin/companies/<id>/approve
    Auth: Bearer JWT (required)
    Role: admin
    Description: Approve a company's registration and notify HR by email.

    Parameters:
        company_id (int): CompanyProfile id from URL path.

    Returns:
        Flask response: JSON success/error.
    """
    try:
        company = CompanyProfile.query.get(company_id)
        if company is None:
            return _bad("Company not found.", 404)

        company.approval_status = "approved"
        company.rejection_reason = None
        db.session.commit()

        # Email failures are logged but must not break API.
        send_company_approved(company.company_name, company.hr_email)
        return _ok({"company": company.to_dict()}, "Company approved successfully.")
    except Exception as exc:
        return _bad(str(exc), 500)


@admin_bp.post("/companies/<int:company_id>/reject")
@jwt_required()
@role_required("admin")
def reject_company(company_id: int):
    """
    Route: POST /api/admin/companies/<id>/reject
    Auth: Bearer JWT (required)
    Role: admin
    Description: Reject a company registration with a reason and notify HR by email.

    Parameters:
        company_id (int): CompanyProfile id from URL path.

    Returns:
        Flask response: JSON success/error.
    """
    try:
        company = CompanyProfile.query.get(company_id)
        if company is None:
            return _bad("Company not found.", 404)

        body = request.get_json(force=True) or {}
        reason = str(body.get("reason") or "").strip()
        if not reason:
            return _bad("Rejection reason is required.", 400)

        company.approval_status = "rejected"
        company.rejection_reason = reason
        db.session.commit()

        # Email failures are logged but must not break API.
        send_company_rejected(company.company_name, company.hr_email, reason)
        return _ok({"company": company.to_dict()}, "Company rejected successfully.")
    except Exception as exc:
        return _bad(str(exc), 500)


@admin_bp.post("/companies/<int:company_id>/blacklist")
@jwt_required()
@role_required("admin")
def blacklist_company(company_id: int):
    """
    Route: POST /api/admin/companies/<id>/blacklist
    Auth: Bearer JWT (required)
    Role: admin
    Description: Blacklist a company user (is_blacklisted=True, is_active=False).

    Parameters:
        company_id (int): CompanyProfile id from URL path.

    Returns:
        Flask response: JSON success/error.
    """
    try:
        company = CompanyProfile.query.options(joinedload(CompanyProfile.user)).get(company_id)
        if company is None or company.user is None:
            return _bad("Company not found.", 404)

        company.user.is_blacklisted = True
        company.user.is_active = False
        db.session.commit()

        return _ok({"user": company.user.to_dict()}, "Company blacklisted successfully.")
    except Exception as exc:
        return _bad(str(exc), 500)


@admin_bp.post("/companies/<int:company_id>/unblacklist")
@jwt_required()
@role_required("admin")
def unblacklist_company(company_id: int):
    """
    Route: POST /api/admin/companies/<id>/unblacklist
    Auth: Bearer JWT (required)
    Role: admin
    Description: Remove blacklist from a company user (is_blacklisted=False, is_active=True).

    Parameters:
        company_id (int): CompanyProfile id from URL path.

    Returns:
        Flask response: JSON success/error.
    """
    try:
        company = CompanyProfile.query.options(joinedload(CompanyProfile.user)).get(company_id)
        if company is None or company.user is None:
            return _bad("Company not found.", 404)

        company.user.is_blacklisted = False
        company.user.is_active = True
        db.session.commit()

        return _ok({"user": company.user.to_dict()}, "Company unblacklisted successfully.")
    except Exception as exc:
        return _bad(str(exc), 500)


@admin_bp.get("/students")
@jwt_required()
@role_required("admin")
def list_students():
    """
    Route: GET /api/admin/students?search=<q>
    Auth: Bearer JWT (required)
    Role: admin
    Description: List students with user info; supports search by name/roll/branch.

    Parameters:
        None (reads query string).

    Returns:
        Flask response: JSON list of students.
    """
    q = (request.args.get("search") or "").strip()
    query = StudentProfile.query.options(joinedload(StudentProfile.user))
    if q:
        like = f"%{q}%"
        query = query.filter(
            (StudentProfile.full_name.ilike(like))
            | (StudentProfile.roll_number.ilike(like))
            | (StudentProfile.branch.ilike(like))
        )
    students = query.order_by(StudentProfile.created_at.desc()).all()
    payload = []
    for s in students:
        item = s.to_dict()
        item["user"] = s.user.to_dict() if s.user else None
        payload.append(item)
    return _ok({"students": payload}, "Students fetched successfully.")


@admin_bp.post("/students/<int:student_id>/blacklist")
@jwt_required()
@role_required("admin")
def blacklist_student(student_id: int):
    """
    Route: POST /api/admin/students/<id>/blacklist
    Auth: Bearer JWT (required)
    Role: admin
    Description: Blacklist a student user (is_blacklisted=True, is_active=False).

    Parameters:
        student_id (int): StudentProfile id from URL path.

    Returns:
        Flask response: JSON success/error.
    """
    student = StudentProfile.query.options(joinedload(StudentProfile.user)).get(student_id)
    if student is None or student.user is None:
        return _bad("Student not found.", 404)

    student.user.is_blacklisted = True
    student.user.is_active = False
    db.session.commit()

    return _ok({"user": student.user.to_dict()}, "Student blacklisted successfully.")


@admin_bp.post("/students/<int:student_id>/unblacklist")
@jwt_required()
@role_required("admin")
def unblacklist_student(student_id: int):
    """
    Route: POST /api/admin/students/<id>/unblacklist
    Auth: Bearer JWT (required)
    Role: admin
    Description: Remove blacklist from a student user (is_blacklisted=False, is_active=True).

    Parameters:
        student_id (int): StudentProfile id from URL path.

    Returns:
        Flask response: JSON success/error.
    """
    try:
        student = StudentProfile.query.options(joinedload(StudentProfile.user)).get(student_id)
        if student is None or student.user is None:
            return _bad("Student not found.", 404)

        student.user.is_blacklisted = False
        student.user.is_active = True
        db.session.commit()

        return _ok({"user": student.user.to_dict()}, "Student unblacklisted successfully.")
    except Exception as exc:
        return _bad(str(exc), 500)


@admin_bp.get("/drives")
@jwt_required()
@role_required("admin")
def list_drives():
    """
    Route: GET /api/admin/drives
    Auth: Bearer JWT (required)
    Role: admin
    Description: List all placement drives with company profile info.

    Parameters:
        None.

    Returns:
        Flask response: JSON list of drives.
    """
    drives = (
        PlacementDrive.query.options(joinedload(PlacementDrive.company))
        .order_by(PlacementDrive.created_at.desc())
        .all()
    )
    return _ok({"drives": [d.to_dict(include_company=True) for d in drives]}, "Drives fetched successfully.")


@admin_bp.post("/drives/<int:drive_id>/approve")
@jwt_required()
@role_required("admin")
def approve_drive(drive_id: int):
    """
    Route: POST /api/admin/drives/<id>/approve
    Auth: Bearer JWT (required)
    Role: admin
    Description: Approve a placement drive and notify the company by email.

    Parameters:
        drive_id (int): PlacementDrive id from URL path.

    Returns:
        Flask response: JSON success/error.
    """
    try:
        drive = PlacementDrive.query.options(joinedload(PlacementDrive.company)).get(drive_id)
        if drive is None or drive.company is None:
            return _bad("Drive not found.", 404)

        drive.status = "approved"
        drive.rejection_reason = None
        db.session.commit()

        # Email failures are logged but must not break API.
        send_drive_approved(drive.company.company_name, drive.company.hr_email, drive.job_title)
        return _ok({"drive": drive.to_dict(include_company=True)}, "Drive approved successfully.")
    except Exception as exc:
        return _bad(str(exc), 500)


@admin_bp.post("/drives/<int:drive_id>/reject")
@jwt_required()
@role_required("admin")
def reject_drive(drive_id: int):
    """
    Route: POST /api/admin/drives/<id>/reject
    Auth: Bearer JWT (required)
    Role: admin
    Description: Reject a placement drive with a reason and notify the company by email.

    Parameters:
        drive_id (int): PlacementDrive id from URL path.

    Returns:
        Flask response: JSON success/error.
    """
    try:
        drive = PlacementDrive.query.options(joinedload(PlacementDrive.company)).get(drive_id)
        if drive is None or drive.company is None:
            return _bad("Drive not found.", 404)

        body = request.get_json(force=True) or {}
        reason = str(body.get("reason") or "").strip()
        if not reason:
            return _bad("Rejection reason is required.", 400)

        drive.status = "rejected"
        drive.rejection_reason = reason
        db.session.commit()

        # Email failures are logged but must not break API.
        send_drive_rejected(drive.company.company_name, drive.company.hr_email, drive.job_title, reason)
        return _ok({"drive": drive.to_dict(include_company=True)}, "Drive rejected successfully.")
    except Exception as exc:
        return _bad(str(exc), 500)


@admin_bp.get("/applications")
@jwt_required()
@role_required("admin")
def list_applications():
    """
    Route: GET /api/admin/applications
    Auth: Bearer JWT (required)
    Role: admin
    Description: List all applications with Student + Drive + Company info.

    Parameters:
        None.

    Returns:
        Flask response: JSON list of applications.
    """
    applications = (
        Application.query.options(
            joinedload(Application.student),
            joinedload(Application.drive).joinedload(PlacementDrive.company),
        )
        .order_by(Application.applied_at.desc())
        .all()
    )
    return _ok(
        {"applications": [a.to_dict(include_drive=True, include_student=True) for a in applications]},
        "Applications fetched successfully.",
    )


def _last_n_month_ranges(n: int) -> List[Tuple[datetime, datetime, str]]:
    """
    Build month ranges for the last N months including current month.

    Parameters:
        n (int): Number of months to include.

    Returns:
        List[Tuple[datetime, datetime, str]]: List of (start, end, label) where label is "Jan 2025".
    """
    now = datetime.now()
    ranges: List[Tuple[datetime, datetime, str]] = []
    year = now.year
    month = now.month

    for i in range(n):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1

        start = datetime(y, m, 1)
        next_month = m + 1
        next_year = y
        if next_month == 13:
            next_month = 1
            next_year += 1
        end = datetime(next_year, next_month, 1)
        label = start.strftime("%b %Y")
        ranges.append((start, end, label))

    return list(reversed(ranges))


@admin_bp.get("/analytics")
@jwt_required()
@role_required("admin")
@cache.cached(timeout=600, key_prefix="admin_analytics")
def admin_analytics():
    """
    Route: GET /api/admin/analytics
    Auth: Bearer JWT (required)
    Role: admin
    Description: Returns data for 4 Chart.js charts (cached 10 minutes).

    Parameters:
        None.

    Returns:
        Flask response: JSON with drives_per_month, application_status_breakdown,
        top_companies_by_applicants, monthly_selections.
    """
    # Drives per month (last 6 months).
    month_ranges = _last_n_month_ranges(6)
    drives_per_month = []
    selections_per_month = []
    for start, end, label in month_ranges:
        drive_count = (
            PlacementDrive.query.filter(PlacementDrive.created_at >= start, PlacementDrive.created_at < end).count()
        )
        selected_count = (
            Application.query.filter(
                Application.status == "selected",
                Application.applied_at >= start,
                Application.applied_at < end,
            ).count()
        )
        drives_per_month.append({"month": label, "count": drive_count})
        selections_per_month.append({"month": label, "selected": selected_count})

    # Application status breakdown.
    breakdown_rows = (
        db.session.query(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )
    application_status_breakdown: Dict[str, int] = {"applied": 0, "shortlisted": 0, "selected": 0, "rejected": 0}
    for status, count in breakdown_rows:
        if status in application_status_breakdown:
            application_status_breakdown[status] = int(count)

    # Top companies by applicants (top 5).
    top_rows = (
        db.session.query(CompanyProfile.company_name, func.count(Application.id).label("applicants"))
        .join(PlacementDrive, PlacementDrive.company_id == CompanyProfile.id)
        .join(Application, Application.drive_id == PlacementDrive.id)
        .group_by(CompanyProfile.company_name)
        .order_by(func.count(Application.id).desc())
        .limit(5)
        .all()
    )
    top_companies_by_applicants = [{"company": name, "applicants": int(cnt)} for name, cnt in top_rows]

    return _ok(
        {
            "drives_per_month": drives_per_month,
            "application_status_breakdown": application_status_breakdown,
            "top_companies_by_applicants": top_companies_by_applicants,
            "monthly_selections": selections_per_month,
        },
        "Admin analytics loaded.",
    )

