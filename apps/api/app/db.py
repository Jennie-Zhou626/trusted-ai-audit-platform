import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable

from .config import DB_PATH


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]


def fetch_one(query: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    with connect() as conn:
        return row_to_dict(conn.execute(query, tuple(params)).fetchone())


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                wallet_address TEXT DEFAULT '',
                contact TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_type TEXT NOT NULL,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                source TEXT DEFAULT '',
                license_type TEXT NOT NULL,
                file_id INTEGER NOT NULL REFERENCES files(id),
                dataset_hash TEXT NOT NULL,
                tx_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS training_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL,
                dataset_ids TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                description TEXT DEFAULT '',
                code_file_id INTEGER NOT NULL REFERENCES files(id),
                config_file_id INTEGER NOT NULL REFERENCES files(id),
                code_hash TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                status TEXT DEFAULT 'registered',
                tx_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS training_rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                training_task_id INTEGER NOT NULL REFERENCES training_tasks(id),
                round_index INTEGER NOT NULL,
                organization TEXT NOT NULL,
                local_epochs INTEGER DEFAULT 1,
                sample_count INTEGER DEFAULT 0,
                gradient_hash TEXT NOT NULL,
                checkpoint_uri TEXT DEFAULT '',
                privacy_method TEXT DEFAULT 'hash-only',
                tx_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS model_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                training_task_id INTEGER NOT NULL REFERENCES training_tasks(id),
                name TEXT NOT NULL,
                model_file_id INTEGER NOT NULL REFERENCES files(id),
                metrics TEXT DEFAULT '{}',
                model_hash TEXT NOT NULL,
                tx_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS audit_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                model_version_id INTEGER NOT NULL REFERENCES model_versions(id),
                result TEXT NOT NULL,
                reason TEXT NOT NULL,
                checks TEXT NOT NULL,
                tx_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(organizations)").fetchall()}
        if "contact" not in columns:
            conn.execute("ALTER TABLE organizations ADD COLUMN contact TEXT DEFAULT ''")
