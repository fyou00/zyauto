"""Akses SQLite (sqlite3 bawaan). Tabel: jobs."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id            TEXT PRIMARY KEY,
  original_name TEXT NOT NULL,
  ext           TEXT NOT NULL CHECK (ext IN ('mp4','mov','mkv')),
  input_path    TEXT NOT NULL,
  output_path   TEXT,
  size_bytes    INTEGER NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('queued','processing','done','failed')),
  attempts      INTEGER NOT NULL DEFAULT 0,
  error         TEXT,
  created_at    TEXT NOT NULL,
  started_at    TEXT,
  finished_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db():
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def list_jobs(limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def create_job(job_id, original_name, ext, input_path, size_bytes):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO jobs (id, original_name, ext, input_path, size_bytes, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'queued', ?)",
            (job_id, original_name, ext, str(input_path), size_bytes, now_iso()),
        )
