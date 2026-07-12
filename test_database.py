"""
Quick verification script for ofac_database.py — not part of the shipped app,
just proving the concurrency lock actually works before trusting it.
"""
import os
import sys
import tempfile
import multiprocessing

sys.path.insert(0, os.path.dirname(__file__))
os.environ["OFAC_APP_ROOT"] = os.path.join(tempfile.gettempdir(), "ofac_database_test_root")

import ofac_database as db
from ofac_constants import DATABASE_PATH, DATA_FOLDER


def worker_try_start(db_path, results_queue, worker_id):
    run_id = db.try_start_run(
        company_code="COMPANY_A",
        email_received_date="2026-07-11",
        triggered_by="test",
        triggered_user=f"worker_{worker_id}",
        output_folder="test_output_folder",
        total_files=3,
    )
    results_queue.put((worker_id, run_id))


def main():
    os.makedirs(DATA_FOLDER, exist_ok=True)
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
    db.init_database()

    print("TEST 1: Basic run lifecycle")
    run_id = db.try_start_run("COMPANY_A", "2026-07-11", "manual", "tester", "test_output_folder", 5)
    assert run_id is not None, "Expected a run_id on first start"
    print(f"  Started run_id={run_id}")

    second_attempt = db.try_start_run("COMPANY_A", "2026-07-11", "manual", "tester2", "test_output_folder", 5)
    assert second_attempt is None, "Expected None when a run is already in progress for same company+date"
    print("  Second concurrent attempt correctly blocked (returned None)")

    diff_company = db.try_start_run("COMPANY_B", "2026-07-11", "manual", "tester", "test_output_folder", 5)
    assert diff_company is not None, "Different company should be allowed to start"
    print(f"  Different company started fine, run_id={diff_company}")

    db.finish_run(run_id, db.RUN_STATUS_COMPLETED, files_processed=5, files_failed=0)
    reopened = db.try_start_run("COMPANY_A", "2026-07-11", "manual", "tester3", "test_output_folder", 5)
    assert reopened is not None, "Should be able to start again after the prior run completed"
    print(f"  Re-run after completion allowed, run_id={reopened}")
    db.finish_run(reopened, db.RUN_STATUS_COMPLETED, files_processed=5, files_failed=0)
    db.finish_run(diff_company, db.RUN_STATUS_COMPLETED, files_processed=5, files_failed=0)

    print("\nTEST 2: File-level logging + queries")
    run_id = db.try_start_run("COMPANY_C", "2026-07-12", "manual", "tester", "test_output_folder", 2)
    db.write_file_log(run_id, file_path="/in/a.xlsx", file_name="a.xlsx", extension="xlsx",
                       password_matched=True, password_label="R**********A",
                       sheet_name="Sheet1", row_count=100, output_row_count=98,
                       output_csv_path="/out/a_part1.csv")
    try:
        db.log_error(run_id, "/in/b.xlsx", "b.xlsx", ValueError("bad header"), sheet_name="Sheet1")
    except Exception:
        pass
    db.finish_run(run_id, db.RUN_STATUS_COMPLETED, files_processed=2, files_failed=1)
    logs = db.get_file_logs_for_run(run_id)
    assert len(logs) == 2, f"Expected 2 file_log rows, got {len(logs)}"
    assert logs[1]["error_msg"].startswith("ValueError"), "Error row should record exception type"
    print(f"  Wrote and read back {len(logs)} file_log rows correctly")

    print("\nTEST 4: compiled_outputs tracking (upsert + stale-part cleanup)")
    db.upsert_compiled_output("COMPANY_D", "2026-07-11", "/out/report_1.xlsx", row_count=500000, part_number=1, source_run_count=1)
    db.upsert_compiled_output("COMPANY_D", "2026-07-11", "/out/report_2.xlsx", row_count=300000, part_number=2, source_run_count=1)
    # Re-upsert part 1 with updated stats (simulates a second run adding more rows to the same part)
    db.upsert_compiled_output("COMPANY_D", "2026-07-11", "/out/report_1.xlsx", row_count=600000, part_number=1, source_run_count=2)

    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM compiled_outputs WHERE company_code = ? AND email_received_date = ? ORDER BY part_number",
            ("COMPANY_D", "2026-07-11"),
        ).fetchall()
    assert len(rows) == 2, f"Expected 2 tracked parts, got {len(rows)}"
    assert rows[0]["row_count"] == 600000, "Upsert should update row_count on conflict, not duplicate the row"
    assert rows[0]["source_run_count"] == 2
    print(f"  Upsert-on-conflict works correctly: part 1 updated in place, part 2 unchanged")

    # Simulate a rebuild that shrinks back down to 1 part -- part 2 should be reported stale and removed
    stale = db.delete_compiled_outputs_beyond("COMPANY_D", "2026-07-11", max_part_number=1)
    assert stale == ["/out/report_2.xlsx"], f"Expected part 2 flagged stale, got {stale}"
    with db.get_connection() as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) as n FROM compiled_outputs WHERE company_code = ? AND email_received_date = ?",
            ("COMPANY_D", "2026-07-11"),
        ).fetchone()["n"]
    assert remaining == 1, f"Expected 1 tracked part remaining after cleanup, got {remaining}"
    print(f"  Stale-part detection and cleanup works correctly")

    print("\nTEST 5: REAL concurrency — 20 processes racing for the same company+date")
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
    db.init_database()

    ctx = multiprocessing.get_context("spawn")
    results_queue = ctx.Queue()
    procs = [
        ctx.Process(target=worker_try_start, args=(DATABASE_PATH, results_queue, i))
        for i in range(20)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    results = []
    while not results_queue.empty():
        results.append(results_queue.get())

    successes = [r for r in results if r[1] is not None]
    blocked = [r for r in results if r[1] is None]
    print(f"  {len(successes)} succeeded, {len(blocked)} correctly blocked (out of {len(results)} total attempts)")
    assert len(successes) == 1, f"Expected exactly 1 success under real concurrency, got {len(successes)}: {successes}"
    assert len(blocked) == 19, f"Expected 19 blocked, got {len(blocked)}"

    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
