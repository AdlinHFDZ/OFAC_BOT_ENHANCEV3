"""
ofac_watcher.py
Watches the input folder for configuration_*.json files (written by the
GUI's "Queue for Watcher" button) and, for each one, spawns a scan: resolve
that company's headers and passwords, run the scan, compile the cumulative
report, export a per-run log, and clean up.

Concurrency: db.try_start_run() is the actual safety mechanism (see
ofac_database.py's docstring) -- this module's job is just to retry with a
backoff if it's told another run for the same company+date is already in
progress, rather than failing outright. The config file is only deleted
after everything succeeds; a crash or a still-blocked lock leaves it in
place so nothing is silently lost.

TEST COVERAGE NOTE: the watchdog Observer/file-system-event part isn't
practical to unit test in this environment (or most environments) --
that's normal, not a gap specific to this build. What's fully testable
without polars is process_config_and_scan's retry/backoff logic and its
config-validation logic, both covered in test_watcher.py. The scan/compile
steps it calls into are already tested in their own modules.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime

from ofac_constants import ensure_app_folders, HEADERS_COMPANIES_FOLDER
import ofac_database as db
import ofac_header_config as header_config
import ofac_settings

CONFIG_FILE_PREFIX = "configuration"
MAX_LOCK_RETRIES = 5
LOCK_RETRY_DELAY_SECONDS = 30


def is_config_file(path):
    name = os.path.basename(path)
    return name.startswith(CONFIG_FILE_PREFIX) and name.endswith(".json")


def validate_config(config):
    """
    Returns a list of problems (empty list means valid). Checked before any
    work starts, so a malformed config fails loudly and specifically rather
    than crashing partway through a scan.
    """
    problems = []
    required_fields = ["company_code", "email_received_date", "files", "passwords"]
    for field in required_fields:
        if field not in config:
            problems.append(f"missing required field: {field}")

    if "files" in config and not isinstance(config["files"], list):
        problems.append("'files' must be a list")
    if "files" in config and isinstance(config["files"], list) and not config["files"]:
        problems.append("'files' is empty -- nothing to process")
    if "passwords" in config and not isinstance(config["passwords"], list):
        problems.append("'passwords' must be a list")

    if "email_received_date" in config:
        try:
            datetime.strptime(config["email_received_date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            problems.append("'email_received_date' must be YYYY-MM-DD")

    return problems


def resolve_passwords(company_code, passwords):
    """
    The config file now stores the actual selected password values
    directly (the vault is unencrypted, so there's no separate label to
    resolve anymore -- see ofac_password_vault.py's docstring for why).
    This just wraps each into a (label, password) tuple for
    ofac_password_retry, which is still shaped that way for its own
    logging purposes; label and password are simply the same value here.
    company_code is accepted for API-compatibility with callers but isn't
    needed for this anymore.
    """
    return [(pwd, pwd) for pwd in passwords]


def try_acquire_run_with_retry(company_code, email_received_date, triggered_by, triggered_user,
                                output_folder, total_files, max_retries=MAX_LOCK_RETRIES,
                                retry_delay=LOCK_RETRY_DELAY_SECONDS, sleep_fn=time.sleep):
    """
    Wraps db.try_start_run with retry/backoff for the case where another run
    for the same company+date is already in progress. Returns the run_id, or
    None if still blocked after max_retries (caller should leave the config
    file in place rather than delete it, so this can be picked up again).
    """
    for attempt in range(max_retries):
        run_id = db.try_start_run(company_code, email_received_date, triggered_by,
                                   triggered_user, output_folder, total_files)
        if run_id is not None:
            return run_id
        if attempt < max_retries - 1:
            sleep_fn(retry_delay)
    return None


def process_config_and_scan(config_path, progress_callback=None):
    """
    Full pipeline for one config file: validate -> acquire run lock (with
    retry) -> resolve headers/passwords -> scan -> compile -> export log ->
    delete config on success.
    """
    if not os.path.exists(config_path):
        return {"status": "error", "message": f"Config file not found: {config_path}"}

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    problems = validate_config(config)
    if problems:
        return {"status": "error", "message": f"Invalid config: {'; '.join(problems)}"}

    company_code = config["company_code"]
    email_received_date = config["email_received_date"]  # YYYY-MM-DD
    date_display = email_received_date.replace("-", "")
    files = config["files"]
    input_folder = config.get("input_folder") or os.path.dirname(config_path)
    triggered_user = config.get("user", "unknown")

    from ofac_constants import company_output_folder
    output_folder = company_output_folder(date_display, company_code, output_root=ofac_settings.get_output_root())
    csv_folder = os.path.join(output_folder, "CSVs")
    archived_folder = os.path.join(output_folder, "Archived")
    unzipped_folder = os.path.join(output_folder, "Unzipped")
    compiled_folder = os.path.join(output_folder, "Compiled")
    for d in [csv_folder, archived_folder, unzipped_folder, compiled_folder]:
        os.makedirs(d, exist_ok=True)

    run_id = try_acquire_run_with_retry(
        company_code, email_received_date, "watcher", triggered_user, output_folder, len(files)
    )
    if run_id is None:
        return {
            "status": "deferred",
            "message": f"Another run for {company_code}/{email_received_date} is still in progress "
                       f"after {MAX_LOCK_RETRIES} retries -- config left in place for later retry.",
        }

    try:
        header_sets = header_config.load_company_headers(company_code)
        password_entries = resolve_passwords(company_code, config["passwords"])

        import ofac_scanner_engine as scanner
        job = scanner.ScanJob(
            run_id=run_id, company_code=company_code, csv_folder=csv_folder,
            archived_folder=archived_folder, unzipped_folder=unzipped_folder,
            passwords=password_entries,
        )
        file_paths = [os.path.join(input_folder, f) for f in files if os.path.exists(os.path.join(input_folder, f))]
        files_processed, files_failed = scanner.run_scan_job(job, file_paths, header_sets, password_entries, progress_callback)

        db.finish_run(run_id, db.RUN_STATUS_COMPLETED if files_failed == 0 else db.RUN_STATUS_FAILED,
                       files_processed=files_processed, files_failed=files_failed)

        import ofac_compiler as compiler
        compile_result = compiler.compile_company_date(company_code, email_received_date, date_display, compiled_folder)

        log_export_path = _export_run_log(run_id, output_folder, date_display, company_code)

        os.remove(config_path)

        return {
            "status": "completed",
            "run_id": run_id,
            "files_processed": files_processed,
            "files_failed": files_failed,
            "compiled_report": compile_result,
            "run_log": log_export_path,
        }

    except Exception as e:
        db.finish_run(run_id, db.RUN_STATUS_FAILED, files_processed=0, files_failed=len(files))
        return {"status": "error", "message": str(e), "run_id": run_id}


def _export_run_log(run_id, output_folder, date_display, company_code):
    """Per-run log export, written once at the end -- see schema doc for why
    this is Excel, atomic, and named with run_id."""
    import polars as pl
    from ofac_file_utils import get_unique_save_path

    logs = db.get_file_logs_for_run(run_id)
    out_path = os.path.join(output_folder, f"Log_{date_display}_{company_code}_run{run_id}.xlsx")
    out_path = get_unique_save_path(out_path)

    if not logs:
        pl.DataFrame().write_excel(out_path)
    else:
        df = pl.DataFrame(logs)
        tmp_path = out_path + ".tmp"
        df.write_excel(tmp_path)
        os.replace(tmp_path, out_path)

    db.write_run_log_record(run_id, out_path, "xlsx")
    return out_path


# ==================== FOLDER WATCHER ====================

def start_watching(watch_folder, script_path=None):
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    ensure_app_folders()
    db.init_database()
    script_path = script_path or os.path.abspath(sys.argv[0])

    class ConfigHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory or not is_config_file(event.src_path):
                return
            print(f"[watcher] Detected config: {event.src_path}")
            try:
                subprocess.Popen(
                    [sys.executable, script_path, "--process-config", event.src_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                print(f"[watcher] Failed to spawn scan process: {e}")

    if not os.path.isdir(watch_folder):
        print(f"[watcher] Invalid watch folder: {watch_folder}")
        return

    observer = Observer()
    observer.schedule(ConfigHandler(), watch_folder, recursive=False)
    observer.start()
    print(f"[watcher] Watching {watch_folder} for {CONFIG_FILE_PREFIX}*.json files...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
