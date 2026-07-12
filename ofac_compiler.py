"""
ofac_compiler.py
Rebuilds the cumulative compiled report for a company+date, per the
confirmed design: one stable, atomically-replaced report per company+date
(not one per run), pulling output from every completed run so far for that
company+date.

Dedup is deliberately row-level only (exact duplicate rows collapse; the
same person from two different source files still appears twice, since
FILE_PATH differs) -- this was an explicit, confirmed decision to defer
cross-file identity dedup, not an oversight. See the schema doc for the
reasoning.

TEST COVERAGE NOTE: same situation as the other polars-dependent files --
not runnable here. What IS tested: the "which stale parts need deleting"
logic (pure arithmetic, no polars needed) and the database calls this reads
from (already tested in test_database.py). Run test_compiler.py on a machine
with polars before trusting this in production.
"""

import os

import polars as pl

from ofac_constants import EXCEL_MAX_ROWS, OUTPUT_COLUMNS
from ofac_file_utils import get_unique_save_path
import ofac_database as db

# Every output column is text/identifier data, never meant for arithmetic --
# forcing all of them to Utf8 on read avoids polars' per-file automatic type
# inference disagreeing across different source CSVs. This was found the
# hard way: POLICY_NUMBER needed it (numeric-looking policy numbers), then
# SHEET needed it too (sheet names that are pure numbers, e.g. "2601"), and
# CMPY_NO would have been next (company codes like "733" are pure numbers).
# Overriding every column up front avoids finding the rest one at a time.
_READ_SCHEMA_OVERRIDES = {col: pl.Utf8 for col in OUTPUT_COLUMNS}


def compiled_base_path(compiled_folder, email_received_date_display, company_code):
    return os.path.join(compiled_folder, f"OFAC_ABS_Log_{email_received_date_display}_{company_code}")


def _atomic_write_excel(df, final_path):
    """
    write_excel needs a real path (it writes directly, no bytes buffer to
    hand to atomic_write_bytes), so this does the same temp-then-replace
    pattern at the file level instead.
    """
    tmp_path = final_path + ".tmp"
    df.write_excel(tmp_path)
    os.replace(tmp_path, final_path)


def compile_company_date(company_code, email_received_date, email_received_date_display, compiled_folder):
    """
    Pulls every completed run's output for this company+date, concatenates,
    dedups (row-level), splits at EXCEL_MAX_ROWS, atomically writes each
    part, and updates compiled_outputs tracking -- including removing
    tracking (and files) for any part that no longer exists after a rebuild
    shrinks the total row count.

    Returns a summary dict: {total_rows, part_count, paths, source_run_count, skipped_missing_files}.
    """
    file_logs = db.get_compilable_file_logs_for_company_date(company_code, email_received_date)
    source_run_count = db.count_compilable_runs_for_company_date(company_code, email_received_date)

    frames = []
    skipped_missing_files = []
    for log_row in file_logs:
        csv_path = log_row.get("output_csv_path")
        if not csv_path or not os.path.exists(csv_path):
            skipped_missing_files.append(csv_path)
            continue
        try:
            # glob=False is required, not optional: per-sheet output filenames
            # look like "file.xlsx[Sheet1]_part1_OFAC_OUTPUT.csv" -- polars'
            # read_csv treats square brackets as glob syntax (a character
            # class) by default, so it would silently fail to find a file
            # that's sitting right there on disk. We're always reading one
            # exact, known path here, never an actual wildcard pattern.
            frames.append(pl.read_csv(csv_path, schema_overrides=_READ_SCHEMA_OVERRIDES, glob=False))
        except Exception:
            skipped_missing_files.append(csv_path)

    os.makedirs(compiled_folder, exist_ok=True)
    base_path = compiled_base_path(compiled_folder, email_received_date_display, company_code)

    if not frames:
        return {
            "total_rows": 0, "part_count": 0, "paths": [],
            "source_run_count": source_run_count, "skipped_missing_files": skipped_missing_files,
        }

    combined = pl.concat(frames, how="vertical") if len(frames) > 1 else frames[0]
    combined = combined.unique()  # row-level dedup only -- confirmed decision, see module docstring

    written_paths = []
    part_number = 1
    offset = 0
    total_rows = combined.height

    if total_rows == 0:
        parts_needed = 0
    else:
        while offset < total_rows:
            chunk = combined.slice(offset, EXCEL_MAX_ROWS)
            final_path = f"{base_path}_{part_number}.xlsx"
            _atomic_write_excel(chunk, final_path)
            written_paths.append(final_path)
            db.upsert_compiled_output(
                company_code, email_received_date, final_path,
                row_count=chunk.height, part_number=part_number, source_run_count=source_run_count,
            )
            offset += EXCEL_MAX_ROWS
            part_number += 1
        parts_needed = part_number - 1

    # Clean up parts left over from a previous, larger version of this
    # compile (e.g. a correction reduced the row count below a split point).
    stale_paths = db.delete_compiled_outputs_beyond(company_code, email_received_date, parts_needed)
    for stale_path in stale_paths:
        try:
            if stale_path and os.path.exists(stale_path):
                os.remove(stale_path)
        except OSError:
            pass

    return {
        "total_rows": total_rows,
        "part_count": parts_needed,
        "paths": written_paths,
        "source_run_count": source_run_count,
        "skipped_missing_files": skipped_missing_files,
    }
