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
  finished_at   TEXT,
  service       TEXT NOT NULL DEFAULT 'topaz_only' CHECK (service IN ('topaz_only','topaz_cc')),
  cc_preset     TEXT,
  stage         TEXT CHECK (stage IS NULL OR stage IN ('topaz','ae','encoding')),
  intermediate_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);
"""

# Migrasi untuk DB lama: kolom ditambah jika belum ada. Baris lama jadi service='topaz_only'.
MIGRATIONS = [
    ("service", "TEXT NOT NULL DEFAULT 'topaz_only' CHECK (service IN ('topaz_only','topaz_cc'))"),
    ("cc_preset", "TEXT"),
    ("stage", "TEXT CHECK (stage IS NULL OR stage IN ('topaz','ae','encoding'))"),
    ("intermediate_path", "TEXT"),
]


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
    config.INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
        for name, definition in MIGRATIONS:
            if name not in existing:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")


def list_jobs(limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def claim_next_job():
    """Ambil satu job queued (tertua) dan ubah jadi processing secara atomic."""
    conn = sqlite3.connect(config.DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if row is None:
            conn.execute("COMMIT")
            return None
        cur = conn.execute(
            "UPDATE jobs SET status = 'processing', attempts = attempts + 1, started_at = ? "
            "WHERE id = ? AND status = 'queued'",
            (now_iso(), row["id"]),
        )
        if cur.rowcount != 1:
            conn.execute("ROLLBACK")
            return None
        conn.execute("COMMIT")
        job = dict(row)
        job["attempts"] += 1
        return job
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def reset_processing_jobs():
    """Dipanggil saat worker start: job yang tertinggal 'processing' (worker mati) dikembalikan.

    attempts < MAX_ATTEMPTS -> queued lagi; sudah habis percobaannya -> failed.
    """
    with get_conn() as conn:
        requeued = conn.execute(
            "UPDATE jobs SET status = 'queued', started_at = NULL "
            "WHERE status = 'processing' AND attempts < ?",
            (config.MAX_ATTEMPTS,),
        ).rowcount
        failed = conn.execute(
            "UPDATE jobs SET status = 'failed', error = ?, finished_at = ? "
            "WHERE status = 'processing' AND attempts >= ?",
            ("gagal setelah percobaan maksimal (worker terhenti)", now_iso(), config.MAX_ATTEMPTS),
        ).rowcount
        return requeued, failed


def mark_done(job_id, output_path):
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'done', output_path = ?, finished_at = ?, error = NULL WHERE id = ?",
            (str(output_path), now_iso(), job_id),
        )


def mark_failed(job_id, error):
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'failed', error = ?, finished_at = ? WHERE id = ?",
            (error, now_iso(), job_id),
        )


def get_job(job_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def set_stage(job_id, stage):
    """stage: 'topaz' | 'ae' | 'encoding' | None."""
    with get_conn() as conn:
        conn.execute("UPDATE jobs SET stage = ? WHERE id = ?", (stage, job_id))


def set_intermediate_path(job_id, path):
    """path: file perantara, atau None setelah dihapus."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET intermediate_path = ? WHERE id = ?",
            (str(path) if path is not None else None, job_id),
        )


def create_job(job_id, original_name, ext, input_path, size_bytes,
               service="topaz_only", cc_preset=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO jobs (id, original_name, ext, input_path, size_bytes, status, created_at, "
            "service, cc_preset) VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?)",
            (job_id, original_name, ext, str(input_path), size_bytes, now_iso(), service, cc_preset),
        )
