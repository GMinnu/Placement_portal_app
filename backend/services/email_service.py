"""
backend/services/email_service.py

HTML email sending utilities and IIT Madras-branded email templates.

All emails use inline CSS because Bootstrap classes do not work reliably in email clients.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from flask import current_app
from flask_mail import Message

from backend.extensions import mail


def send_email(subject: str, recipients: List[str], html: str, sender: Optional[str] = None) -> None:
    """
    Send an HTML email using Flask-Mail.

    Parameters:
        subject (str): Email subject line.
        recipients (List[str]): List of recipient email addresses.
        html (str): Full HTML string for the email body.
        sender (Optional[str]): Sender email address. If None, uses MAIL_DEFAULT_SENDER.

    Returns:
        None. Sends the email via the configured SMTP server.
    """
    resolved_sender = sender or current_app.config.get("MAIL_DEFAULT_SENDER")
    msg = Message(subject=subject, recipients=recipients, sender=resolved_sender)
    msg.html = html
    try:
        mail.send(msg)
    except Exception as exc:
        # Email delivery failures should not break API flows; log and continue.
        try:
            current_app.logger.exception("Email send failed: %s", exc)
        except Exception:
            # If logging itself fails, ignore to keep request flow intact.
            pass


def _build_email_shell(title: str, body_html: str) -> str:
    """
    Build the common IIT Madras-branded email wrapper with inline CSS.

    Parameters:
        title (str): Heading shown in the email body.
        body_html (str): Inner HTML content (already escaped/safe).

    Returns:
        str: Full HTML document as a string.
    """
    year = datetime.now().year
    return f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
  </head>
  <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
    <div style="width:100%;padding:24px 0;">
      <div style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:10px;overflow:hidden;border:1px solid #e5e7eb;">
        <div style="background:#003366;color:#ffffff;padding:18px 22px;">
          <div style="font-size:16px;font-weight:700;letter-spacing:0.3px;">Indian Institute of Technology Madras — Placement Cell</div>
          <div style="font-size:13px;opacity:0.95;margin-top:4px;">IIT Madras Placement Portal</div>
        </div>
        <div style="padding:22px;">
          <div style="font-size:18px;font-weight:700;color:#111827;margin-bottom:10px;">{title}</div>
          <div style="font-size:14px;line-height:1.6;color:#374151;">
            {body_html}
          </div>
          <div style="margin-top:18px;font-size:13px;color:#6b7280;">
            Regards,<br/>
            Placement Cell Team<br/>
            Indian Institute of Technology Madras
          </div>
        </div>
        <div style="background:#f9fafb;padding:12px 22px;font-size:12px;color:#6b7280;">
          © {year} Indian Institute of Technology Madras. All rights reserved.
        </div>
      </div>
    </div>
  </body>
</html>
""".strip()


def send_welcome_student(student_name: str, email: str) -> None:
    """
    Send a welcome email to a newly registered student.

    Parameters:
        student_name (str): Student full name.
        email (str): Student email address.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{student_name}</strong>,</p>
    <p>Welcome to the <strong>IIT Madras Placement Portal</strong>. Your student account has been created successfully.</p>
    <p>You can now log in, complete your profile, upload your resume, and apply to approved placement drives.</p>
    """
    html = _build_email_shell("Welcome to IIT Madras Placement Portal", body)
    send_email("Welcome to IIT Madras Placement Portal", [email], html)


def send_welcome_company(company_name: str, hr_email: str) -> None:
    """
    Send a welcome email to a newly registered company (pending approval).

    Parameters:
        company_name (str): Company name.
        hr_email (str): HR email address.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{company_name}</strong> Team,</p>
    <p>Thank you for registering on the <strong>IIT Madras Placement Portal</strong>.</p>
    <p>Your account is currently <strong>pending admin approval</strong>. You will receive an email once the approval decision is made.</p>
    """
    html = _build_email_shell("Company Registration Received", body)
    send_email("IIT Madras Placement Portal — Registration Received", [hr_email], html)


def send_company_approved(company_name: str, hr_email: str) -> None:
    """
    Notify a company that their registration has been approved.

    Parameters:
        company_name (str): Company name.
        hr_email (str): HR email address.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{company_name}</strong> Team,</p>
    <p>Your company registration has been <strong style="color:#16a34a;">approved</strong> by the IIT Madras Placement Cell.</p>
    <p>You can now log in and create placement drives for student applications.</p>
    """
    html = _build_email_shell("Company Approved", body)
    send_email("IIT Madras Placement Portal — Company Approved", [hr_email], html)


def send_company_rejected(company_name: str, hr_email: str, reason: str) -> None:
    """
    Notify a company that their registration has been rejected.

    Parameters:
        company_name (str): Company name.
        hr_email (str): HR email address.
        reason (str): Rejection reason entered by admin.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{company_name}</strong> Team,</p>
    <p>Your company registration has been <strong style="color:#dc2626;">rejected</strong> by the IIT Madras Placement Cell.</p>
    <p><strong>Reason:</strong> {reason}</p>
    <p>If you believe this is an error, you may contact the Placement Cell for clarification.</p>
    """
    html = _build_email_shell("Company Rejected", body)
    send_email("IIT Madras Placement Portal — Company Rejected", [hr_email], html)


def send_drive_approved(company_name: str, hr_email: str, job_title: str) -> None:
    """
    Notify a company that their placement drive has been approved.

    Parameters:
        company_name (str): Company name.
        hr_email (str): HR email address.
        job_title (str): Job title for the drive.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{company_name}</strong> Team,</p>
    <p>Your placement drive for <strong>{job_title}</strong> has been <strong style="color:#16a34a;">approved</strong>.</p>
    <p>Eligible students can now view and apply to this drive on the IIT Madras Placement Portal.</p>
    """
    html = _build_email_shell("Drive Approved", body)
    send_email(f"IIT Madras Placement Portal — Drive Approved: {job_title}", [hr_email], html)


def send_drive_rejected(company_name: str, hr_email: str, job_title: str, reason: str) -> None:
    """
    Notify a company that their placement drive has been rejected.

    Parameters:
        company_name (str): Company name.
        hr_email (str): HR email address.
        job_title (str): Job title for the drive.
        reason (str): Rejection reason entered by admin.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{company_name}</strong> Team,</p>
    <p>Your placement drive for <strong>{job_title}</strong> has been <strong style="color:#dc2626;">rejected</strong>.</p>
    <p><strong>Reason:</strong> {reason}</p>
    <p>You may update the drive details and submit again for approval.</p>
    """
    html = _build_email_shell("Drive Rejected", body)
    send_email(f"IIT Madras Placement Portal — Drive Rejected: {job_title}", [hr_email], html)


def send_deadline_reminder(
    student_name: str,
    student_email: str,
    job_title: str,
    company_name: str,
    days_left: int,
    deadline: str,
) -> None:
    """
    Send a deadline reminder email to a student for an upcoming drive deadline.

    Parameters:
        student_name (str): Student full name.
        student_email (str): Student email address.
        job_title (str): Job title of the drive.
        company_name (str): Company name.
        days_left (int): Number of days remaining until deadline.
        deadline (str): Deadline formatted string to display.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{student_name}</strong>,</p>
    <p>This is a reminder that the application deadline for <strong>{job_title}</strong> at <strong>{company_name}</strong> is approaching.</p>
    <div style="background:#f3f4f6;border:1px solid #e5e7eb;border-radius:8px;padding:12px 14px;margin:14px 0;">
      <div style="font-size:14px;"><strong>Deadline:</strong> {deadline}</div>
      <div style="font-size:14px;"><strong>Days left:</strong> {days_left}</div>
    </div>
    <p>Please log in to the IIT Madras Placement Portal to apply before the deadline.</p>
    """
    html = _build_email_shell("Application Deadline Reminder", body)
    subject = f"Reminder: {job_title} at {company_name} — Deadline in {days_left} days"
    send_email(subject, [student_email], html)


def send_shortlist_notification(student_name: str, student_email: str, company_name: str, job_title: str) -> None:
    """
    Notify a student that they have been shortlisted for a drive.

    Parameters:
        student_name (str): Student full name.
        student_email (str): Student email address.
        company_name (str): Company name.
        job_title (str): Job title.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{student_name}</strong>,</p>
    <p>Congratulations! You have been <strong style="color:#0284c7;">shortlisted</strong> for <strong>{job_title}</strong> at <strong>{company_name}</strong>.</p>
    <p>Your offer letter is now available for download in the IIT Madras Placement Portal under your applications.</p>
    """
    html = _build_email_shell("Shortlisted for Interview", body)
    send_email(f"Shortlisted: {job_title} at {company_name}", [student_email], html)


def send_selection_notification(
    student_name: str,
    student_email: str,
    company_name: str,
    job_title: str,
    package_lpa: float,
) -> None:
    """
    Notify a student that they have been selected for a drive.

    Parameters:
        student_name (str): Student full name.
        student_email (str): Student email address.
        company_name (str): Company name.
        job_title (str): Job title.
        package_lpa (float): Offered CTC in LPA.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{student_name}</strong>,</p>
    <p>Congratulations! You have been <strong style="color:#16a34a;">selected</strong> for <strong>{job_title}</strong> at <strong>{company_name}</strong>.</p>
    <p><strong>Package:</strong> {package_lpa} LPA</p>
    <p>We wish you continued success. Please check the portal for further instructions.</p>
    """
    html = _build_email_shell("Selection Confirmation", body)
    send_email(f"Selected: {job_title} at {company_name}", [student_email], html)


def send_rejection_notification(
    student_name: str,
    student_email: str,
    company_name: str,
    job_title: str,
) -> None:
    """
    Notify a student that they have been rejected for a drive.

    Parameters:
        student_name (str): Student full name.
        student_email (str): Student email address.
        company_name (str): Company name.
        job_title (str): Job title.

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear <strong>{student_name}</strong>,</p>
    <p>Thank you for participating in the recruitment process for <strong>{job_title}</strong> at <strong>{company_name}</strong>.</p>
    <p>We regret to inform you that you have not been selected for this opportunity.</p>
    <p>We encourage you to continue applying to other suitable placement drives through the IIT Madras Placement Portal.</p>
    """
    html = _build_email_shell("Application Update", body)
    send_email(f"Application Update: {job_title} at {company_name}", [student_email], html)


def send_monthly_report_to_admin(admin_email: str, month_name: str, report_html: str) -> None:
    """
    Send the monthly HTML report to the admin email address.

    Parameters:
        admin_email (str): Admin recipient email.
        month_name (str): Month name label used in the subject and header.
        report_html (str): HTML fragment containing the report body (tables, metrics).

    Returns:
        None. Sends an HTML email.
    """
    body = f"""
    <p>Dear Admin,</p>
    <p>Please find below the placement activity report for <strong>{month_name}</strong>.</p>
    <div style="margin-top:12px;">{report_html}</div>
    """
    html = _build_email_shell(f"Monthly Report — {month_name}", body)
    send_email(f"IIT Madras Placement Portal — Monthly Report ({month_name})", [admin_email], html)

