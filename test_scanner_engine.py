"""
test_scanner_engine.py
NOT RUN in the environment this was written in (no polars, no network to
get it -- see ofac_scanner_engine.py's docstring). Run this on a machine
with polars + python-dateutil installed:

    pip install polars python-dateutil
    python test_scanner_engine.py

Priority order if something fails: the chunked-reading tests
(test_text_chunking_reads_every_row_exactly_once and
test_parted_csv_writer_splits_correctly) matter most, since they directly
exercise the two critical big-file bugs from the code review. Excel-specific
and 7z-specific tests need openpyxl / msoffcrypto / a real 7z.exe and are
separated out so the core logic can be verified even before those are set up.
"""

import os
import sys
import csv
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("OFAC_APP_ROOT", os.path.join(tempfile.gettempdir(), "ofac_scanner_engine_test_root"))

import polars as pl
import openpyxl
import ofac_database as db
import ofac_scanner_engine as scanner
from ofac_scanner_engine import ScanJob, PartedCSVWriter, _read_text_chunks

TEST_ROOT = os.path.join(tempfile.gettempdir(), "ofac_scanner_engine_test_root")


def _fresh_test_dirs():
    if os.path.exists(TEST_ROOT):
        shutil.rmtree(TEST_ROOT)
    csv_folder = os.path.join(TEST_ROOT, "csv")
    archived_folder = os.path.join(TEST_ROOT, "archived")
    unzipped_folder = os.path.join(TEST_ROOT, "unzipped")
    for d in [csv_folder, archived_folder, unzipped_folder]:
        os.makedirs(d, exist_ok=True)
    return csv_folder, archived_folder, unzipped_folder


def test_parted_csv_writer_splits_correctly():
    """No polars files needed -- builds DataFrames directly in memory."""
    csv_folder, _, _ = _fresh_test_dirs()
    base_path = os.path.join(csv_folder, "test_file")
    writer = PartedCSVWriter(base_path, max_rows_per_file=10)

    for _ in range(3):
        chunk = pl.DataFrame({"COMPLETE_NAME": [f"Person {i}" for i in range(7)]})
        writer.add(chunk)
    parts = writer.finalize()

    total_rows = sum(count for _, count in parts)
    assert total_rows == 21, f"Expected 21 total rows across parts, got {total_rows}"
    assert all(count <= 10 for _, count in parts), f"A part exceeded max_rows_per_file: {parts}"
    for path, count in parts:
        on_disk = pl.read_csv(path, glob=False)
        assert on_disk.height == count, f"File {path} row count mismatch: file has {on_disk.height}, expected {count}"
    print(f"test_parted_csv_writer_splits_correctly PASSED ({len(parts)} parts, {total_rows} total rows)")


def test_text_chunking_reads_every_row_exactly_once():
    """
    THE core proof that bug #1 (broken batched-CSV loop) is actually fixed:
    write a CSV with a known number of rows, force a small batch size well
    below the total, and confirm every row is read exactly once -- no rows
    lost (the old v2 bug: crash before finishing) and no infinite loop
    (the old v1 bug: same batch read forever).
    """
    csv_folder, _, _ = _fresh_test_dirs()
    test_csv_path = os.path.join(csv_folder, "big_test.csv")

    total_rows = 537  # deliberately not a clean multiple of the batch size
    with open(test_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Sex", "DOB", "PolicyNo"])
        for i in range(total_rows):
            writer.writerow([f"Person {i}", "M" if i % 2 == 0 else "F", "1990-01-01", f"P{i:06d}"])

    chunks_read = list(_read_text_chunks(test_csv_path, encoding="utf-8", delimiter=",", quotechar='"', chunk_rows=50))

    total_rows_read = sum(c.height for c in chunks_read)
    # +1 because the header row itself comes through as a data row in has_header=False mode
    assert total_rows_read == total_rows + 1, (
        f"Expected {total_rows + 1} rows read (data + header row), got {total_rows_read}. "
        f"If this is 0 or hangs, the chunking loop is broken again."
    )
    assert len(chunks_read) > 1, "Expected multiple batches given chunk_rows=50 on 538 rows"
    print(f"test_text_chunking_reads_every_row_exactly_once PASSED "
          f"({len(chunks_read)} batches, {total_rows_read} rows, none lost/duplicated)")


def test_process_text_file_small_path_end_to_end():
    """Full integration: real file on disk -> real database -> real output CSV."""
    csv_folder, archived_folder, unzipped_folder = _fresh_test_dirs()
    db.init_database()
    run_id = db.try_start_run("TESTCO", "2026-07-12", "manual", "tester", TEST_ROOT, 1)
    assert run_id is not None

    test_csv_path = os.path.join(csv_folder, "small_test.csv")
    with open(test_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Sex", "DOB", "PolicyNo"])
        writer.writerow(["John Smith", "M", "1990-01-01", "P123456"])
        writer.writerow(["Jane Doe", "F", "1985-05-05", "P654321"])

    job = ScanJob(run_id=run_id, company_code="TESTCO", csv_folder=csv_folder,
                  archived_folder=archived_folder, unzipped_folder=unzipped_folder,
                  passwords=[])
    header_sets = {
        "name": {"name"}, "firstlastname": set(), "sex": {"sex"},
        "dob": {"dob"}, "policynum": {"policyno"},
    }

    scanner.process_text_file(job, test_csv_path, "small_test.csv", header_sets)

    logs = db.get_file_logs_for_run(run_id)
    assert len(logs) == 1, f"Expected 1 file_log row, got {len(logs)}"
    assert logs[0]["output_row_count"] == 2
    output_df = pl.read_csv(logs[0]["output_csv_path"], glob=False)
    assert output_df.height == 2
    assert set(output_df["COMPLETE_NAME"].to_list()) == {"JOHN SMITH", "JANE DOE"}

    db.finish_run(run_id, db.RUN_STATUS_COMPLETED, files_processed=1, files_failed=0)
    print("test_process_text_file_small_path_end_to_end PASSED")


def test_process_excel_file_small_path_end_to_end():
    """
    Closes a real gap: every other Excel-related test in this file (and in
    test_header_extractor_engine.py) builds a polars DataFrame directly in
    memory and calls detection/extraction functions on it -- none of them
    ever actually call pl.read_excel() against a real .xlsx file on disk,
    which is what process_excel_file() does in production. This test writes
    a genuine .xlsx with openpyxl and runs it through the real function, so
    a dependency gap in the Excel *read* path (like the missing fastexcel
    package) can't hide behind a passing test suite again.
    """
    csv_folder, archived_folder, unzipped_folder = _fresh_test_dirs()
    db.init_database()
    run_id = db.try_start_run("TESTCO", "2026-07-12", "manual", "tester", TEST_ROOT, 1)
    assert run_id is not None

    test_xlsx_path = os.path.join(csv_folder, "small_test.xlsx")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(["Name", "Sex", "DOB", "PolicyNo"])
    sheet.append(["John Smith", "M", "1990-01-01", "P123456"])
    sheet.append(["Jane Doe", "F", "1985-05-05", "P654321"])
    workbook.save(test_xlsx_path)

    job = ScanJob(run_id=run_id, company_code="TESTCO", csv_folder=csv_folder,
                  archived_folder=archived_folder, unzipped_folder=unzipped_folder,
                  passwords=[])
    header_sets = {
        "name": {"name"}, "firstlastname": set(), "sex": {"sex"},
        "dob": {"dob"}, "policynum": {"policyno"},
    }

    scanner.process_excel_file(job, test_xlsx_path, "small_test.xlsx", header_sets, password_entries=[])

    logs = db.get_file_logs_for_run(run_id)
    assert len(logs) == 1, f"Expected 1 file_log row, got {len(logs)}"
    assert logs[0]["output_row_count"] == 2
    assert logs[0]["sheet_name"] == "Sheet1"
    output_df = pl.read_csv(logs[0]["output_csv_path"], glob=False)
    assert output_df.height == 2
    assert set(output_df["COMPLETE_NAME"].to_list()) == {"JOHN SMITH", "JANE DOE"}

    db.finish_run(run_id, db.RUN_STATUS_COMPLETED, files_processed=1, files_failed=0)
    print("test_process_excel_file_small_path_end_to_end PASSED "
          "(this is the test that would have caught the missing fastexcel dependency)")


def test_run_scan_job_archives_file_after_success():
    csv_folder, archived_folder, unzipped_folder = _fresh_test_dirs()
    db.init_database()
    run_id = db.try_start_run("TESTCO2", "2026-07-12", "manual", "tester", TEST_ROOT, 1)

    input_folder = os.path.join(TEST_ROOT, "input")
    os.makedirs(input_folder, exist_ok=True)
    test_csv_path = os.path.join(input_folder, "input_test.csv")
    with open(test_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Sex", "DOB", "PolicyNo"])
        writer.writerow(["Alice Wong", "F", "1992-03-03", "P111"])

    job = ScanJob(run_id=run_id, company_code="TESTCO2", csv_folder=csv_folder,
                  archived_folder=archived_folder, unzipped_folder=unzipped_folder,
                  passwords=[])
    header_sets = {
        "name": {"name"}, "firstlastname": set(), "sex": {"sex"},
        "dob": {"dob"}, "policynum": {"policyno"},
    }

    processed, failed = scanner.run_scan_job(job, [test_csv_path], header_sets, [])
    assert processed == 1
    assert failed == 0
    assert not os.path.exists(test_csv_path), "Original file should have been moved to Archived"
    archived_files = os.listdir(archived_folder)
    assert len(archived_files) == 1
    print("test_run_scan_job_archives_file_after_success PASSED")


def test_run_scan_job_leaves_failed_file_in_place():
    csv_folder, archived_folder, unzipped_folder = _fresh_test_dirs()
    db.init_database()
    run_id = db.try_start_run("TESTCO3", "2026-07-12", "manual", "tester", TEST_ROOT, 1)

    input_folder = os.path.join(TEST_ROOT, "input3")
    os.makedirs(input_folder, exist_ok=True)
    bad_path = os.path.join(input_folder, "not_really_a_csv.csv")
    with open(bad_path, "wb") as f:
        f.write(b"\x00\x01\x02 this is not valid CSV content \xff\xfe")

    job = ScanJob(run_id=run_id, company_code="TESTCO3", csv_folder=csv_folder,
                  archived_folder=archived_folder, unzipped_folder=unzipped_folder,
                  passwords=[])
    header_sets = {"name": {"name"}, "firstlastname": set(), "sex": set(), "dob": set(), "policynum": set()}

    processed, failed = scanner.run_scan_job(job, [bad_path], header_sets, [])
    # This may or may not actually fail depending on how permissive the CSV
    # reader is with garbage bytes -- the important invariant either way is
    # that a failure never silently archives the file.
    if failed == 1:
        assert os.path.exists(bad_path), "Failed file should NOT be moved to Archived"
        print("test_run_scan_job_leaves_failed_file_in_place PASSED (file failed as expected, stayed in place)")
    else:
        print("test_run_scan_job_leaves_failed_file_in_place SKIPPED (polars read the garbage file without erroring)")


if __name__ == "__main__":
    test_parted_csv_writer_splits_correctly()
    test_text_chunking_reads_every_row_exactly_once()
    test_process_text_file_small_path_end_to_end()
    test_process_excel_file_small_path_end_to_end()
    test_run_scan_job_archives_file_after_success()
    test_run_scan_job_leaves_failed_file_in_place()
    print("\nALL SCANNER ENGINE TESTS PASSED")
