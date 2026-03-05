## Placement Portal Application for Indian Institute of Technology Madras

### 1. Title and Abstract

**Title**: IIT Madras Placement Portal – Full‑Stack Recruitment Management System

**Abstract (≈200 words)**  
The Placement Portal Application (PPA) is a full‑stack web system built for the **Indian Institute of Technology Madras** to streamline the campus recruitment process. It unifies the workflows of three primary stakeholders: students, companies, and the institute’s placement cell administrators. Students can register, maintain academic profiles, upload resumes, view eligible placement drives, and track application statuses. Companies can register, manage their profiles, create and manage placement drives, and shortlist or select candidates. Administrators oversee approvals of companies and drives, monitor applications, and gain insights through analytics dashboards.

The system is developed using a **Flask** backend with **SQLite** and **SQLAlchemy**, and a **Vue.js 3** single‑page frontend delivered via CDN. **JWT‑based authentication**, password hashing, and role‑based guards protect all sensitive operations. Background jobs implemented with **Celery** and **Redis** send deadline reminders and monthly activity reports and generate CSV exports. The portal follows a consistent JSON response format and uses **Bootstrap 5** for a responsive, user‑friendly interface. Docker and docker‑compose encapsulate the backend, Celery worker, and Redis services for portable deployment. Overall, the PPA demonstrates a production‑style architecture while remaining lightweight enough for academic use and evaluation.

### 2. Introduction

The campus placement process at **Indian Institute of Technology Madras** involves multiple stakeholders and large volumes of data. Traditionally, registrations, eligibility checks, drive announcements, and offer tracking are handled through ad‑hoc tools or manual coordination. This leads to inefficient communication, inconsistent data, and limited visibility into aggregate metrics.

The Placement Portal Application addresses these issues through a unified web platform. Students receive a single interface to maintain profiles and apply to drives; companies can manage their recruitment pipelines, while administrators oversee approvals and obtain high‑level analytics. Key objectives include:

- Centralizing placement data in a single, structured database.
- Automating repetitive processes like eligibility checks and deadline reminders.
- Providing secure, role‑based access control.
- Offering clear analytics for policy and decision‑making.

### 3. System Architecture

The system follows a layered architecture separating frontend, backend API, persistence, caching, and background processing layers.

**ASCII Architecture Diagram**

```text
                       +-------------------------------+
                       |   Browser (Vue 3 SPA)        |
                       |   - Bootstrap 5 UI           |
                       |   - Chart.js analytics       |
                       +-------------------------------+
                                     |
                                     | HTTPS / JSON (JWT)
                                     v
+---------------------------------------------------------------+
|                    Flask Backend API                          |
|  - app.py (create_app)                                       |
|  - Blueprints: auth, admin, company, student                 |
|  - Services: auth, eligibility, email, offer, export         |
|  - SQLAlchemy models for User, Student, Company, Drive, etc. |
+---------------------------------------------------------------+
       |                                |                 |
       | ORM                            | Cache           | Async Tasks
       v                                v                 v
+-----------------+          +-----------------+   +--------------------+
| SQLite Database |          | Redis (Caching) |   | Celery + Redis     |
| - Users         |          | - Dashboard     |   | - Reminders        |
| - Profiles      |          | - Analytics     |   | - Monthly reports  |
| - Drives        |          +-----------------+   | - CSV exports      |
| - Applications  |                                +--------------------+
| - Export Jobs   |
+-----------------+
```

The backend exposes RESTful endpoints secured by JWT tokens. The Vue.js SPA communicates exclusively through these APIs, storing the token in `localStorage`. Background tasks share the same application codebase via Celery workers configured to run within the Flask app context.

### 4. Database Design

The application uses six core models implemented with SQLAlchemy:

1. **User**
   - Fields: `id`, `email`, `password_hash`, `role`, `is_active`, `is_blacklisted`, `created_at`.
   - Purpose: Unifies credentials for all roles (admin, company, student).
   - Relationships: One‑to‑one with `StudentProfile` and `CompanyProfile`.

2. **StudentProfile**
   - Fields: `id`, `user_id`, `full_name`, `roll_number`, `branch`, `year_of_study`, `cgpa`, `phone`, `resume_path`, `created_at`, `updated_at`.
   - Purpose: Stores academic and personal data for each student.
   - Relationships: Many `Application` records and many `ExportJob` records.

3. **CompanyProfile**
   - Fields: `id`, `user_id`, `company_name`, `hr_name`, `hr_email`, `website`, `description`, `approval_status`, `rejection_reason`, `created_at`.
   - Purpose: Represents companies participating in placements.
   - Relationships: One‑to‑many with `PlacementDrive`.

4. **PlacementDrive**
   - Fields: `id`, `company_id`, `job_title`, `job_description`, `eligible_branches`, `min_cgpa`, `eligible_year`, `package_lpa`, `application_deadline`, `status`, `rejection_reason`, `created_at`.
   - Purpose: Captures each recruitment drive created by a company.
   - Relationships: Many `Application` records, belongs to `CompanyProfile`.

5. **Application**
   - Fields: `id`, `student_id`, `drive_id`, `applied_at`, `status`, `offer_letter_path`, `updated_at`.
   - Constraints: Unique `(student_id, drive_id)` pair to prevent duplicate applications.
   - Purpose: Tracks per‑drive student participation and decisions.

6. **ExportJob**
   - Fields: `id`, `student_id`, `status`, `file_path`, `requested_at`, `completed_at`.
   - Purpose: Records CSV export requests and their lifecycle.

Relationships include:

- `User` 1‑to‑1 `StudentProfile` (students).
- `User` 1‑to‑1 `CompanyProfile` (companies).
- `CompanyProfile` 1‑to‑many `PlacementDrive`.
- `StudentProfile` 1‑to‑many `Application`.
- `PlacementDrive` 1‑to‑many `Application`.
- `StudentProfile` 1‑to‑many `ExportJob`.

### 5. API Design

The backend follows REST principles with JSON payloads, resource‑oriented URIs, and HTTP verbs that map naturally to CRUD operations. All responses conform to a consistent envelope:

- Success: `{ "success": true, "data": { ... }, "message": "..." }`
- Error: `{ "success": false, "error": "Descriptive error message" }`

**JWT Authentication Flow**

- On login or registration, the server issues a short‑lived JWT containing the user id as identity and the role as an additional claim.
- The client stores the token in `localStorage` as `ppa_token`.
- For subsequent requests, the client includes `Authorization: Bearer <token>` in headers.
- Decorators `@jwt_required()` and a custom `@role_required(role)` enforce authentication and authorization on protected routes.
- The `/api/auth/me` endpoint returns the user object and associated profile details, enabling the SPA to personalize views.

### 6. Frontend Design

The frontend is a single‑page application implemented with **Vue.js 3** loaded via CDN. Instead of a router library, navigation is controlled by a reactive `currentPage` variable. Major page groups include:

- **Public**: Login, student registration, company registration.
- **Admin**: Dashboard, companies, students, drives, applications, analytics (Chart.js).
- **Company**: Dashboard, profile, create drive, drive applications.
- **Student**: Dashboard (with filters), profile (with resume upload), applications (with export).

State is held centrally in the root `createApp` instance, including `token`, `currentUser`, page‑specific collections, and loading indicators. All HTTP communication uses the `apiCall` method wrapping `fetch()` with JSON parsing and error handling. Bootstrap 5 is applied for cards, tables, forms, badges, and responsive grid layouts.

### 7. Background Jobs

Background processing is handled by **Celery** with **Redis** as broker and result backend:

- **Daily Deadline Reminders (`send_deadline_reminders`)**
  - Scheduled via Celery Beat at 8:00 AM.
  - Finds all approved drives with deadlines in the next three days.
  - Identifies eligible students who have not applied and emails them reminders.

- **Monthly Report (`send_monthly_report`)**
  - Scheduled on the first day of every month at 7:00 AM.
  - Aggregates the previous month’s drives, applications, and selections.
  - Builds an HTML report with a company‑wise breakdown table.
  - Sends the report to the placement cell admin email.

- **CSV Export (`generate_csv_export`)**
  - Triggered by a student action.
  - Writes a CSV file of all their applications, then updates the `ExportJob` record.
  - Frontend polls the job status and allows download once ready.

All tasks run inside a Flask app context to reuse configuration, SQLAlchemy session, and email utilities.

### 8. Security

Security is addressed through several layers:

- **Password Hashing**: All passwords are hashed using Werkzeug’s `generate_password_hash` and `check_password_hash`. Plaintext passwords are never stored.
- **JWT Auth**: Tokens encode user id and role. Protected endpoints require `@jwt_required()` and are further guarded by `@role_required('admin' | 'company' | 'student')`.
- **Account Flags**: `is_active` and `is_blacklisted` are enforced during login and in the role guard. Blacklisted users cannot access protected operations.
- **Input Validation**: Registration and profile update services validate required fields, uniqueness of email and roll number, eligibility constraints, and drive deadlines.
- **File Handling**: Resume uploads enforce file type (.pdf/.doc/.docx) and size limit (5 MB) and are stored in a dedicated uploads directory.

### 9. Caching Strategy

The application uses **Flask‑Caching** with Redis backend to improve responsiveness:

- **Admin Dashboard (`/api/admin/dashboard`)**
  - Cached for 5 minutes to avoid repeated heavy joins for counts and recent lists.

- **Admin Analytics (`/api/admin/analytics`)**
  - Cached for 10 minutes due to aggregate queries and chart preparation.

- **Student Dashboard (`/api/student/dashboard`)**
  - Cached for 2 minutes per student and filter combination to smooth repeated polling for available drives.

Cache keys include relevant parameters (such as student id and query string) so that each logical view is consistent and isolated.

### 10. Features Implemented

- Unified user table with role‑based behavior for admin, company, and student.
- Student profile management with academic data and resume upload.
- Company registration with admin approval workflow and drive creation.
- Placement drive lifecycle (pending, approved, rejected) with eligibility constraints.
- Application tracking with statuses (applied, shortlisted, selected, rejected).
- Automatic offer letter generation for shortlisted candidates.
- CSV export of student applications.
- Admin dashboards, searchable tables, and analytics charts.
- Email notifications for welcomes, approvals, rejections, reminders, selections, and reports.
- Dockerized environment with Flask API, Redis, and Celery worker.

### 11. Deployment

Deployment is container‑based:

- The **Dockerfile** builds a Python 3.11 image, installs backend dependencies, copies the project, and exposes port 5000.
- **docker‑compose.yml** orchestrates three services:
  - `redis` – key‑value store and message broker.
  - `flask` – Flask API serving both backend routes and the SPA entry.
  - `celery_worker` – Celery worker running with Beat enabled for scheduled tasks.

By adjusting SMTP credentials and using `docker-compose up --build`, the Placement Portal Application can be brought online consistently across different environments.

