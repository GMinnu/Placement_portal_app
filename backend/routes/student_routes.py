"""
backend/routes/student_routes.py

Blueprint: Student-only routes.
Role: student
URL Prefix: /api/student
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request, send_file, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.orm import joinedload

from backend.config import Config
from backend.extensions import cache, db
from backend.models.application import Application
from backend.models.drive import PlacementDrive
from backend.models.export_job import ExportJob
from backend.models.student import StudentProfile
from backend.models.user import User
from backend.models.company import CompanyProfile
from backend.routes import role_required
from backend.services.eligibility_service import check_eligibility


# Blueprint for /api/student/* routes.
student_bp = Blueprint("student", __name__, url_prefix="/api/student")


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


def _get_student_for_current_user() -> StudentProfile:
    """
    Fetch the StudentProfile for the currently authenticated student user.

    Parameters:
        None (uses JWT identity).

    Returns:
        StudentProfile: StudentProfile associated with the current user.
    """
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id)) if user_id is not None else None
    if user is None or user.student_profile is None:
        raise ValueError("Student profile not found.")
    return user.student_profile


def _allowed_resume_extension(filename: str) -> bool:
    """
    Validate resume file extension.

    Parameters:
        filename (str): Uploaded filename.

    Returns:
        bool: True if extension is one of .pdf, .doc, .docx.
    """
    ext = (Path(filename).suffix or "").lower()
    return ext in {".pdf", ".doc", ".docx"}


def _as_utc(dt: datetime | None) -> datetime | None:
    """
    Normalize a datetime to timezone-aware UTC.

    If dt is naive, it is treated as UTC for consistency across the app.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _drive_student_view(student: StudentProfile, drive: PlacementDrive) -> Dict[str, Any]:
    """
    Drive payload tailored for the student UI.

    Includes eligibility and whether the student already applied.
    """
    is_ok, reason = check_eligibility(student, drive)
    now = datetime.now(timezone.utc)
    deadline_utc = _as_utc(drive.application_deadline)
    deadline_passed = bool(deadline_utc and deadline_utc < now)

    already_applied = (
        Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
        is not None
    )

    payload = drive.to_dict(include_company=True)
    payload["eligibility"] = {"is_eligible": bool(is_ok), "reason": reason}
    payload["already_applied"] = bool(already_applied)
    payload["deadline_passed"] = bool(deadline_passed)
    payload["can_apply"] = bool(is_ok and not already_applied and not deadline_passed)
    return payload


@student_bp.get("/dashboard")
@jwt_required()
@role_required("student")
def student_dashboard():
    """
    Route: GET /api/student/dashboard
    Auth: Bearer JWT (required)
    Role: student
    Description: List approved drives with optional query filters.
    Includes eligibility info and apply-ability for the logged-in student.

    Query params:
        branch, min_cgpa, year, search

    Returns:
        Flask response: JSON list of drives (approved) with eligibility metadata.
    """
    try:
        student = _get_student_for_current_user()

        query = PlacementDrive.query.options(
            joinedload(PlacementDrive.company).joinedload(CompanyProfile.user)
        ).filter(PlacementDrive.status == "approved")

        # Optional filters.
        if request.args.get("branch"):
            query = query.filter(PlacementDrive.eligible_branches.ilike(f"%{request.args.get('branch').strip()}%"))
        if request.args.get("min_cgpa"):
            try:
                query = query.filter(PlacementDrive.min_cgpa <= float(request.args.get("min_cgpa")))
            except Exception:
                return _bad("min_cgpa must be a number.", 400)
        if request.args.get("year"):
            try:
                query = query.filter(PlacementDrive.eligible_year == int(request.args.get("year")))
            except Exception:
                return _bad("year must be an integer.", 400)
        if request.args.get("search"):
            s = request.args.get("search").strip()
            query = query.filter(PlacementDrive.job_title.ilike(f"%{s}%"))

        drives = query.order_by(PlacementDrive.application_deadline.asc()).all()

        visible_drives: List[Dict[str, Any]] = []
        for d in drives:
            company = d.company
            # Company must be approved and its user must not be blacklisted or inactive.
            if not company or company.approval_status != "approved":
                continue
            company_user = getattr(company, "user", None)
            if company_user is None or not company_user.is_active or company_user.is_blacklisted:
                continue

            visible_drives.append(_drive_student_view(student, d))

        data = {"drives": visible_drives}
        return _ok(data, "Drives loaded.")
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.get("/drives/<int:drive_id>")
@jwt_required()
@role_required("student")
def get_drive_details(drive_id: int):
    """
    Route: GET /api/student/drives/<id>
    Auth: Bearer JWT (required)
    Role: student
    Description: Fetch one approved drive with eligibility + apply-ability metadata.
    """
    try:
        student = _get_student_for_current_user()
        drive = (
            PlacementDrive.query.options(
                joinedload(PlacementDrive.company).joinedload(CompanyProfile.user)
            )
            .filter(PlacementDrive.id == int(drive_id))
            .first()
        )
        if drive is None:
            return _bad("Drive not found.", 404)
        if drive.status != "approved":
            return _bad("Drive is not available.", 403)

        company = drive.company
        if not company or company.approval_status != "approved":
            return _bad("Drive is not available.", 403)
        company_user = getattr(company, "user", None)
        if company_user is None or not company_user.is_active or company_user.is_blacklisted:
            return _bad("Drive is not available.", 403)

        return _ok({"drive": _drive_student_view(student, drive)}, "Drive loaded.")
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.get("/profile")
@jwt_required()
@role_required("student")
def get_student_profile():
    """
    Route: GET /api/student/profile
    Auth: Bearer JWT (required)
    Role: student
    Description: Return StudentProfile details along with user email.

    Returns:
        Flask response: JSON with student_profile and email.
    """
    try:
        student = _get_student_for_current_user()
        user = student.user
        return _ok({"student_profile": student.to_dict(), "email": user.email if user else None}, "Student profile loaded.")
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.put("/profile")
@jwt_required()
@role_required("student")
def update_student_profile():
    """
    Route: PUT /api/student/profile
    Auth: Bearer JWT (required)
    Role: student
    Description: Update StudentProfile fields (full_name, roll_number, branch, year_of_study, cgpa, phone).

    Returns:
        Flask response: JSON with updated student profile.
    """
    try:
        student = _get_student_for_current_user()
        body = request.get_json(force=True) or {}

        if "roll_number" in body:
            new_roll = str(body["roll_number"]).strip().upper()
            existing = StudentProfile.query.filter(StudentProfile.roll_number == new_roll, StudentProfile.id != student.id).first()
            if existing is not None:
                return _bad("Roll number is already registered.", 400)
            student.roll_number = new_roll

        allowed_branches = {"CSE", "ECE", "EE", "ME"}

        for field in ["full_name", "branch", "phone"]:
            if field in body:
                value = str(body[field]).strip()
                if not value:
                    return _bad(f"{field} cannot be empty.", 400)
                if field == "branch":
                    value_upper = value.upper()
                    if value_upper not in allowed_branches:
                        return _bad("Invalid branch. Allowed values: CSE, ECE, EE, ME.", 400)
                    student.branch = value_upper
                elif field == "phone":
                    digits = "".join(ch for ch in value if ch.isdigit())
                    if len(digits) != 10:
                        return _bad("Invalid phone number. Must be exactly 10 digits.", 400)
                    student.phone = digits
                else:
                    setattr(student, field, value)

        # Accept either year_of_passout or year_of_study for compatibility.
        if "year_of_passout" in body:
            student.year_of_study = int(body["year_of_passout"])
        if "year_of_study" in body:
            student.year_of_study = int(body["year_of_study"])
        if "cgpa" in body:
            student.cgpa = float(body["cgpa"])

        db.session.commit()
        return _ok({"student_profile": student.to_dict()}, "Student profile updated.")
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.post("/profile/resume")
@jwt_required()
@role_required("student")
def upload_resume():
    """
    Route: POST /api/student/profile/resume
    Auth: Bearer JWT (required)
    Role: student
    Description: Upload student resume (.pdf/.doc/.docx, max 5MB) and update resume_path.

    Form data:
        file field named 'resume'

    Returns:
        Flask response: JSON with resume_url.
    """
    try:
        student = _get_student_for_current_user()
        if "resume" not in request.files:
            return _bad("No resume file uploaded.", 400)
        file = request.files["resume"]
        if not file or not file.filename:
            return _bad("Invalid resume file.", 400)

        if not _allowed_resume_extension(file.filename):
            return _bad("Invalid file type. Only .pdf, .doc, .docx allowed.", 400)

        Config.ensure_storage_directories()
        ext = Path(file.filename).suffix.lower()
        filename = f"student_{student.id}_resume{ext}"
        save_path = Path(Config.UPLOAD_FOLDER) / filename

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 5 * 1024 * 1024:
            return _bad("File too large. Max size is 5MB.", 400)

        file.save(str(save_path))

        student.resume_path = f"uploads/{filename}"
        db.session.commit()

        return _ok({"resume_url": f"/api/student/resume/{filename}"}, "Resume uploaded successfully.")
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.get("/resume/<path:filename>")
@jwt_required()
@role_required("student")
def serve_resume(filename: str):
    """
    Route: GET /api/student/resume/<filename>
    Auth: Bearer JWT (required)
    Role: student
    Description: Serve a resume file from backend/uploads using send_from_directory.

    Parameters:
        filename (str): Resume filename.

    Returns:
        Flask response: File response or JSON error.
    """
    try:
        student = _get_student_for_current_user()
        expected_prefix = f"student_{student.id}_resume"
        if not Path(filename).name.startswith(expected_prefix):
            return _bad("Access denied.", 403)
        return send_from_directory(Config.UPLOAD_FOLDER, filename, as_attachment=False)
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.post("/drives/<int:drive_id>/apply")
@jwt_required()
@role_required("student")
def apply_to_drive(drive_id: int):
    """
    Route: POST /api/student/drives/<id>/apply
    Auth: Bearer JWT (required)
    Role: student
    Description: Apply to an approved drive if eligible, before deadline, and not already applied.

    Parameters:
        drive_id (int): PlacementDrive id from URL path.

    Returns:
        Flask response: JSON with created application.
    """
    try:
        student = _get_student_for_current_user()
        drive = PlacementDrive.query.options(joinedload(PlacementDrive.company)).get(drive_id)
        if drive is None:
            return _bad("Drive not found.", 404)
        if drive.status != "approved":
            return _bad("Drive is not open for applications.", 403)

        now = datetime.now(timezone.utc)
        deadline_utc = _as_utc(drive.application_deadline)
        if deadline_utc is not None and deadline_utc < now:
            return _bad("Application deadline has passed.", 403)

        is_ok, reason = check_eligibility(student, drive)
        if not is_ok:
            return _bad(reason, 403)

        existing = Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
        if existing is not None:
            return _bad("You have already applied to this drive.", 400)

        application = Application(student_id=student.id, drive_id=drive.id, status="applied", offer_letter_path=None)
        db.session.add(application)
        db.session.commit()

        return _ok({"application": application.to_dict(include_drive=True, include_student=False)}, "Applied successfully.")
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.get("/applications")
@jwt_required()
@role_required("student")
def list_student_applications():
    """
    Route: GET /api/student/applications
    Auth: Bearer JWT (required)
    Role: student
    Description: List all applications for this student with Drive + Company info (ordered desc).

    Returns:
        Flask response: JSON list of applications.
    """
    try:
        student = _get_student_for_current_user()
        apps = (
            Application.query.options(
                joinedload(Application.drive).joinedload(PlacementDrive.company)
            )
            .filter_by(student_id=student.id)
            .order_by(Application.applied_at.desc())
            .all()
        )
        return _ok({"applications": [a.to_dict(include_drive=True, include_student=False) for a in apps]}, "Applications loaded.")
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.get("/applications/<int:application_id>/offer-letter")
@jwt_required()
@role_required("student")
def download_offer_letter(application_id: int):
    """
    Route: GET /api/student/applications/<id>/offer-letter
    Auth: Bearer JWT (required)
    Role: student
    Description: Serve offer letter HTML if available and status is selected.

    Parameters:
        application_id (int): Application id.

    Returns:
        Flask response: File response or JSON error.
    """
    try:
        student = _get_student_for_current_user()
        app = Application.query.filter_by(id=application_id, student_id=student.id).first()
        if app is None:
            return _bad("Application not found.", 404)
        if not app.offer_letter_path or app.status not in ["selected"]:
            return _bad("Offer letter is not available.", 403)

        filename = Path(app.offer_letter_path).name
        abs_path = Path(Config.OFFER_LETTERS_FOLDER) / filename
        if not abs_path.exists():
            return _bad("Offer letter file not found.", 404)
        return send_file(str(abs_path), mimetype="text/html", as_attachment=False)
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.post("/export")
@jwt_required()
@role_required("student")
def request_export():
    """
    Route: POST /api/student/export
    Auth: Bearer JWT (required)
    Role: student
    Description: Create an ExportJob(status='pending') and trigger async CSV export task.

    Returns:
        Flask response: JSON with export_job_id.
    """
    try:
        from backend.tasks.export_tasks import generate_csv_export

        student = _get_student_for_current_user()
        job = ExportJob(student_id=student.id, status="pending", file_path=None, completed_at=None)
        db.session.add(job)
        db.session.commit()

        # Prefer async via Celery, but fall back to synchronous generation if broker/worker isn't available.
        try:
            generate_csv_export.delay(job.id)
            return _ok({"export_job_id": job.id}, "Export started.")
        except Exception:
            # Run inline so the feature still works in local/no-redis setups.
            generate_csv_export(job.id)
            db.session.expire_all()
            return _ok({"export_job_id": job.id}, "Export generated.")
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.get("/export/<int:job_id>/status")
@jwt_required()
@role_required("student")
def export_status(job_id: int):
    """
    Route: GET /api/student/export/<job_id>/status
    Auth: Bearer JWT (required)
    Role: student
    Description: Return ExportJob status and file_path if done.

    Parameters:
        job_id (int): ExportJob id.

    Returns:
        Flask response: JSON with export job status.
    """
    try:
        student = _get_student_for_current_user()
        job = ExportJob.query.filter_by(id=job_id, student_id=student.id).first()
        if job is None:
            return _bad("Export job not found.", 404)
        return _ok({"export_job": job.to_dict()}, "Export status fetched.")
    except Exception as e:
        return _bad(str(e), 400)


@student_bp.get("/export/<int:job_id>/download")
@jwt_required()
@role_required("student")
def export_download(job_id: int):
    """
    Route: GET /api/student/export/<job_id>/download
    Auth: Bearer JWT (required)
    Role: student
    Description: Download the generated CSV file if the export job is done.

    Parameters:
        job_id (int): ExportJob id.

    Returns:
        Flask response: CSV file attachment or JSON error.
    """
    try:
        student = _get_student_for_current_user()
        job = ExportJob.query.filter_by(id=job_id, student_id=student.id).first()
        if job is None:
            return _bad("Export job not found.", 404)
        if job.status != "done" or not job.file_path:
            return _bad("Export file is not ready.", 403)

        filename = Path(job.file_path).name
        abs_path = Path(Config.EXPORTS_FOLDER) / filename
        if not abs_path.exists():
            return _bad("Export file not found.", 404)

        return send_file(
            str(abs_path),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return _bad(str(e), 400)

