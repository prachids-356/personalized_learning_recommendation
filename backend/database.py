"""Persistent storage for the learning engine's runtime data."""

from contextlib import contextmanager
import os
import sqlite3
from threading import Lock

import pandas as pd
from sqlalchemy import create_engine, inspect, text


DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "data", "files", "learning_engine.db"),
)
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
_database_lock = Lock()


@contextmanager
def connection():
    if engine is not None:
        with engine.begin() as db:
            yield db
        return

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH, timeout=30)
    try:
        yield db
        db.commit()
    finally:
        db.close()


def initialize_from_csv(students_csv, logs_csv, retention_csv):
    """Create the database and import seed CSVs only when tables are empty."""
    with _database_lock, connection() as db:
        has_students_table = (
            inspect(db).has_table("students")
            if engine is not None
            else db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='students'"
            ).fetchone()
        )
        if has_students_table:
            count_query = text("SELECT COUNT(*) FROM students") if engine is not None else "SELECT COUNT(*) FROM students"
            count_result = db.execute(count_query).fetchone()
            count = count_result[0]
            if count:
                return

        pd.read_csv(students_csv).to_sql("students", db, if_exists="replace", index=False)
        pd.read_csv(logs_csv).to_sql("student_logs", db, if_exists="replace", index=False)
        pd.read_csv(retention_csv).to_sql("retention_logs", db, if_exists="replace", index=False)


def load_dataframes():
    with connection() as db:
        students = pd.read_sql_query("SELECT * FROM students", db)
        logs = pd.read_sql_query("SELECT * FROM student_logs", db)
        retention = pd.read_sql_query("SELECT * FROM retention_logs", db)
    return students, logs, retention


def save_dataframes(students, logs, retention):
    """Persist all runtime tables in one transaction."""
    with _database_lock, connection() as db:
        students.to_sql("students", db, if_exists="replace", index=False)
        logs.to_sql("student_logs", db, if_exists="replace", index=False)
        retention.to_sql("retention_logs", db, if_exists="replace", index=False)