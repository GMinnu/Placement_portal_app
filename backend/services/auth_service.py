"""
backend/services/auth_service.py

Authentication and user management service functions.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from flask_jwt_extended import create_access_token

from backend.extensions import db
from backend.models.company import CompanyProfile
from backend.models.student import StudentProfile
from backend.models.user import User


def _require_fields(data: Dict[str, Any], required_fields: list[str]) -> None:
    """
    Validate presence of required fields in a request payload.

    Parameters:
        data (Dict[str, Any]): Incoming request payload dictionary.
        required_fields (list[str]): List of field names that must be present and non-empty.

    Returns:
        None. Raises ValueError if any required field is missing/empty.
    """
    missing = [f for f in required_fields if f not in data or data.get(f) in (None, "", [])]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


def register_student(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any], str]:
    """
    Register a new student user and create their StudentProfile.

    Parameters:
        data (Dict[str, Any]): Registration data containing:
            email, password, full_name, roll_number, branch, year_of_study, cgpa, phone.

    Returns:
        Tuple[str, Dict[str, Any], str]:
            token: JWT access token string for the newly created user.
            user_info: Dictionary containing user + student profile info.
            message: Human-readable success message.
    """
    _require_fields(
        data,
        ["email", "password", "full_name", "roll_number", "branch", "cgpa", "phone"],
    )

    # Allow either key for year, but store in the existing DB column (year_of_study).
    year_of_passout_raw = data.get("year_of_passout", data.get("year_of_study"))
    if year_of_passout_raw in (None, "", []):
        raise ValueError("Missing required field: year_of_passout")

    email = str(data["email"]).strip().lower()
    roll_number = str(data["roll_number"]).strip().upper()

    if User.query.filter_by(email=email).first() is not None:
        raise ValueError("Email is already registered.")

    if StudentProfile.query.filter_by(roll_number=roll_number).first() is not None:
        raise ValueError("Roll number is already registered.")

    # Validate branch against allowed set.
    allowed_branches = {"CSE", "ECE", "EE", "ME"}
    branch = str(data["branch"]).strip().upper()
    if branch not in allowed_branches:
        raise ValueError("Invalid branch. Allowed values: CSE, ECE, EE, ME.")

    # Validate phone as exactly 10 digits.
    phone_raw = str(data["phone"]).strip()
    phone_digits = "".join(ch for ch in phone_raw if ch.isdigit())
    if len(phone_digits) != 10:
        raise ValueError("Invalid phone number. Must be exactly 10 digits.")

    user = User(email=email, role="student", is_active=True, is_blacklisted=False)
    user.set_password(str(data["password"]))

    student = StudentProfile(
        user=user,
        full_name=str(data["full_name"]).strip(),
        roll_number=roll_number,
        branch=branch,
        year_of_study=int(year_of_passout_raw),
        cgpa=float(data["cgpa"]),
        phone=phone_digits,
        resume_path=None,
    )

    db.session.add(user)
    db.session.add(student)
    db.session.commit()

    # Identity must be a string for JWT (avoids "Subject must be a string" 422 errors).
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    user_info = {
        "user": user.to_dict(),
        "student_profile": student.to_dict(),
        "name": student.full_name,
    }
    return token, user_info, "Student registered successfully."


def register_company(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any], str]:
    """
    Register a new company user and create their CompanyProfile in pending approval state.

    Parameters:
        data (Dict[str, Any]): Registration data containing:
            email, password, company_name, hr_name, hr_email, website, description.

    Returns:
        Tuple[str, Dict[str, Any], str]:
            token: JWT access token string for the newly created user.
            user_info: Dictionary containing user + company profile info.
            message: Human-readable success message ("Pending admin approval").
    """
    _require_fields(
        data,
        ["email", "password", "company_name", "hr_name", "hr_email"],
    )

    email = str(data["email"]).strip().lower()
    if User.query.filter_by(email=email).first() is not None:
        raise ValueError("Email is already registered.")

    user = User(email=email, role="company", is_active=True, is_blacklisted=False)
    user.set_password(str(data["password"]))

    company = CompanyProfile(
        user=user,
        company_name=str(data["company_name"]).strip(),
        hr_name=str(data["hr_name"]).strip(),
        hr_email=str(data["hr_email"]).strip().lower(),
        website=str(data.get("website") or "").strip() or None,
        description=str(data.get("description") or "").strip() or None,
        approval_status="pending",
        rejection_reason=None,
    )

    db.session.add(user)
    db.session.add(company)
    db.session.commit()

    # Identity must be a string for JWT (avoids "Subject must be a string" 422 errors).
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    user_info = {
        "user": user.to_dict(),
        "company_profile": company.to_dict(),
        "name": company.company_name,
    }
    return token, user_info, "Pending admin approval"


def login_user(email: str, password: str) -> Tuple[str, Dict[str, Any], str]:
    """
    Authenticate a user with email/password and return a JWT token and user summary.

    Parameters:
        email (str): User email used as username.
        password (str): Plaintext password to verify.

    Returns:
        Tuple[str, Dict[str, Any], str]:
            token: JWT access token string.
            data: Dictionary containing { token, role, user_id, name } as required by spec.
            message: Human-readable success message.
    """
    email_normalized = str(email).strip().lower()
    user = User.query.filter_by(email=email_normalized).first()
    if user is None:
        raise ValueError("Invalid email or password.")

    if not user.is_active or user.is_blacklisted:
        raise ValueError("Account is inactive or blacklisted. Please contact admin.")

    if not user.check_password(str(password)):
        raise ValueError("Invalid email or password.")

    # Identity must be a string for JWT (avoids "Subject must be a string" 422 errors).
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    name = "Admin"
    if user.role == "student" and user.student_profile:
        name = user.student_profile.full_name
    if user.role == "company" and user.company_profile:
        name = user.company_profile.company_name

    data = {"token": token, "role": user.role, "user_id": user.id, "name": name}
    return token, data, "Login successful."


def get_current_user(user_id: int) -> Dict[str, Any]:
    """
    Fetch a user by id and include role-specific profile data.

    Parameters:
        user_id (int): User primary key id (from JWT identity).

    Returns:
        Dict[str, Any]: Dictionary containing user info and nested profile data.
    """
    user = User.query.get(int(user_id))
    if user is None:
        raise ValueError("User not found.")

    payload: Dict[str, Any] = {"user": user.to_dict()}
    if user.role == "student" and user.student_profile is not None:
        payload["student_profile"] = user.student_profile.to_dict()
        payload["name"] = user.student_profile.full_name
    elif user.role == "company" and user.company_profile is not None:
        payload["company_profile"] = user.company_profile.to_dict()
        payload["name"] = user.company_profile.company_name
    else:
        payload["name"] = "Admin"

    return payload

