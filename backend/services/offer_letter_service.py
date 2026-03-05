"""
backend/services/offer_letter_service.py

Offer letter generation service for shortlisted applications.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Tuple

from backend.config import Config
from backend.extensions import db
from backend.models.application import Application
from backend.models.drive import PlacementDrive


def _ordinal(n: int) -> str:
    """
    Convert an integer day value into an ordinal string (e.g., 1 -> 1st).

    Parameters:
        n (int): Day of month.

    Returns:
        str: Ordinal day string.
    """
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _format_offer_date(dt: datetime) -> str:
    """
    Format a datetime into the required offer letter date style (e.g., "15th January, 2025").

    Parameters:
        dt (datetime): Date to format.

    Returns:
        str: Formatted date string.
    """
    day = _ordinal(dt.day)
    month = dt.strftime("%B")
    year = dt.strftime("%Y")
    return f"{day} {month}, {year}"


def _build_offer_letter_html(
    student_name: str,
    roll_number: str,
    branch: str,
    company_name: str,
    hr_name: str,
    job_title: str,
    package_lpa: float,
    offer_date: str,
) -> str:
    """
    Build the HTML content for a dummy offer letter with inline CSS.

    Parameters:
        student_name (str): Student full name.
        roll_number (str): Student roll number.
        branch (str): Student branch.
        company_name (str): Company name.
        hr_name (str): HR name.
        job_title (str): Job title.
        package_lpa (float): Package in LPA.
        offer_date (str): Offer date formatted string.

    Returns:
        str: Complete HTML document for the offer letter.
    """
    return f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Offer Letter — {company_name}</title>
  </head>
  <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:820px;margin:28px auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
      <div style="background:#003366;color:#ffffff;padding:20px 26px;">
        <div style="font-size:18px;font-weight:800;">Indian Institute of Technology Madras — Placement Cell</div>
        <div style="font-size:13px;opacity:0.95;margin-top:4px;">Offer Letter (Auto-generated)</div>
      </div>
      <div style="padding:26px;">
        <div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;">
          <div style="font-size:14px;color:#111827;"><strong>Date:</strong> {offer_date}</div>
          <div style="font-size:14px;color:#111827;"><strong>Reference:</strong> IITM/PPA/OFFER</div>
        </div>

        <div style="margin-top:18px;font-size:14px;color:#111827;">
          <p style="margin:0 0 10px 0;">To,</p>
          <p style="margin:0;"><strong>{student_name}</strong></p>
          <p style="margin:0;">Roll Number: {roll_number}</p>
          <p style="margin:0;">Branch: {branch}</p>
        </div>

        <div style="margin-top:18px;font-size:14px;line-height:1.7;color:#111827;">
          <p>Dear <strong>{student_name}</strong>,</p>
          <p>
            Congratulations! On behalf of the <strong>Indian Institute of Technology Madras — Placement Cell</strong>,
            we are pleased to inform you that you have been shortlisted for an offer with <strong>{company_name}</strong>.
          </p>
          <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;margin:14px 0;">
            <div style="font-size:14px;"><strong>Company:</strong> {company_name}</div>
            <div style="font-size:14px;"><strong>HR Contact:</strong> {hr_name}</div>
            <div style="font-size:14px;"><strong>Position:</strong> {job_title}</div>
            <div style="font-size:14px;"><strong>Compensation:</strong> {package_lpa} LPA</div>
          </div>
          <p>
            This offer is subject to the company's standard employment terms and successful completion of any formalities.
          </p>
          <p style="margin-bottom:0;">
            <strong>Terms:</strong><br/>
            - Joining Date: To be communicated by the company<br/>
            - Offer Validity: 30 days from the date of this letter
          </p>
        </div>

        <div style="margin-top:22px;">
          <div style="font-size:14px;color:#111827;">Sincerely,</div>
          <div style="margin-top:22px;font-size:14px;color:#111827;">
            <strong>Head, Placement Cell</strong><br/>
            Indian Institute of Technology Madras
          </div>
        </div>
      </div>
    </div>
  </body>
</html>
""".strip()


def generate_offer_letter(application_id: int) -> str:
    """
    Auto-generates a dummy HTML offer letter when a student is shortlisted.

    Fetches Application → StudentProfile + PlacementDrive + CompanyProfile.
    Generates a professional HTML file styled with inline CSS containing:
      - Header: "Indian Institute of Technology Madras — Placement Cell"
      - Date of offer (current date formatted as "15th January, 2025")
      - Student name, roll number, branch
      - Company name, HR name
      - Job title, package (X LPA)
      - Congratulatory message body paragraph
      - Terms: joining date placeholder, offer validity (30 days)
      - Signature block: "Head, Placement Cell, IIT Madras"
    Saves to: backend/offer_letters/offer_<application_id>.html
    Returns relative file path string.

    Parameters:
        application_id (int): Application primary key id.

    Returns:
        str: Relative offer letter file path (under backend/offer_letters/).
    """
    application = (
        Application.query.options(
            db.joinedload(Application.student),
            db.joinedload(Application.drive).joinedload(PlacementDrive.company),
        )
        .filter_by(id=int(application_id))
        .first()
    )
    if application is None:
        raise ValueError("Application not found.")

    if application.student is None or application.drive is None or application.drive.company is None:
        raise ValueError("Application is missing required linked data.")

    offer_date = _format_offer_date(datetime.now())
    html = _build_offer_letter_html(
        student_name=application.student.full_name,
        roll_number=application.student.roll_number,
        branch=application.student.branch,
        company_name=application.drive.company.company_name,
        hr_name=application.drive.company.hr_name,
        job_title=application.drive.job_title,
        package_lpa=application.drive.package_lpa,
        offer_date=offer_date,
    )

    Config.ensure_storage_directories()
    filename = f"offer_{application.id}.html"
    output_path = Path(Config.OFFER_LETTERS_FOLDER) / filename
    output_path.write_text(html, encoding="utf-8")

    return f"offer_letters/{filename}"

