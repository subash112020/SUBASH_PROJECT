import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "internship.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS mentors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE
            );

            CREATE TABLE IF NOT EXISTS interns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                department TEXT NOT NULL,
                joining_date TEXT NOT NULL,
                duration_months INTEGER NOT NULL DEFAULT 0,
                end_date TEXT,
                employment_status TEXT NOT NULL DEFAULT 'Active Intern',
                assigned_mentor TEXT,
                FOREIGN KEY (assigned_mentor) REFERENCES mentors(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                intern_id TEXT NOT NULL,
                task_type TEXT NOT NULL DEFAULT 'Individual Work',
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                deadline TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (intern_id) REFERENCES interns(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS task_members (
                task_id TEXT NOT NULL,
                intern_id TEXT NOT NULL,
                PRIMARY KEY (task_id, intern_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (intern_id) REFERENCES interns(id) ON DELETE CASCADE
            );
            """
        )
        task_columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
        if "task_type" not in task_columns:
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN task_type TEXT NOT NULL DEFAULT 'Individual Work'"
            )
        connection.execute(
            """INSERT OR IGNORE INTO task_members (task_id, intern_id)
             SELECT tasks.id, tasks.intern_id FROM tasks
             JOIN interns ON interns.id = tasks.intern_id
             WHERE tasks.intern_id IS NOT NULL AND tasks.intern_id != ''"""
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(interns)")}
        if "duration_months" not in columns:
            connection.execute("ALTER TABLE interns ADD COLUMN duration_months INTEGER NOT NULL DEFAULT 0")
        if "end_date" not in columns:
            connection.execute("ALTER TABLE interns ADD COLUMN end_date TEXT")
        if "employment_status" not in columns:
            connection.execute("ALTER TABLE interns ADD COLUMN employment_status TEXT NOT NULL DEFAULT 'Active Intern'")


def _load_legacy_json(filename):
    path = BASE_DIR / filename
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return value if isinstance(value, list) else []


def migrate_legacy_json():
    """Import existing JSON records once, without replacing database records."""
    with get_connection() as connection:
        if connection.execute("SELECT 1 FROM mentors LIMIT 1").fetchone() is None:
            connection.executemany(
                "INSERT OR IGNORE INTO mentors (id, name) VALUES (?, ?)",
                [(mentor.get("id"), mentor.get("name"))
                 for mentor in _load_legacy_json("mentors.json")
                 if mentor.get("id") and mentor.get("name")],
            )

        if connection.execute("SELECT 1 FROM interns LIMIT 1").fetchone() is None:
            connection.executemany(
                """INSERT OR IGNORE INTO interns
                   (id, name, email, phone, department, joining_date, assigned_mentor)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [(intern.get("id"), intern.get("name", ""), intern.get("email", ""),
                  intern.get("phone", ""), intern.get("department", ""),
                  intern.get("joining_date", ""), intern.get("assigned_mentor"))
                 for intern in _load_legacy_json("interns.json")
                 if intern.get("id")],
            )

        if connection.execute("SELECT 1 FROM tasks LIMIT 1").fetchone() is None:
            connection.executemany(
                """INSERT OR IGNORE INTO tasks
                   (id, intern_id, title, description, deadline, priority, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [(task.get("id"), task.get("intern_id"), task.get("title", ""),
                  task.get("description", ""), task.get("deadline", ""),
                  task.get("priority", "Medium"), task.get("status", "Start"))
                 for task in _load_legacy_json("tasks.json")
                 if task.get("id") and task.get("intern_id")],
            )


if __name__ == "__main__":
    initialize_database()
    migrate_legacy_json()
    print(f"Database initialized: {DATABASE}")