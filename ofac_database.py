"""
ofac_database.py
All SQLite access for the OFAC Scanner: schema creation, run tracking,
per-file/per-sheet logging, per-run log export records, and cumulative
compiled-output tracking.

This replaces the old Log_<date>.csv files entirely. WAL mode is enabled so
multiple scanner processes (spawned by the watcher, one per config file) can
read and write concurrently without corrupting each other.

Concurrency note: try_start_run() is the one function that must be race-safe
across processes -- it's what stops two scans for the same company+date from
running at once (the original bug). It uses an explicit BEGIN IMMEDIATE
transaction rather than a plain SELECT-then-INSERT, because SQLite does not
start a transaction before a bare SELECT: two processes could otherwise both
see "no run in progress" and both insert one. BEGIN IMMEDIATE grabs SQLite's
write lock up front, so the second process's SELECT genuinely waits behind
the first process's INSERT+COMMIT instead of racing it.
"""

import sqlite3
import os
import traceback
from datetime import datetime
from contextlib import contextmanager

from ofac_constants import DATABASE_PATH, DATA_FOLDER

RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_STOPPED = "stopped"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_code TEXT NOT NULL,
    email_received_date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    triggered_by TEXT,
    triggered_user TEXT,
    output_folder TEXT,
    total_files INTEGER,
    files_processed INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS file_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(run_id),
    file_path TEXT,
    file_name TEXT,
    extension TEXT,
    password_matched INTEGER,
    password_label TEXT,
    sheet_name TEXT,
    table_index INTEGER,
    error_msg TEXT,
    identified_headers TEXT,
    multiple_name INTEGER,
    row_count INTEGER,
    output_row_count INTEGER,
    output_csv_path TEXT,
    first_last_name_header TEXT,
    full_name_header TEXT,
    policy_number_header TEXT,
    dob_header TEXT,
    sex_header TEXT,
    remarks TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS run_logs (
    run_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(run_id),
    output_path TEXT,
    format TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS compiled_outputs (
    compiled_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_code TEXT NOT NULL,
    email_received_date TEXT NOT NULL,
    output_path TEXT,
    row_count INTEGER,
    part_number INTEGER,
    last_updated_at TEXT,
    source_run_count INTEGER,
    UNIQUE(company_code, email_received_date, part_number)
);

CREATE INDEX IF NOT EXISTS idx_runs_company_date ON runs(company_code, email_received_date);
CREATE INDEX IF NOT EXISTS idx_file_logs_run ON file_logs(run_id);
"""


def init_database(db_path=DATABASE_PATH):
    """Create the database file and all tables/indexes if they don't already exist."""
    os.makedirs(DATA_FOLDER, exist_ok=True)
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_connection(db_path=DATABASE_PATH):
    """
    Yield a SQLite connection in autocommit mode with WAL enabled. Autocommit
    (isolation_level=None) means we control transactions explicitly wherever
    it matters (see try_start_run) instead of relying on sqlite3's implicit
    transaction handling, which does not protect plain SELECTs.
    """
    conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ==================== RUN LIFECYCLE ====================

def try_start_run(company_code, email_received_date, triggered_by, triggered_user,
                   output_folder, total_files, db_path=DATABASE_PATH):
    """
    Attempt to start a new run for this company+date. Returns the new run_id
    on success, or None if a run for the same company+date is already
    in-progress -- the caller should queue/wait rather than proceed.
    """
    with get_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            existing = conn.execute(
                "SELECT run_id FROM runs WHERE company_code = ? AND email_received_date = ? AND status = ?",
                (company_code, email_received_date, RUN_STATUS_RUNNING),
            ).fetchone()

            if existing is not None:
                conn.execute("ROLLBACK")
                return None

            cur = conn.execute(
                """INSERT INTO runs
                   (company_code, email_received_date, started_at, status,
                    triggered_by, triggered_user, output_folder, total_files)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (company_code, email_received_date, _now(), RUN_STATUS_RUNNING,
                 triggered_by, triggered_user, output_folder, total_files),
            )
            conn.execute("COMMIT")
            return cur.lastrowid
        except Exception:
            conn.execute("ROLLBACK")
            raise


def finish_run(run_id, status, files_processed, files_failed, db_path=DATABASE_PATH):
    with get_connection(db_path) as conn:
        conn.execute(
            """UPDATE runs
               SET status = ?, finished_at = ?, files_processed = ?, files_failed = ?
               WHERE run_id = ?""",
            (status, _now(), files_processed, files_failed, run_id),
        )


# ==================== FILE-LEVEL LOGGING ====================

FILE_LOG_FIELDS = [
    "file_path", "file_name", "extension", "password_matched", "password_label",
    "sheet_name", "table_index", "error_msg", "identified_headers", "multiple_name",
    "row_count", "output_row_count", "output_csv_path", "first_last_name_header",
    "full_name_header", "policy_number_header", "dob_header", "sex_header", "remarks",
]


def write_file_log(run_id, db_path=DATABASE_PATH, **fields):
    """
    Write one row per file/sheet processed. Pass only the fields you have --
    everything else defaults to NULL. Never pass a raw password here: use
    password_matched (bool) and password_label (a masked value, e.g.
    "R**********A" -- see ofac_password_vault.mask_password) instead, so
    the database never holds a usable plaintext secret.
    """
    unknown = set(fields) - set(FILE_LOG_FIELDS)
    if unknown:
        raise ValueError(f"write_file_log got unknown field(s): {unknown}")

    row = {k: fields.get(k) for k in FILE_LOG_FIELDS}
    columns = ", ".join(["run_id", "created_at"] + FILE_LOG_FIELDS)
    placeholders = ", ".join(["?"] * (2 + len(FILE_LOG_FIELDS)))
    values = [run_id, _now()] + [row[k] for k in FILE_LOG_FIELDS]

    with get_connection(db_path) as conn:
        conn.execute(f"INSERT INTO file_logs ({columns}) VALUES ({placeholders})", values)


def log_error(run_id, file_path, file_name, exception, sheet_name=None, remarks=None, db_path=DATABASE_PATH):
    """Convenience wrapper for logging a failed file/sheet with exception details."""
    tb = traceback.format_exc()
    combined_remarks = f"{remarks or ''} | {tb[-2000:]}".strip(" |")
    write_file_log(
        run_id,
        db_path=db_path,
        file_path=file_path,
        file_name=file_name,
        sheet_name=sheet_name,
        error_msg=f"{type(exception).__name__}: {exception}",
        remarks=combined_remarks,
    )


# ==================== HISTORY / QUERIES ====================

def get_recent_runs(limit=200, db_path=DATABASE_PATH):
    with get_connection(db_path) as conn:
        cur = conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]


def get_file_logs_for_run(run_id, db_path=DATABASE_PATH):
    with get_connection(db_path) as conn:
        cur = conn.execute("SELECT * FROM file_logs WHERE run_id = ? ORDER BY log_id", (run_id,))
        return [dict(row) for row in cur.fetchall()]


def get_compilable_file_logs_for_company_date(company_code, email_received_date, db_path=DATABASE_PATH):
    """
    Every file_logs row with a valid output CSV, from any run for this
    company+date that has actually finished (any terminal status) -- NOT
    just runs where every single file succeeded.

    This was a real bug, not a deliberate design choice: the previous
    version only pulled from runs with status='completed', but a run's
    overall status flips to 'failed' the moment even ONE file in a large
    batch errors out -- even if 49 of 50 files processed perfectly. Since
    the compiler only pulled from 'completed' runs, a single bad file in a
    big batch silently excluded every successfully-processed file in that
    same run from the compiled report, with no error shown -- exactly the
    symptom of "individual files look right but there's no compiled output".

    A file_logs row's own output_csv_path is what actually proves that file
    succeeded (log_error() never sets it) -- that's the correct signal to
    compile on, completely independent of how the rest of the batch did.
    Only 'running' (still in progress) is excluded, since those files might
    not be fully written yet.
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """SELECT fl.* FROM file_logs fl
               JOIN runs r ON fl.run_id = r.run_id
               WHERE r.company_code = ? AND r.email_received_date = ?
                 AND r.status != ?
                 AND fl.output_csv_path IS NOT NULL""",
            (company_code, email_received_date, RUN_STATUS_RUNNING),
        )
        return [dict(row) for row in cur.fetchall()]


def count_compilable_runs_for_company_date(company_code, email_received_date, db_path=DATABASE_PATH):
    """Companion to get_compilable_file_logs_for_company_date -- same status
    inclusion rule, used for the compiled_outputs.source_run_count stat."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "SELECT COUNT(*) AS n FROM runs WHERE company_code = ? AND email_received_date = ? AND status != ?",
            (company_code, email_received_date, RUN_STATUS_RUNNING),
        )
        return cur.fetchone()["n"]


# ==================== PER-RUN LOG EXPORT ====================

def write_run_log_record(run_id, output_path, fmt, db_path=DATABASE_PATH):
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO run_logs (run_id, output_path, format, created_at) VALUES (?, ?, ?, ?)",
            (run_id, output_path, fmt, _now()),
        )


# ==================== COMPILED OUTPUT TRACKING ====================

def upsert_compiled_output(company_code, email_received_date, output_path,
                            row_count, part_number, source_run_count, db_path=DATABASE_PATH):
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO compiled_outputs
               (company_code, email_received_date, output_path, row_count,
                part_number, last_updated_at, source_run_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(company_code, email_received_date, part_number)
               DO UPDATE SET output_path=excluded.output_path,
                              row_count=excluded.row_count,
                              last_updated_at=excluded.last_updated_at,
                              source_run_count=excluded.source_run_count""",
            (company_code, email_received_date, output_path, row_count,
             part_number, _now(), source_run_count),
        )


def delete_compiled_outputs_beyond(company_code, email_received_date, max_part_number, db_path=DATABASE_PATH):
    """
    Remove tracking rows for compiled-output parts that no longer exist after
    a rebuild shrinks the part count (e.g. a correction reduced total rows
    below a split boundary). Returns the stale file paths so the caller can
    delete the actual files too.
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """SELECT output_path FROM compiled_outputs
               WHERE company_code = ? AND email_received_date = ? AND part_number > ?""",
            (company_code, email_received_date, max_part_number),
        )
        stale_paths = [row["output_path"] for row in cur.fetchall()]
        conn.execute(
            """DELETE FROM compiled_outputs
               WHERE company_code = ? AND email_received_date = ? AND part_number > ?""",
            (company_code, email_received_date, max_part_number),
        )
        return stale_paths
