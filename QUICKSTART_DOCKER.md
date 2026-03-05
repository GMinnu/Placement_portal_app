## 🚀 Quick Start Guide – IIT Madras Placement Portal (Docker)

This guide is written for absolute beginners who are comfortable following step‑by‑step terminal instructions.

You will run everything using **Docker** and **docker‑compose** – no need to install Python packages manually.

---

## ✅ Step 1: Install Docker Desktop

1. Download Docker Desktop for your OS: `https://www.docker.com/products/docker-desktop`
2. Install it using the default options.
3. Start Docker Desktop.
4. Wait until it shows **“Docker is running”** in the system tray / menu bar.

If you open a new terminal and run:

```bash
docker --version
docker-compose --version
```

you should see version numbers (no errors).

---

## ✅ Step 2: Open the Project Folder

1. Open **PowerShell** or **Command Prompt**.
2. Navigate to the project root folder (where `docker-compose.yml` lives):

```bash
cd C:\Users\sathw\Placement_portal_app\placement_portal
```

You should see files like:

- `Dockerfile`
- `docker-compose.yml`
- `backend/`
- `frontend/`

You can confirm with:

```bash
dir
```

---

## ✅ Step 3: Configure Email Settings (Optional but Recommended)

The app uses **Flask-Mail** with SMTP (e.g., Gmail) for sending emails.

1. Open `docker-compose.yml` in your editor.
2. Under the `flask:` and `celery_worker:` services, look for:

```yaml
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
ADMIN_EMAIL=admin@iitm.ac.in
```

3. Replace:
   - `your-email@gmail.com` with your Gmail (or SMTP) email.
   - `your-app-password` with an **app password** (not your normal login).

If you just want to try the UI and do **not** care about emails, you can leave these values as‑is. Email sending may fail, but the rest of the app will still work.

---

## ✅ Step 4: Build and Start All Containers

You only need **one terminal** for this.

From the `placement_portal` folder, run:

```bash
docker-compose up --build
```

What this does:

- Builds the Flask + Celery Docker image (using `Dockerfile`).
- Starts **three services**:
  - `redis` – in‑memory store and Celery broker.
  - `flask` – Flask backend + Vue frontend entry at port 5000.
  - `celery_worker` – Celery worker + Celery Beat for scheduled tasks.

**What you should see:**

- A lot of log lines as images build (first time can take a few minutes).
- After startup, you should see logs similar to:

```text
flask_1          |  * Running on http://0.0.0.0:5000
redis_1          | * Ready to accept connections
celery_worker_1  | [INFO/MainProcess] celery@... ready.
```

✅ **If you see no obvious errors and the logs keep running, the app is up.**  
Keep this terminal **open** – it is your central log window.

---

## ✅ Step 5: Open the Web App

1. Open your web browser (Chrome, Edge, etc.).
2. Go to:

```text
http://localhost:5000
```

You should see the **IIT Madras Placement Portal** login page.

**Default Admin Login:**

- Email: `admin@iitm.ac.in`
- Password: `Admin@123`

These are created automatically on first run.

---

## ✅ Step 6: (Optional) Run Containers in Background

If you don’t want to keep the logs in the foreground, you can run in **detached** mode.

From the `placement_portal` folder:

```bash
docker-compose up -d
```

Now:

- Containers run in the background.
- You can safely close the terminal.

To see which containers are running:

```bash
docker ps
```

To follow logs later:

```bash
docker-compose logs -f
```

Press `Ctrl + C` to stop tailing logs (this does **not** stop the containers).

---

## ✅ Step 7: Stop Everything Cleanly

To stop all services defined in `docker-compose.yml`:

```bash
cd C:\Users\sathw\Placement_portal_app\placement_portal
docker-compose down
```

This will:

- Stop the `flask`, `redis`, and `celery_worker` containers.
- Remove the stopped containers (images remain, so next start is faster).

---

## 📋 What Should Be Running (Docker View)

You don’t need multiple terminals like a manual setup; Docker groups services for you.

When running (either `up` or `up -d`), `docker ps` should show:

| Container        | Service        | Purpose                                  |
|------------------|----------------|------------------------------------------|
| placement_portal_flask_1        | flask         | Flask API + Vue SPA on port 5000       |
| placement_portal_redis_1        | redis         | Redis for caching + Celery broker      |
| placement_portal_celery_worker_1| celery_worker | Celery worker + Celery Beat scheduler  |

If all three are listed and healthy, your app is ready.

---

## ❓ Common Issues (Docker)

### 1. “docker: command not found”

- Docker Desktop is not installed or not added to PATH.
- Install Docker Desktop and restart your computer.

### 2. “ERROR: Couldn’t connect to Docker daemon”

- Docker Desktop might not be running.
- Start Docker Desktop and wait until it shows **“Docker is running”**.

### 3. Port 5000 already in use

- Another app is using port `5000`.
- Either stop that app, or edit `docker-compose.yml` to change:

```yaml
flask:
  ports: ["5000:5000"]
```

to something like:

```yaml
flask:
  ports: ["5001:5000"]
```

Then access `http://localhost:5001` instead.

### 4. Email errors in logs

- If SMTP credentials are not valid, email operations will fail.
- For local testing, you can ignore these, or configure real credentials as described earlier.

---

## 🎉 You’re All Set!

Once `docker-compose up --build` is running and you can open `http://localhost:5000`:

- Log in as **admin** using `admin@iitm.ac.in / Admin@123`.
- Explore admin dashboards, approve companies and drives.
- Register as a student and company to see the full workflow.

For deeper technical details (API routes, Celery jobs, data models), see the main `README.md` and `PROJECT_REPORT.md` files.

