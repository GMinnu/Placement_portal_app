## IIT Madras Placement Portal Application

### Project Overview

The Placement Portal Application (PPA) is a full‑stack web application for the **Indian Institute of Technology Madras** that streamlines campus recruitment. It supports three primary roles:

- **Admin** – manages approvals, analytics, and platform‑wide monitoring.
- **Company** – registers, creates placement drives, and manages applications.
- **Student** – maintains academic profile, uploads resume, browses eligible drives, and applies.

The portal centralizes placement activities of the **Indian Institute of Technology Madras** placement cell, ensuring secure authentication, automated email notifications, background jobs for reminders/reports, and CSV exports.

### Tech Stack

| Layer            | Technology                            | Version   | Purpose                                      |
|-----------------|----------------------------------------|-----------|----------------------------------------------|
| Backend API     | Flask                                  | 3.0.0     | REST API and app factory                     |
| ORM             | Flask‑SQLAlchemy / SQLAlchemy          | 3.1.1 / 2.0.23 | Database access over SQLite             |
| Auth            | Flask‑JWT‑Extended + Werkzeug          | 4.6.0 / 3.0.1 | JWT auth and password hashing            |
| Email           | Flask‑Mail                             | 0.10.0    | SMTP email sending                           |
| Caching         | Flask‑Caching (Redis backend)          | 2.1.0     | Caching for dashboards and analytics         |
| Async Jobs      | Celery + Redis                         | 5.3.6 / 5.0.1 | Background tasks and scheduling          |
| Config          | python‑dotenv                          | 1.0.0     | Environment variable loading                 |
| Database        | SQLite                                 | —         | Application relational store                 |
| Frontend UI     | Vue.js 3 via CDN                       | —         | SPA client, routing via `currentPage`        |
| Styling         | Bootstrap 5.3 via CDN                  | —         | Responsive layout and components             |
| Charts          | Chart.js via CDN                       | —         | Admin analytics visualizations               |
| Deployment      | Docker + docker‑compose                | —         | Containerized backend + Celery + Redis       |

### Project Structure

```text
placement_portal/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── extensions.py
│   ├── requirements.txt
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── student.py
│   │   ├── company.py
│   │   ├── drive.py
│   │   ├── application.py
│   │   └── export_job.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py
│   │   ├── admin_routes.py
│   │   ├── company_routes.py
│   │   └── student_routes.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── eligibility_service.py
│   │   ├── email_service.py
│   │   ├── offer_letter_service.py
│   │   └── export_service.py
│   ├── tasks/
│   │   ├── celery_worker.py
│   │   ├── reminder_tasks.py
│   │   ├── monthly_report_tasks.py
│   │   └── export_tasks.py
│   ├── uploads/
│   ├── exports/
│   └── offer_letters/
├── frontend/
│   ├── index.html
│   └── app.js
├── Dockerfile
├── docker-compose.yml
├── README.md
└── PROJECT_REPORT.md
```

### Prerequisites

- **Python** 3.11+
- **Docker Desktop** (for containerized setup)
- **Redis** (pulled automatically via Docker image in docker‑compose)

### Quick Start with Docker

The commands below assume you are in the `placement_portal` folder (where `Dockerfile` and `docker-compose.yml` live).

```bash
# 1) Open a terminal in the project root folder
cd placement_portal

# 2) (Optional, one-time) Build the Docker image manually
docker build -t iitm-placement-portal .

# 3) Start all services (Flask API, Redis, Celery worker) and build images
docker-compose up --build

# 4) After services start, open the app in your browser
#    URL: http://localhost:5000
#    Default admin login: admin@iitm.ac.in / Admin@123
```

#### Common Docker Commands (Beginner Cheatsheet)

Run these from inside the `placement_portal` folder:

```bash
# Start containers in the background (detached mode)
docker-compose up -d

# See running containers
docker ps

# See logs for all services
docker-compose logs -f

# Stop all containers defined in docker-compose.yml
docker-compose down

# Rebuild images after changing backend code
docker-compose up --build
```

### Manual Setup (without Docker)

```bash
cd backend
pip install -r requirements.txt
python app.py

# In a new terminal from placement_portal/backend
celery -A tasks.celery_worker.celery worker --beat --loglevel=info
```

### Environment Variables (`.env` example)

| Key             | Description                                     | Example Value                        |
|----------------|-------------------------------------------------|--------------------------------------|
| SECRET_KEY     | Flask secret key                                | `iitm-placement-secret-2024`         |
| JWT_SECRET_KEY | JWT signing key                                 | `iitm-jwt-secret-2024`               |
| DATABASE_URL   | SQLAlchemy database URL                         | `sqlite:///placement_portal.db`      |
| REDIS_URL      | Redis URL for cache and Celery                  | `redis://localhost:6379/0`           |
| MAIL_SERVER    | SMTP server host                                | `smtp.gmail.com`                     |
| MAIL_PORT      | SMTP port                                       | `587`                                |
| MAIL_USE_TLS   | Enable TLS                                      | `true`                               |
| MAIL_USERNAME  | SMTP username (sender email)                    | `your-email@gmail.com`               |
| MAIL_PASSWORD  | SMTP app password                               | `your-app-password`                  |
| ADMIN_EMAIL    | Admin report recipient email                    | `admin@iitm.ac.in`                   |

### Default Admin Credentials

On first run, the backend automatically creates a default admin:

- **Email**: `admin@iitm.ac.in`
- **Password**: `Admin@123`

### API Routes Reference (Summary)

| Method | Endpoint                                  | Auth         | Role     | Description                                       |
|--------|-------------------------------------------|-------------|----------|---------------------------------------------------|
| POST   | `/api/auth/register/student`              | None        | Public   | Register student + profile                        |
| POST   | `/api/auth/register/company`              | None        | Public   | Register company + profile                        |
| POST   | `/api/auth/login`                         | None        | Public   | Login, returns JWT + role                         |
| GET    | `/api/auth/me`                            | JWT         | Any      | Current user + profile                            |
| GET    | `/api/admin/dashboard`                    | JWT         | Admin    | Dashboard metrics + recent activity               |
| GET    | `/api/admin/companies`                    | JWT         | Admin    | List companies + search                           |
| POST   | `/api/admin/companies/<id>/approve`       | JWT         | Admin    | Approve company                                   |
| POST   | `/api/admin/companies/<id>/reject`        | JWT         | Admin    | Reject company with reason                        |
| POST   | `/api/admin/companies/<id>/blacklist`     | JWT         | Admin    | Blacklist company                                 |
| GET    | `/api/admin/students`                     | JWT         | Admin    | List students + search                            |
| POST   | `/api/admin/students/<id>/blacklist`      | JWT         | Admin    | Blacklist student                                 |
| GET    | `/api/admin/drives`                       | JWT         | Admin    | List drives                                       |
| POST   | `/api/admin/drives/<id>/approve`          | JWT         | Admin    | Approve drive                                     |
| POST   | `/api/admin/drives/<id>/reject`           | JWT         | Admin    | Reject drive with reason                          |
| GET    | `/api/admin/applications`                 | JWT         | Admin    | List applications with joins                      |
| GET    | `/api/admin/analytics`                    | JWT         | Admin    | Analytics for charts                              |
| GET    | `/api/company/dashboard`                  | JWT         | Company  | Company profile + drives                          |
| GET    | `/api/company/profile`                    | JWT         | Company  | Company profile                                   |
| PUT    | `/api/company/profile`                    | JWT         | Company  | Update company profile                            |
| POST   | `/api/company/drives`                     | JWT         | Company  | Create placement drive                            |
| GET    | `/api/company/drives`                     | JWT         | Company  | List own drives                                   |
| GET    | `/api/company/drives/<id>`                | JWT         | Company  | Drive details                                     |
| PUT    | `/api/company/drives/<id>`                | JWT         | Company  | Update pending drive                              |
| GET    | `/api/company/drives/<id>/applications`   | JWT         | Company  | Applications for drive                            |
| POST   | `/api/company/applications/<id>/shortlist`| JWT         | Company  | Shortlist + offer letter + email                  |
| POST   | `/api/company/applications/<id>/select`   | JWT         | Company  | Mark selected + email                             |
| POST   | `/api/company/applications/<id>/reject`   | JWT         | Company  | Mark rejected + email                             |
| GET    | `/api/student/dashboard`                  | JWT         | Student  | Eligible drives (cached)                          |
| GET    | `/api/student/profile`                    | JWT         | Student  | Student profile + email                           |
| PUT    | `/api/student/profile`                    | JWT         | Student  | Update profile                                    |
| POST   | `/api/student/profile/resume`             | JWT         | Student  | Upload resume file                                |
| GET    | `/api/student/resume/<filename>`          | JWT         | Student  | Serve resume                                      |
| POST   | `/api/student/drives/<id>/apply`          | JWT         | Student  | Apply to drive with eligibility checks            |
| GET    | `/api/student/applications`               | JWT         | Student  | List own applications                             |
| GET    | `/api/student/applications/<id>/offer-letter` | JWT     | Student  | View offer letter HTML                            |
| POST   | `/api/student/export`                     | JWT         | Student  | Create export job + trigger Celery                |
| GET    | `/api/student/export/<job_id>/status`     | JWT         | Student  | Poll export job status                            |
| GET    | `/api/student/export/<job_id>/download`   | JWT         | Student  | Download CSV                                      |

### Celery Jobs Reference

- **`send_deadline_reminders`** (daily at 8:00 AM)
  - Finds all approved drives with deadlines in the next 3 days.
  - For each drive, finds eligible students who have not applied.
  - Sends HTML reminder emails to these students.

- **`send_monthly_report`** (1st of every month at 7:00 AM)
  - Computes previous month statistics:
    - Total drives conducted.
    - Total applications received.
    - Total students selected.
    - Company‑wise breakdown.
  - Builds a styled HTML report table.
  - Emails the report to `ADMIN_EMAIL`.

- **`generate_csv_export`** (on demand)
  - Triggered when a student clicks *Export Applications*.
  - Writes CSV: Student ID, Name, Roll, Company, Job Title, Package LPA, Application Date, Status.
  - Stores file in `backend/exports/`.
  - Updates `ExportJob` status and file path.

### Features Checklist

- [x] Unified user model for admin/company/student.
|- [x] Student profile management with resume upload.
- [x] Company profile and placement drive management.
- [x] Admin approvals for companies and drives.
- [x] JWT‑based authentication with role guards.
- [x] Redis‑backed caching for admin dashboards and analytics.
- [x] Celery background jobs for reminders, reports, and CSV exports.
- [x] HTML email templates with IIT Madras branding.
- [x] Automatic offer letter generation on shortlist.
- [x] Vue 3 SPA frontend with Bootstrap 5 UI.
- [x] Dockerized deployment with flask + redis + celery_worker services.

