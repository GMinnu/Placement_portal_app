"""
backend/tasks/monthly_report_tasks.py

Celery task: generate + email monthly HTML report to admin.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

from sqlalchemy import func

from backend.config import Config
from backend.extensions import celery, db
from backend.models.application import Application
from backend.models.company import CompanyProfile
from backend.models.drive import PlacementDrive
from backend.services.email_service import send_monthly_report_to_admin


def _previous_month_range(now: datetime) -> Tuple[datetime, datetime, str]:
    """
    Compute the datetime range for the previous calendar month.

    Parameters:
        now (datetime): Current datetime.

    Returns:
        Tuple[datetime, datetime, str]: (start, end, month_name_label).
    """
    year = now.year
    month = now.month
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    start = datetime(prev_year, prev_month, 1, tzinfo=timezone.utc)
    if prev_month == 12:
        end = datetime(prev_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(prev_year, prev_month + 1, 1, tzinfo=timezone.utc)

    month_name = start.strftime("%B %Y")
    return start, end, month_name


def _build_report_html(total_drives: int, total_apps: int, total_selected: int, rows: List[dict]) -> str:
    """
    Build the HTML body for the monthly report using email-safe inline styles.

    Parameters:
        total_drives (int): Total drives conducted in the period.
        total_apps (int): Total applications in the period.
        total_selected (int): Total selected applications in the period.
        rows (List[dict]): Company-wise breakdown rows.

    Returns:
        str: HTML fragment for the report.
    """
    table_rows = ""
    for r in rows:
        table_rows += f"""
        <tr>
          <td style="padding:10px 12px;border-top:1px solid #e5e7eb;">{r['company_name']}</td>
          <td style="padding:10px 12px;border-top:1px solid #e5e7eb;text-align:right;">{r['drives']}</td>
          <td style="padding:10px 12px;border-top:1px solid #e5e7eb;text-align:right;">{r['applications']}</td>
          <td style="padding:10px 12px;border-top:1px solid #e5e7eb;text-align:right;">{r['selected']}</td>
        </tr>
        """.strip()

    return f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:10px 0 16px 0;">
      <div style="flex:1;min-width:180px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;">
        <div style="font-size:12px;color:#6b7280;">Total Drives Conducted</div>
        <div style="font-size:20px;font-weight:800;color:#111827;margin-top:4px;">{total_drives}</div>
      </div>
      <div style="flex:1;min-width:180px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;">
        <div style="font-size:12px;color:#6b7280;">Total Applications Received</div>
        <div style="font-size:20px;font-weight:800;color:#111827;margin-top:4px;">{total_apps}</div>
      </div>
      <div style="flex:1;min-width:180px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;">
        <div style="font-size:12px;color:#6b7280;">Total Students Selected</div>
        <div style="font-size:20px;font-weight:800;color:#111827;margin-top:4px;">{total_selected}</div>
      </div>
    </div>

    <div style="margin-top:10px;">
      <div style="font-size:15px;font-weight:800;color:#111827;margin-bottom:8px;">Company-wise Breakdown</div>
      <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
        <thead>
          <tr style="background:#003366;color:#ffffff;">
            <th style="text-align:left;padding:10px 12px;">Company</th>
            <th style="text-align:right;padding:10px 12px;">Drives</th>
            <th style="text-align:right;padding:10px 12px;">Applications</th>
            <th style="text-align:right;padding:10px 12px;">Selected</th>
          </tr>
        </thead>
        <tbody>
          {table_rows if table_rows else '<tr><td colspan="4" style="padding:12px;color:#6b7280;">No data for this period.</td></tr>'}
        </tbody>
      </table>
    </div>
    """.strip()


@celery.task(name="backend.tasks.monthly_report_tasks.send_monthly_report")
def send_monthly_report() -> dict:
    """
    Runs on 1st of every month at 7:00 AM via Celery Beat.
    Generates an HTML report for the previous month containing:
      - Total drives conducted
      - Total applications received
      - Total students selected
      - Company-wise breakdown table (HTML table with Bootstrap styling)
    Sends this HTML email to admin's email address from config.

    Parameters:
        None.

    Returns:
        dict: Summary containing totals used in the report.
    """
    now = datetime.now(timezone.utc)
    start, end, month_name = _previous_month_range(now)

    total_drives = PlacementDrive.query.filter(PlacementDrive.created_at >= start, PlacementDrive.created_at < end).count()
    total_apps = Application.query.filter(Application.applied_at >= start, Application.applied_at < end).count()
    total_selected = (
        Application.query.filter(
            Application.status == "selected",
            Application.applied_at >= start,
            Application.applied_at < end,
        ).count()
    )

    drive_counts = (
        db.session.query(CompanyProfile.company_name, func.count(PlacementDrive.id))
        .join(PlacementDrive, PlacementDrive.company_id == CompanyProfile.id)
        .filter(PlacementDrive.created_at >= start, PlacementDrive.created_at < end)
        .group_by(CompanyProfile.company_name)
        .all()
    )
    app_counts = (
        db.session.query(CompanyProfile.company_name, func.count(Application.id))
        .join(PlacementDrive, PlacementDrive.company_id == CompanyProfile.id)
        .join(Application, Application.drive_id == PlacementDrive.id)
        .filter(Application.applied_at >= start, Application.applied_at < end)
        .group_by(CompanyProfile.company_name)
        .all()
    )
    selected_counts = (
        db.session.query(CompanyProfile.company_name, func.count(Application.id))
        .join(PlacementDrive, PlacementDrive.company_id == CompanyProfile.id)
        .join(Application, Application.drive_id == PlacementDrive.id)
        .filter(
            Application.status == "selected",
            Application.applied_at >= start,
            Application.applied_at < end,
        )
        .group_by(CompanyProfile.company_name)
        .all()
    )

    drive_map = {name: int(cnt) for name, cnt in drive_counts}
    app_map = {name: int(cnt) for name, cnt in app_counts}
    sel_map = {name: int(cnt) for name, cnt in selected_counts}

    company_names = sorted(set(drive_map.keys()) | set(app_map.keys()) | set(sel_map.keys()))
    rows = [
        {
            "company_name": name,
            "drives": drive_map.get(name, 0),
            "applications": app_map.get(name, 0),
            "selected": sel_map.get(name, 0),
        }
        for name in company_names
    ]

    report_html = _build_report_html(total_drives, total_apps, total_selected, rows)
    send_monthly_report_to_admin(Config.ADMIN_EMAIL, month_name, report_html)

    return {"month": month_name, "total_drives": total_drives, "total_apps": total_apps, "total_selected": total_selected}

