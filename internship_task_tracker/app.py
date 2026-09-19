import calendar
import json
from io import BytesIO
from datetime import date
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape

from flask import Flask, flash, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename
import hashlib
import secrets
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

app = Flask(__name__)
app.secret_key = "internship-tracker-development-key-change-me"

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
DOC_UPLOAD_DIR = UPLOADS_DIR / "documents"
PROJECT_UPLOAD_DIR = UPLOADS_DIR / "projects"
UPLOADS_DIR.mkdir(exist_ok=True)
DOC_UPLOAD_DIR.mkdir(exist_ok=True)
PROJECT_UPLOAD_DIR.mkdir(exist_ok=True)
INTERNS_FILE = BASE_DIR / "interns.json"
TASKS_FILE = BASE_DIR / "tasks.json"
MENTORS_FILE = BASE_DIR / "mentors.json"
USERS_FILE = BASE_DIR / "users.json"
STATUSES = ("Start", "In Progress", "Completed", "Not Completed")
PRIORITIES = ("High", "Medium", "Low")
DEFAULT_DEPARTMENTS = (
    "Python Developement",
    "UI and UX Design",
    "Fullstack Developement",
    "Frontend Developement",
    "Backend Developement",
    "Digital Marketing",
    "Research and Development",
    "Video Editing",
    "Graphical Designing",
    "Android Developement",
    "HR Department",
    "Sales Department",
    "Finance Department",
)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


def calculate_end_date(joining_date, duration_months):
    joining = date.fromisoformat(joining_date)
    month_index = joining.month - 1 + int(duration_months)
    year = joining.year + month_index // 12
    month = month_index % 12 + 1
    day = min(joining.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def calculate_intern_status(end_date):
    return "Active Intern" if date.today().isoformat() <= end_date else "Past Employee"


def load_json(path):
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def available_departments(interns=None, mentors=None):
    interns = interns if interns is not None else load_json(INTERNS_FILE)
    mentors = mentors if mentors is not None else load_json(MENTORS_FILE)
    return list(DEFAULT_DEPARTMENTS)


def save_upload(file_storage, folder, prefix):
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None
    stored_name = f"{prefix}_{uuid4().hex[:12]}_{filename}"
    destination = folder / stored_name
    file_storage.save(destination)
    return {"filename": filename, "stored_name": stored_name}


def document_path(record):
    if not record or not record.get("stored_name"):
        return None
    path = DOC_UPLOAD_DIR / record["stored_name"]
    return path if path.exists() else None


def project_path(record):
    if not record or not record.get("stored_name"):
        return None
    path = PROJECT_UPLOAD_DIR / record["stored_name"]
    return path if path.exists() else None


def set_completed_timestamp(task, status):
    normalized = normalize_task_status(status)
    task["status"] = normalized
    if normalized == "Completed":
        task.setdefault("completed_at", date.today().isoformat())
    else:
        task.pop("completed_at", None)


def task_department(task, interns):
    if task.get("department"):
        return task.get("department")
    assigned_ids = task.get("assigned_intern_ids") or [task.get("intern_id")]
    for intern in interns:
        if intern.get("id") in assigned_ids:
            return intern.get("department", "")
    return ""


def get_data():
    interns = load_json(INTERNS_FILE)
    changed = False
    for intern in interns:
        duration = intern.get("duration_months")
        if duration:
            try:
                intern["end_date"] = calculate_end_date(intern["joining_date"], int(duration))
                intern["employment_status"] = calculate_intern_status(intern["end_date"])
                changed = True
            except (KeyError, TypeError, ValueError):
                pass
    if changed:
        save_json(INTERNS_FILE, interns)
    return interns, load_json(TASKS_FILE), load_json(MENTORS_FILE)


def normalize_task_status(value):
    if value is None:
        return "Start"
    status = str(value).strip()
    normalized = status.casefold()
    if normalized in {"pending", "start"}:
        return "Start"
    if normalized in {"in progress", "in_progress"}:
        return "In Progress"
    if normalized in {"completed", "done"}:
        return "Completed"
    if normalized in {"not completed", "not-completed", "notcomplete", "uncompleted"}:
        return "Not Completed"
    return status if status in STATUSES else "Start"


def is_overdue(task):
    try:
        return normalize_task_status(task.get("status")) != "Completed" and date.fromisoformat(task["deadline"]) < date.today()
    except (KeyError, TypeError, ValueError):
        return False


def intern_summary(intern, tasks):
    assigned = [{**task, "overdue": is_overdue(task)} for task in tasks
                if intern["id"] in task.get("assigned_intern_ids", [task.get("intern_id")])]
    completed = sum(normalize_task_status(task.get("status")) == "Completed" for task in assigned)
    start_tasks = sum(normalize_task_status(task.get("status")) == "Start" for task in assigned)
    not_completed_tasks = sum(normalize_task_status(task.get("status")) == "Not Completed" for task in assigned)
    completed_items = [task for task in assigned if normalize_task_status(task.get("status")) == "Completed"]
    latest_completed = max(
        completed_items,
        key=lambda task: task.get("completed_at") or task.get("deadline") or "",
        default=None,
    )
    return {**intern, "tasks": assigned, "total_tasks": len(assigned),
            "completed_tasks": completed,
            "start_tasks": start_tasks,
            "pending_tasks": start_tasks,
            "not_completed_tasks": not_completed_tasks,
            "in_progress_tasks": sum(normalize_task_status(task.get("status")) == "In Progress" for task in assigned),
            "latest_completed_task": latest_completed.get("title") if latest_completed else "No completed task yet",
            "latest_completed_at": (latest_completed.get("completed_at") or latest_completed.get("deadline") or "") if latest_completed else "",
            "progress": round(completed / len(assigned) * 100, 1) if assigned else 0}


def decorate_tasks(tasks, interns):
    names = {intern["id"]: intern["name"] for intern in interns}
    decorated = []
    for task in tasks:
        assigned_ids = task.get("assigned_intern_ids") or [task.get("intern_id")]
        assigned_names = task.get("assigned_names") or [names.get(task.get("intern_id"), "Unknown intern")]
        decorated.append({**task, "task_type": task.get("task_type", "Individual Work"),
                          "assigned_intern_ids": assigned_ids,
                          "assigned_names": assigned_names,
                          "intern_name": ", ".join(assigned_names),
                          "department": task_department(task, interns),
                          "overdue": is_overdue(task)})
    return decorated


def check_password(stored, password):
    try:
        algorithm, salt, expected = stored.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
        return actual == expected
    except ValueError:
        return False


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def find_user(identifier, users):
    identifier = identifier.strip().casefold()
    return next((u for u in users
                 if u.get("username", "").casefold() == identifier
                 or u.get("email", "").casefold() == identifier), None)


def profile_name(user, interns, mentors):
    if user.get("role") == "intern":
        item = next((i for i in interns if i.get("id") == user.get("intern_id")), None)
        return item.get("name") if item else ""
    if user.get("role") == "mentor":
        item = next((m for m in mentors if m.get("id") == user.get("mentor_id")), None)
        return item.get("name") if item else ""
    return ""


def current_user():
    return session.get("user")


def login_required():
    return "user" in session


def role_required(*roles):
    user = current_user()
    return bool(user and user.get("role") in roles)


def find_intern_for_user(user, interns):
    return next((i for i in interns if i.get("id") == user.get("intern_id")), None)


def mentor_intern_ids(user, interns):
    return {i.get("id") for i in interns if i.get("assigned_mentor") == user.get("mentor_id")}


@app.context_processor
def navigation_data():
    return {"current_year": date.today().year, "current_user": current_user()}


@app.route("/login", methods=["GET", "POST"])
def login():
    if login_required():
        return redirect(url_for("home"))

    if request.method == "POST":
        identifier = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "").strip().casefold()

        users = load_json(USERS_FILE)
        user = find_user(identifier, users)
       
        user = find_user(identifier, users)

        if user and user.get("role", "").casefold() == selected_role and check_password(user.get("password", ""), password):
                session.clear()
                session["user"] = {
                    k: user[k]
                    for k in ("id", "username", "email", "role", "mentor_id", "intern_id")
                    if k in user
                }
                flash(f"Welcome, {user.get('username', identifier)}!", "success")
                return redirect(url_for("home"))

        flash("Invalid login details or selected role.", "danger")

    return render_template("login.html")



@app.route("/admin/users", methods=["GET", "POST"])
def user_management():
    if not role_required("admin"):
        flash("Only an admin can manage login accounts.", "danger")
        return redirect(url_for("home"))
    users = load_json(USERS_FILE)
    interns, _, mentors = get_data()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip().casefold()
        profile_id = request.form.get("profile_id", "").strip()
        if not username or not email or not password or role not in {"admin", "mentor", "intern"}:
            flash("Username, email, password, and role are required.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif any(u.get("username", "").casefold() == username.casefold() or u.get("email", "").casefold() == email.casefold() for u in users):
            flash("Username or email is already in use.", "danger")
        elif role == "mentor" and not any(m.get("id") == profile_id for m in mentors):
            flash("Select a valid mentor profile.", "danger")
        elif role == "intern" and not any(i.get("id") == profile_id for i in interns):
            flash("Select a valid intern profile.", "danger")
        else:
            new_user = {"id": uuid4().hex[:10], "username": username, "email": email,
                        "password": hash_password(password), "role": role}
            if role == "mentor":
                new_user["mentor_id"] = profile_id
            elif role == "intern":
                new_user["intern_id"] = profile_id
            users.append(new_user)
            save_json(USERS_FILE, users)
            flash("Login account created successfully.", "success")
            return redirect(url_for("user_management"))
    rows = []
    for user in users:
        rows.append({**user, "profile": profile_name(user, interns, mentors)})
    return render_template("user_management.html", users=rows, interns=interns, mentors=mentors)


@app.route("/admin/users/<user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    if not role_required("admin"):
        flash("Only an admin can edit login accounts.", "danger")
        return redirect(url_for("home"))
    users = load_json(USERS_FILE)
    interns, _, mentors = get_data()
    user = next((u for u in users if u.get("id") == user_id), None)
    if not user:
        flash("User account not found.", "danger")
        return redirect(url_for("user_management"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        role = request.form.get("role", "").strip().casefold()
        profile_id = request.form.get("profile_id", "").strip()
        password = request.form.get("password", "")
        duplicate = any(u.get("id") != user_id and
                        (u.get("username", "").casefold() == username.casefold() or
                         u.get("email", "").casefold() == email.casefold()) for u in users)
        if not username or not email or role not in {"admin", "mentor", "intern"}:
            flash("Username, email, and role are required.", "danger")
        elif duplicate:
            flash("Username or email is already in use.", "danger")
        elif password and len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif role == "mentor" and not any(m.get("id") == profile_id for m in mentors):
            flash("Select a valid mentor profile.", "danger")
        elif role == "intern" and not any(i.get("id") == profile_id for i in interns):
            flash("Select a valid intern profile.", "danger")
        else:
            user["username"] = username
            user["email"] = email
            user["role"] = role
            user.pop("mentor_id", None)
            user.pop("intern_id", None)
            if role == "mentor":
                user["mentor_id"] = profile_id
            elif role == "intern":
                user["intern_id"] = profile_id
            if password:
                user["password"] = hash_password(password)
            save_json(USERS_FILE, users)
            if current_user().get("id") == user_id: # type: ignore
                session["user"] = {k: user[k] for k in ("id", "username", "email", "role", "mentor_id", "intern_id") if k in user}
            flash("User account updated.", "success")
            return redirect(url_for("user_management"))
    return render_template("edit_user.html", user=user, interns=interns, mentors=mentors)


@app.post("/admin/users/<user_id>/delete")
def delete_user(user_id):
    if not role_required("admin"):
        flash("Only an admin can delete login accounts.", "danger")
        return redirect(url_for("home"))
    users = load_json(USERS_FILE)
    if current_user().get("id") == user_id:
        flash("You cannot delete the account you are currently using.", "danger")
    elif not any(u.get("id") == user_id for u in users):
        flash("User account not found.", "danger")
    else:
        save_json(USERS_FILE, [u for u in users if u.get("id") != user_id])
        flash("User account deleted.", "success")
    return redirect(url_for("user_management"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/")
def home():
    if not login_required():
        return redirect(url_for("login"))
    role = current_user().get("role")
    if role == "admin":
        return redirect(url_for("dashboard"))
    if role == "mentor":
        return redirect(url_for("mentor_dashboard"))
    return redirect(url_for("intern_dashboard"))


@app.route("/admin/dashboard")
def dashboard():
    if not role_required("admin"):
        flash("Admin access is required.", "danger")
        return redirect(url_for("home"))
    interns, tasks, mentors = get_data()
    completed = sum(normalize_task_status(task.get("status")) == "Completed" for task in tasks)
    start = sum(normalize_task_status(task.get("status")) == "Start" for task in tasks)
    not_completed = sum(normalize_task_status(task.get("status")) == "Not Completed" for task in tasks)
    in_progress = sum(normalize_task_status(task.get("status")) == "In Progress" for task in tasks)
    overdue = sum(is_overdue(task) for task in tasks)
    active_interns = sum(intern.get("employment_status") == "Active Intern" for intern in interns)
    past_employees = sum(intern.get("employment_status") == "Past Employee" for intern in interns)
    total_departments = len({intern.get("department") for intern in interns if intern.get("department")})
    intern_summaries = [intern_summary(i, tasks) for i in interns]
    recent_completed = sorted(
        [i for i in intern_summaries if i.get("latest_completed_at")],
        key=lambda i: i.get("latest_completed_at", ""), reverse=True
    )
    return render_template("dashboard.html", interns=intern_summaries, recent_completed=recent_completed,
                           tasks=decorate_tasks(tasks, interns), total_interns=len(interns),
                           mentors=mentors, total_mentors=len(mentors), total_tasks=len(tasks),
                           completed=completed, start=start, not_completed=not_completed, in_progress=in_progress,
                           overdue=overdue, active_interns=active_interns,
                           past_employees=past_employees, total_departments=total_departments,
                           progress=round(completed / len(tasks) * 100, 1) if tasks else 0)


@app.route("/mentor/dashboard")
def mentor_dashboard():
    if not role_required("mentor"):
        flash("Mentor access is required.", "danger")
        return redirect(url_for("home"))
    interns, tasks, _ = get_data()
    ids = mentor_intern_ids(current_user(), interns)
    my_interns = [intern_summary(i, tasks) for i in interns if i.get("id") in ids]
    my_tasks = [t for t in tasks if ids.intersection(t.get("assigned_intern_ids", [t.get("intern_id")]))]
    completed = sum(normalize_task_status(t.get("status")) == "Completed" for t in my_tasks)
    return render_template("mentor_dashboard.html", interns=my_interns,
                           tasks=decorate_tasks(my_tasks, interns), total_tasks=len(my_tasks),
                           completed=completed, progress=round(completed / len(my_tasks) * 100, 1) if my_tasks else 0)


@app.route("/intern/dashboard")
def intern_dashboard():
    if not role_required("intern"):
        flash("Intern access is required.", "danger")
        return redirect(url_for("home"))
    interns, tasks, mentors = get_data()
    intern = find_intern_for_user(current_user(), interns)
    if not intern:
        session.clear()
        flash("Your intern profile could not be found.", "danger")
        return redirect(url_for("login"))
    summary = intern_summary(intern, tasks)
    mentor = next((m for m in mentors if m.get("id") == intern.get("assigned_mentor")), None)
    return render_template("intern_dashboard.html", intern=summary, mentor=mentor)


@app.route("/interns")
def view_interns():
    if not role_required("admin", "mentor"):
        flash("You do not have permission to view the intern directory.", "danger")
        return redirect(url_for("home"))
    interns, tasks, mentors = get_data()
    mentor_names = {mentor["id"]: mentor["name"] for mentor in mentors}
    enriched = [{**intern, "mentor_name": mentor_names.get(intern.get("assigned_mentor"), "Unassigned")}
                for intern in interns]
    if role_required("mentor"):
        ids = mentor_intern_ids(current_user(), interns)
        enriched = [i for i in enriched if i.get("id") in ids]
    enriched = [intern_summary(i, tasks) for i in enriched]
    enriched.sort(key=lambda item: (0 if item.get("employment_status") == "Active Intern" else 1,
                                    item.get("end_date") or "9999-12-31", item.get("name", "").casefold()))
    return render_template("interns.html", interns=enriched, departments=available_departments(interns, mentors))


@app.route("/interns/add", methods=["GET", "POST"])
def add_intern():
    if not role_required("admin"):
        flash("Only an admin can add interns.", "danger")
        return redirect(url_for("home"))
    interns, _, mentors = get_data()
    if request.method == "POST":
        intern = {field: request.form.get(field, "").strip() for field in
                  ("id", "name", "email", "phone", "department", "joining_date", "duration_months")}
        intern["assigned_mentor"] = request.form.get("assigned_mentor", "").strip()
        uploaded = save_upload(request.files.get("document"), DOC_UPLOAD_DIR, "intern")
        if uploaded:
            intern["document"] = uploaded
        try:
            duration_months = int(intern["duration_months"])
            end_date = calculate_end_date(intern["joining_date"], duration_months)
        except (TypeError, ValueError):
            duration_months = 0
            end_date = ""
        if not all(intern[field] for field in
                   ("id", "name", "email", "phone", "department", "joining_date")) or duration_months <= 0:
            flash("Please complete every intern field.", "danger")
        elif any(item.get("id") == intern["id"] for item in interns):
            flash("That Intern ID is already in use.", "danger")
        else:
            intern["duration_months"] = duration_months
            intern["end_date"] = end_date
            intern["employment_status"] = calculate_intern_status(end_date)
            interns.append(intern)
            save_json(INTERNS_FILE, interns)
            flash("Intern added successfully.", "success")
            return redirect(url_for("view_interns"))
    return render_template("add_intern.html", intern=None, mentors=mentors, departments=available_departments(interns, mentors))


@app.route("/mentors")
def view_mentors():
    if not role_required("admin"):
        flash("Only an admin can manage mentors.", "danger")
        return redirect(url_for("home"))
    interns, _, mentors = get_data()
    rows = []
    for mentor in mentors:
        assigned_count = sum(i.get("assigned_mentor") == mentor.get("id") for i in interns)
        rows.append({**mentor, "assigned_count": assigned_count})
    return render_template("mentors.html", mentors=rows, departments=available_departments(interns, mentors))


@app.route("/mentors/add", methods=["GET", "POST"])
def add_mentor():
    if not role_required("admin"):
        flash("Only an admin can add mentors.", "danger")
        return redirect(url_for("home"))
    interns, _, mentors = get_data()
    if request.method == "POST":
        mentor = {
            "id": request.form.get("id", "").strip(),
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "department": request.form.get("department", "").strip(),
        }
        uploaded = save_upload(request.files.get("document"), DOC_UPLOAD_DIR, "mentor")
        if uploaded:
            mentor["document"] = uploaded
        if not all(mentor.values()):
            flash("Please complete every mentor field.", "danger")
        elif any(m.get("id") == mentor["id"] for m in mentors):
            flash("That Mentor ID is already in use.", "danger")
        else:
            mentors.append(mentor)
            save_json(MENTORS_FILE, mentors)
            flash("Mentor added successfully.", "success")
            return redirect(url_for("view_mentors"))
    return render_template("add_mentor.html", mentor=None, departments=available_departments(interns, mentors))


@app.route("/mentors/<mentor_id>/edit", methods=["GET", "POST"])
def edit_mentor(mentor_id):
    if not role_required("admin"):
        flash("Only an admin can edit mentors.", "danger")
        return redirect(url_for("home"))
    interns, _, mentors = get_data()
    mentor = next((m for m in mentors if m.get("id") == mentor_id), None)
    if not mentor:
        flash("Mentor not found.", "danger")
        return redirect(url_for("view_mentors"))
    if request.method == "POST":
        mentor["name"] = request.form.get("name", "").strip()
        mentor["email"] = request.form.get("email", "").strip()
        mentor["phone"] = request.form.get("phone", "").strip()
        mentor["department"] = request.form.get("department", "").strip()
        uploaded = save_upload(request.files.get("document"), DOC_UPLOAD_DIR, "mentor")
        if uploaded:
            mentor["document"] = uploaded
        if not all(mentor.get(field) for field in ("name", "email", "phone", "department")):
            flash("Please complete every mentor field.", "danger")
        else:
            save_json(MENTORS_FILE, mentors)
            flash("Mentor details updated.", "success")
            return redirect(url_for("view_mentors"))
    return render_template("add_mentor.html", mentor=mentor, departments=available_departments(interns, mentors))


@app.post("/mentors/<mentor_id>/delete")
def delete_mentor(mentor_id):
    if not role_required("admin"):
        flash("Only an admin can delete mentors.", "danger")
        return redirect(url_for("home"))
    interns, _, mentors = get_data()
    if any(i.get("assigned_mentor") == mentor_id for i in interns):
        flash("Reassign this mentor's interns before deleting the mentor.", "danger")
    elif not any(m.get("id") == mentor_id for m in mentors):
        flash("Mentor not found.", "danger")
    else:
        save_json(MENTORS_FILE, [m for m in mentors if m.get("id") != mentor_id])
        flash("Mentor deleted.", "success")
    return redirect(url_for("view_mentors"))


@app.get("/documents/<kind>/<item_id>")
def download_document(kind, item_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    interns, _, mentors = get_data()
    record = None
    if kind == "intern":
        record = next((i for i in interns if i.get("id") == item_id), None)
        allowed = user.get("role") == "admin" or (
            user.get("role") == "intern" and user.get("intern_id") == item_id
        ) or (
            user.get("role") == "mentor" and item_id in mentor_intern_ids(user, interns)
        )
    elif kind == "mentor":
        record = next((m for m in mentors if m.get("id") == item_id), None)
        allowed = user.get("role") == "admin" or (
            user.get("role") == "mentor" and user.get("mentor_id") == item_id
        )
    else:
        return redirect(url_for("home"))
    if not record or not allowed:
        flash("You do not have permission to download this document.", "danger")
        return redirect(url_for("home"))
    path = document_path(record.get("document"))
    if not path:
        flash("No document is available for this person.", "warning")
        return redirect(url_for("home"))
    return send_file(path, as_attachment=True, download_name=record["document"].get("filename", path.name))




@app.route("/interns/<intern_id>/edit", methods=["GET", "POST"])
def edit_intern(intern_id):
    if not role_required("admin"):
        flash("Only an admin can edit interns.", "danger")
        return redirect(url_for("home"))
    interns, _, mentors = get_data()
    intern = next((item for item in interns if item.get("id") == intern_id), None)
    if intern is None:
        flash("Intern not found.", "danger")
        return redirect(url_for("view_interns"))
    if request.method == "POST":
        for field in ("name", "email", "phone", "department", "joining_date"):
            intern[field] = request.form.get(field, "").strip()
        try:
            duration_months = int(request.form.get("duration_months", "0"))
            end_date = calculate_end_date(intern["joining_date"], duration_months)
        except (TypeError, ValueError):
            flash("Enter a valid internship duration and joining date.", "danger")
            return render_template("add_intern.html", intern=intern, mentors=mentors, departments=available_departments(interns, mentors))
        if duration_months <= 0:
            flash("Internship duration must be greater than zero.", "danger")
            return render_template("add_intern.html", intern=intern, mentors=mentors, departments=available_departments(interns, mentors))
        intern["duration_months"] = duration_months
        intern["end_date"] = end_date
        intern["employment_status"] = calculate_intern_status(end_date)
        intern["assigned_mentor"] = request.form.get("assigned_mentor", "").strip()
        uploaded = save_upload(request.files.get("document"), DOC_UPLOAD_DIR, "intern")
        if uploaded:
            intern["document"] = uploaded
        save_json(INTERNS_FILE, interns)
        flash("Intern details updated.", "success")
        return redirect(url_for("view_interns"))
    return render_template("add_intern.html", intern=intern, mentors=mentors, departments=available_departments(interns, mentors))


@app.post("/interns/<intern_id>/delete")
def delete_intern(intern_id):
    if not role_required("admin"):
        flash("Only an admin can delete interns.", "danger")
        return redirect(url_for("home"))
    interns, tasks, _ = get_data()
    save_json(INTERNS_FILE, [item for item in interns if item.get("id") != intern_id])
    save_json(TASKS_FILE, [task for task in tasks if task.get("intern_id") != intern_id])
    flash("Intern and assigned tasks deleted.", "success")
    return redirect(url_for("view_interns"))


@app.route("/tasks")
def view_tasks():
    if not role_required("admin", "mentor"):
        flash("Only admins and mentors can view the full task list.", "danger")
        return redirect(url_for("home"))
    interns, tasks, _ = get_data()
    if role_required("mentor"):
        ids = mentor_intern_ids(current_user(), interns)
        tasks = [t for t in tasks if ids.intersection(
            t.get("assigned_intern_ids", [t.get("intern_id")]))]
    return render_template("tasks.html", tasks=decorate_tasks(tasks, interns))


@app.get("/tasks/<task_id>")
def view_task(task_id):
    if not role_required("admin", "mentor"):
        flash("Only admins and mentors can view task details.", "danger")
        return redirect(url_for("home"))
    interns, tasks, mentors = get_data()
    task = next((item for item in tasks if item.get("id") == task_id), None)
    if task is None:
        flash("Task not found.", "danger")
        return redirect(url_for("view_tasks"))
    if role_required("mentor") and not mentor_intern_ids(current_user(), interns).intersection(
            task.get("assigned_intern_ids", [task.get("intern_id")])):
        flash("You cannot view this task.", "danger")
        return redirect(url_for("view_tasks"))
    intern_by_id = {item.get("id"): item for item in interns}
    mentor_names = {mentor["id"]: mentor["name"] for mentor in mentors}
    assigned_interns = []
    for intern_id in task.get("assigned_intern_ids", [task.get("intern_id")]):
        intern = intern_by_id.get(intern_id)
        if intern:
            assigned_interns.append({**intern, "mentor_name": mentor_names.get(
                intern.get("assigned_mentor"), "Unassigned")})
    return render_template("task_detail.html", task=decorate_tasks([task], interns)[0],
                           assigned_interns=assigned_interns)


@app.route("/tasks/add", methods=["GET", "POST"])
def assign_task():
    if not role_required("admin", "mentor"):
        flash("Only admins and mentors can assign tasks.", "danger")
        return redirect(url_for("home"))
    interns, tasks, _ = get_data()
    if role_required("mentor"):
        ids = mentor_intern_ids(current_user(), interns)
        interns = [i for i in interns if i.get("id") in ids]
    if request.method == "POST":
        manual_task_id = request.form.get("task_id", "").strip()
        task_type = request.form.get("task_type", "Individual Work").strip()
        selected_ids = [item.strip() for item in request.form.getlist("selected_intern_ids") if item.strip()]
        intern_id = request.form.get("intern_id", "").strip()
        if task_type == "Individual Work":
            selected_ids = [intern_id]
        department = request.form.get("department", "").strip()
        project_id = request.form.get("project_id", "").strip()
        title = request.form.get("title", "").strip()
        if role_required("mentor") and project_id:
            project = next((p for p in tasks if p.get("id") == project_id and p.get("created_by_role", "admin") == "admin"), None)
            if project:
                title = project.get("title", "").strip()
        manual_task_id = request.form.get("task_id", "").strip()
        task = {"id": manual_task_id, "intern_id": selected_ids[0] if selected_ids else "",
                "task_type": task_type,
                "department": department,
                "title": title,
                "description": request.form.get("description", "").strip(),
                "deadline": request.form.get("deadline", ""),
                "priority": request.form.get("priority", "Medium"),
                "status": normalize_task_status(request.form.get("status", "Start")),
                "created_by_role": current_user().get("role")}
        valid_ids = {item.get("id") for item in interns}
        if not manual_task_id:
            flash("Enter a Task ID.", "danger")
        elif any(existing.get("id", "").casefold() == manual_task_id.casefold() for existing in tasks):
            flash("That Task ID already exists. Enter a unique Task ID.", "danger")
        elif role_required("mentor") and (not project_id or not next((p for p in tasks if p.get("id") == project_id and p.get("created_by_role", "admin") == "admin"), None)):
            flash("Choose an admin-created project before assigning work.", "danger")
        elif task_type not in ("Individual Work", "Team Work"):
            flash("Select a valid task type.", "danger")
        elif not department or not selected_ids or not task["title"] or not task["deadline"]:
            flash("Select a department and at least one intern, then provide a title and deadline.", "danger")
        elif any(item not in valid_ids for item in selected_ids):
            flash("You cannot assign a task to that intern.", "danger")
        elif any(next((i.get("department") for i in interns if i.get("id") == item), "") != department for item in selected_ids):
            flash("All selected interns must belong to the chosen department.", "danger")
        elif task_type == "Individual Work" and len(selected_ids) != 1:
            flash("Individual Work must have exactly one intern selected.", "danger")
        else:
            set_completed_timestamp(task, task["status"])
            task["assigned_intern_ids"] = selected_ids
            task["assigned_names"] = [next(item["name"] for item in interns if item["id"] == item_id)
                                       for item_id in selected_ids]
            tasks.append(task)
            save_json(TASKS_FILE, tasks)
            flash("Task assigned successfully.", "success")
            return redirect(url_for("view_tasks"))
    projects = [p for p in tasks if p.get("created_by_role", "admin") == "admin"] if role_required("mentor") else []
    return render_template("assign_task.html", interns=interns,
                           departments=available_departments(interns),
                           projects=projects, task=None,
                           priorities=PRIORITIES, statuses=STATUSES)


@app.route("/tasks/<task_id>/edit", methods=["GET", "POST"])
def edit_task(task_id):
    if not role_required("admin", "mentor"):
        flash("Only admins and mentors can edit tasks.", "danger")
        return redirect(url_for("home"))
    all_interns, tasks, _ = get_data()
    task = next((item for item in tasks if item.get("id") == task_id), None)
    if task is None:
        flash("Task not found.", "danger")
        return redirect(url_for("view_tasks"))
    if role_required("mentor") and not mentor_intern_ids(current_user(), all_interns).intersection(
            task.get("assigned_intern_ids", [task.get("intern_id")])):
        flash("You cannot edit this task.", "danger")
        return redirect(url_for("view_tasks"))
    interns = all_interns
    if role_required("mentor"):
        interns = [i for i in all_interns if i.get("id") in mentor_intern_ids(current_user(), all_interns)]
    active_interns = interns
    task.setdefault("assigned_intern_ids", [task.get("intern_id")] if task.get("intern_id") else [])
    if not task.get("department"):
        task["department"] = task_department(task, all_interns)
    if request.method == "POST":
        task_type = request.form.get("task_type", "Individual Work").strip()
        selected_ids = [item.strip() for item in request.form.getlist("selected_intern_ids") if item.strip()]
        if task_type == "Individual Work":
            selected_ids = [request.form.get("intern_id", "").strip()]
        department = request.form.get("department", "").strip()
        project_id = request.form.get("project_id", "").strip()
        if role_required("mentor") and project_id:
            project = next((p for p in tasks if p.get("id") == project_id), None)
            if project:
                task["title"] = project.get("title", "").strip()
        else:
            task["title"] = request.form.get("title", "").strip()
        task["description"] = request.form.get("description", "").strip()
        task["deadline"] = request.form.get("deadline", "").strip()
        task["priority"] = request.form.get("priority", "Medium").strip()
        set_completed_timestamp(task, request.form.get("status", "Start").strip())
        task["department"] = department
        if role_required("mentor") and (not project_id or not next((p for p in tasks if p.get("id") == project_id and p.get("created_by_role", "admin") == "admin"), None)):
            flash("Choose an admin-created project before editing this task.", "danger")
        elif task_type not in ("Individual Work", "Team Work") or not selected_ids or any(item not in {i.get("id") for i in active_interns} for item in selected_ids):
            flash("You cannot assign this task to that intern.", "danger")
        elif not department:
            flash("Select a department.", "danger")
        elif any(next((i.get("department") for i in active_interns if i.get("id") == item), "") != department for item in selected_ids):
            flash("All selected interns must belong to the chosen department.", "danger")
        elif task_type == "Individual Work" and len(selected_ids) != 1:
            flash("Individual Work must have exactly one intern selected.", "danger")
        else:
            task["task_type"] = task_type
            task["intern_id"] = selected_ids[0]
            task["assigned_intern_ids"] = selected_ids
            task["assigned_names"] = [next(item["name"] for item in active_interns if item["id"] == item_id)
                                       for item_id in selected_ids]
            save_json(TASKS_FILE, tasks)
            flash("Task details updated.", "success")
            return redirect(url_for("view_tasks"))
    projects = [p for p in tasks if p.get("created_by_role", "admin") == "admin"] if role_required("mentor") else []
    return render_template("assign_task.html", interns=active_interns,
                           departments=available_departments(active_interns),
                           projects=projects, task=task,
                           priorities=PRIORITIES, statuses=STATUSES)


@app.post("/tasks/<task_id>/delete")
def delete_task(task_id):
    if not role_required("admin", "mentor"):
        flash("Only admins and mentors can delete tasks.", "danger")
        return redirect(url_for("home"))
    interns, tasks, _ = get_data()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if task is None:
        flash("Task not found.", "danger")
    elif role_required("mentor") and not mentor_intern_ids(current_user(), interns).intersection(task.get("assigned_intern_ids", [task.get("intern_id")])):
        flash("You cannot delete this task.", "danger")
    else:
        save_json(TASKS_FILE, [t for t in tasks if t.get("id") != task_id])
        flash("Task deleted.", "success")
    return redirect(url_for("view_tasks"))


@app.post("/intern/tasks/<task_id>/status")
def update_intern_task_status(task_id):
    if not role_required("intern"):
        flash("Only interns can use this action.", "danger")
        return redirect(url_for("home"))
    interns, tasks, _ = get_data()
    user = current_user()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if task is None or user.get("intern_id") not in set(task.get("assigned_intern_ids") or [task.get("intern_id")]):
        flash("Task not found or access denied.", "danger")
        return redirect(url_for("intern_dashboard"))
    status = request.form.get("status", "").strip()
    normalized_status = normalize_task_status(status)
    if normalized_status not in STATUSES:
        flash("Invalid task status.", "danger")
    else:
        set_completed_timestamp(task, normalized_status)
        save_json(TASKS_FILE, tasks)
        flash("Task status updated. Your progress has been recalculated.", "success")
    return redirect(url_for("intern_dashboard"))


@app.route("/reports")
def reports():
    if not role_required("admin", "mentor"):
        flash("Only admins and mentors can view reports.", "danger")
        return redirect(url_for("home"))
    interns, tasks, mentors = get_data()
    mentor_names = {mentor["id"]: mentor["name"] for mentor in mentors}
    enriched = [{**intern, "mentor_name": mentor_names.get(intern.get("assigned_mentor"), "Unassigned")}
                for intern in interns]
    if role_required("mentor"):
        ids = mentor_intern_ids(current_user(), interns)
        enriched = [i for i in enriched if i.get("id") in ids]
    intern_rows = [intern_summary(i, tasks) for i in enriched]
    mentor_rows = []
    for mentor in mentors:
        if role_required("mentor") and mentor.get("id") != current_user().get("mentor_id"):
            continue
        mentor_interns = [i for i in interns if i.get("assigned_mentor") == mentor.get("id")]
        mentor_rows.append({
            **mentor,
            "assigned_count": len(mentor_interns),
            "total_tasks": sum(intern_summary(i, tasks).get("total_tasks", 0) for i in mentor_interns),
            "completed_tasks": sum(intern_summary(i, tasks).get("completed_tasks", 0) for i in mentor_interns),
        })
    return render_template("report.html", interns=intern_rows, mentors=mentor_rows,
                           departments=available_departments(interns, mentors))


@app.get("/download-report")
def download_report():
    if not role_required("admin", "mentor"):
        flash("Only admins and mentors can download reports.", "danger")
        return redirect(url_for("home"))
    interns, tasks, mentors = get_data()
    mentor_names = {mentor["id"]: mentor["name"] for mentor in mentors}
    requested_intern = request.args.get("intern_id", "").strip()
    requested_mentor = request.args.get("mentor_id", "").strip()

    if role_required("mentor"):
        allowed_ids = mentor_intern_ids(current_user(), interns)
        interns = [intern for intern in interns if intern.get("id") in allowed_ids]
        if requested_mentor and requested_mentor != current_user().get("mentor_id"):
            requested_mentor = ""

    if requested_intern:
        interns = [intern for intern in interns if intern.get("id") == requested_intern]
    enriched = [{**intern, "mentor_name": mentor_names.get(intern.get("assigned_mentor"), "Unassigned")}
                for intern in interns]
    report_rows = [intern_summary(intern, tasks) for intern in enriched]

    if requested_mentor:
        mentor = next((m for m in mentors if m.get("id") == requested_mentor), None)
        if not mentor:
            flash("Mentor not found.", "danger")
            return redirect(url_for("reports"))
        assigned = [i for i in load_json(INTERNS_FILE) if i.get("assigned_mentor") == requested_mentor]
        report_rows = [intern_summary(i, tasks) for i in assigned]
        title = f"Mentor Report - {mentor.get('name', 'Mentor')}"
        filename = f"mentor-report-{secure_filename(mentor.get('name', 'mentor'))}.pdf"
    else:
        title = "Progress Reports" if not requested_intern else f"Progress Report - {report_rows[0].get('name', 'Intern') if report_rows else 'Intern'}"
        filename = "progress-reports.pdf" if not requested_intern else f"progress-report-{secure_filename(report_rows[0].get('name', 'intern'))}.pdf"

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title=title)
    styles = getSampleStyleSheet()
    story = [Paragraph(escape(title), styles["Title"])]
    for intern in report_rows:
        story.extend([
            Paragraph(escape(intern.get("name", "")), styles["Heading2"]),
            Paragraph(escape(f'{intern.get("department", "")} · {intern.get("email", "")} · ID {intern.get("id", "")}'), styles["BodyText"]),
            Paragraph(escape(f'Mentor: {intern.get("mentor_name", "Unassigned")}'), styles["BodyText"]),
            Paragraph(escape(f'Progress: {intern.get("progress", 0)}% · Latest completed: {intern.get("latest_completed_task", "None")}'), styles["BodyText"]),
            Spacer(1, 6),
        ])
        rows = [["Assigned task", "Deadline", "Status"]]
        for task in intern.get("tasks", []):
            rows.append([Paragraph(escape(task.get("title", "")), styles["BodyText"]),
                         task.get("deadline", ""), task.get("status", "")])
        if len(rows) == 1:
            rows.append(["No tasks assigned.", "", ""])
        table = Table(rows, colWidths=[210, 100, 100], repeatRows=1)
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, "#cccccc"),
                                   ("BACKGROUND", (0, 0), (-1, 0), "#eef2f5")]))
        story.append(table)
        story.append(Spacer(1, 14))
    document.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.post("/intern/tasks/<task_id>/upload")
def upload_project(task_id):
    if not role_required("intern"):
        flash("Only interns can upload project files.", "danger")
        return redirect(url_for("home"))
    interns, tasks, _ = get_data()
    user = current_user()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if task is None or user.get("intern_id") not in (task.get("assigned_intern_ids") or [task.get("intern_id")]):
        flash("Task not found or access denied.", "danger")
        return redirect(url_for("intern_dashboard"))
    uploaded = save_upload(request.files.get("project_file"), PROJECT_UPLOAD_DIR, task_id)
    if not uploaded:
        flash("Choose a ZIP project file to upload.", "danger")
    elif not uploaded["filename"].lower().endswith(".zip"):
        path = PROJECT_UPLOAD_DIR / uploaded["stored_name"]
        path.unlink(missing_ok=True)
        flash("Only .zip project files are accepted.", "danger")
    else:
        task["project_file"] = uploaded
        save_json(TASKS_FILE, tasks)
        flash("Project ZIP uploaded successfully.", "success")
    return redirect(url_for("intern_dashboard"))


@app.get("/tasks/<task_id>/project")
def download_project(task_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    interns, tasks, _ = get_data()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for("home"))
    assigned = set(task.get("assigned_intern_ids") or [task.get("intern_id")])
    allowed = user.get("role") == "admin" or (
        user.get("role") == "intern" and user.get("intern_id") in assigned
    ) or (
        user.get("role") == "mentor" and mentor_intern_ids(user, interns).intersection(assigned)
    )
    if not allowed:
        flash("You do not have permission to download this project.", "danger")
        return redirect(url_for("home"))
    path = project_path(task.get("project_file"))
    if not path:
        flash("No project file is available.", "warning")
        return redirect(url_for("home"))
    return send_file(path, as_attachment=True, download_name=task["project_file"].get("filename", path.name))


if __name__ == "__main__":
    app.run(debug=True)
