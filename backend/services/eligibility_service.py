"""
backend/services/eligibility_service.py

Eligibility checking logic for student applications to drives.
"""

from __future__ import annotations

from typing import Tuple

from backend.models.drive import PlacementDrive
from backend.models.student import StudentProfile


def check_eligibility(student_profile: StudentProfile, drive: PlacementDrive) -> Tuple[bool, str]:
    """
    Checks if a student is eligible to apply to a specific placement drive.

    Checks:
    1. Student's branch is in drive.eligible_branches (split by comma)
    2. Student's cgpa >= drive.min_cgpa
    3. Student's year_of_study == drive.eligible_year

    Parameters:
        student_profile (StudentProfile): The student's profile data.
        drive (PlacementDrive): The placement drive being applied to.

    Returns:
        Tuple[bool, str]: (is_eligible, reason). If eligible, reason is "Eligible".
    """
    eligible_branches = [b.strip().upper() for b in (drive.eligible_branches or "").split(",") if b.strip()]
    student_branch = (student_profile.branch or "").strip().upper()

    if student_branch not in eligible_branches:
        return False, f"Branch '{student_profile.branch}' is not eligible for this drive."

    if float(student_profile.cgpa) < float(drive.min_cgpa):
        return False, f"Minimum CGPA required is {drive.min_cgpa}."

    if int(student_profile.year_of_study) != int(drive.eligible_year):
        return False, f"Only passout year {drive.eligible_year} students are eligible."

    return True, "Eligible"

