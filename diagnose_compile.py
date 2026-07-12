"""
diagnose_compile.py
Run this to see exactly why a compiled report isn't being generated for a
specific company + date. Shows every run's status, every file's individual
result, what the compiler's own query considers eligible, and then attempts
the actual compile so any real error surfaces with a full traceback instead
of being swallowed by the GUI's generic "Error: ..." log line.

Usage:
    python diagnose_compile.py <COMPANY_CODE> <YYYY-MM-DD>

Example:
    python diagnose_compile.py 733 2026-07-12

Run this from inside your code folder (same place as ofac_main.py), with
the same Python environment (venv) you use to run the app.
"""

import sys
import os
import traceback

import ofac_database as db
import ofac_settings
from ofac_constants import company_output_folder


def main():
    if len(sys.argv) != 3:
        print("Usage: python diagnose_compile.py <COMPANY_CODE> <YYYY-MM-DD>")
        sys.exit(1)

    company_code = sys.argv[1]
    email_received_date = sys.argv[2]
    date_display = email_received_date.replace("-", "")

    print(f"=== Diagnosing compile for {company_code!r} / {email_received_date!r} ===\n")

    print("--- 1. All runs recorded for this exact company+date ---")
    with db.get_connection() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM runs WHERE company_code = ? AND email_received_date = ? ORDER BY started_at",
            (company_code, email_received_date),
        ).fetchall()]

    if not rows:
        print("  NO RUNS FOUND for this exact company_code + date combination.")
        print("  Double-check: company code is case-sensitive, date must be YYYY-MM-DD.")
        print("  (If you're not sure what's actually in the database, run list_recent_runs.py instead.)")
    for r in rows:
        print(f"  run_id={r['run_id']}  status={r['status']}  started={r['started_at']}  "
              f"finished={r['finished_at']}  processed={r['files_processed']}  failed={r['files_failed']}")

    print("\n--- 2. Every file_logs row for those runs ---")
    run_ids = [r["run_id"] for r in rows]
    file_rows = []
    if run_ids:
        with db.get_connection() as conn:
            placeholders = ",".join("?" * len(run_ids))
            file_rows = [dict(r) for r in conn.execute(
                f"SELECT * FROM file_logs WHERE run_id IN ({placeholders}) ORDER BY log_id",
                run_ids,
            ).fetchall()]

    if not file_rows:
        print("  No file_logs rows at all for these runs.")
    for fr in file_rows:
        path = fr.get("output_csv_path")
        exists = os.path.exists(path) if path else False
        print(f"  run_id={fr['run_id']}  file={fr['file_name']}  sheet={fr['sheet_name']!r}")
        print(f"      output_csv_path={path!r}  (exists on disk right now: {exists})")
        print(f"      output_row_count={fr['output_row_count']}  error_msg={fr['error_msg']!r}")

    print("\n--- 3. What the compiler's own query considers eligible ---")
    compilable = db.get_compilable_file_logs_for_company_date(company_code, email_received_date)
    print(f"  {len(compilable)} file_log row(s) currently eligible to compile.")
    for c in compilable:
        path = c.get("output_csv_path")
        exists = os.path.exists(path) if path else False
        print(f"    {c['file_name']} -> {path}  (exists: {exists})")
    if not compilable:
        print("  This is why nothing compiles: the compiler found zero eligible rows.")
        print("  Compare against section 2 above -- look for rows where output_csv_path is set")
        print("  but they're still not showing up here, or where output_csv_path is None/empty")
        print("  (meaning that file never actually produced output in the first place).")

    print("\n--- 4. Attempting the real compile now, to surface any actual exception ---")
    try:
        import ofac_compiler as compiler
        output_root = ofac_settings.get_output_root()
        output_folder = company_output_folder(date_display, company_code, output_root=output_root)
        compiled_folder = os.path.join(output_folder, "Compiled")
        print(f"  Compiling into: {compiled_folder}")
        result = compiler.compile_company_date(company_code, email_received_date, date_display, compiled_folder)
        print(f"  Compile finished without raising an exception.")
        print(f"  Result: {result}")
        if result["total_rows"] == 0:
            print("  total_rows is 0 -- nothing was compiled, but no error was raised either.")
            print("  This matches section 3 above finding zero eligible rows.")
    except Exception:
        print("  *** COMPILE RAISED AN EXCEPTION -- this is the real error: ***\n")
        traceback.print_exc()

    print("\n=== End of diagnosis ===")


if __name__ == "__main__":
    main()
