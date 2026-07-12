"""
test_compiler.py
NOT RUN here (no polars -- see other test files' docstrings for why). Run on
a machine with polars installed:

    pip install polars
    python test_compiler.py

The database-side logic this depends on (upsert_compiled_output,
delete_compiled_outputs_beyond) IS already tested in test_database.py and
passes there -- these tests focus on what's specific to the compiler:
cumulative pull-from-multiple-runs behavior, row-level dedup, and skipping
missing source files without aborting the whole compile.
"""

import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("OFAC_APP_ROOT", os.path.join(tempfile.gettempdir(), "ofac_compiler_test_root"))

import polars as pl
import ofac_database as db
import ofac_compiler as compiler

TEST_ROOT = os.path.join(tempfile.gettempdir(), "ofac_compiler_test_root")


def _fresh_dirs():
    if os.path.exists(TEST_ROOT):
        shutil.rmtree(TEST_ROOT)
    compiled_folder = os.path.join(TEST_ROOT, "compiled")
    csvs_folder = os.path.join(TEST_ROOT, "csvs")
    os.makedirs(compiled_folder, exist_ok=True)
    os.makedirs(csvs_folder, exist_ok=True)
    return compiled_folder, csvs_folder


def _write_output_csv(csvs_folder, filename, names):
    path = os.path.join(csvs_folder, filename)
    pl.DataFrame({
        "SURNAME": [""] * len(names), "FIRST_NAME": [""] * len(names),
        "COMPLETE_NAME": names, "SEX": ["M"] * len(names),
        "DATE_OF_BIRTH": ["01/01/1990"] * len(names), "CMPY_NO": ["TESTCO"] * len(names),
        "POLICY_NUMBER": [f"P{i}" for i in range(len(names))],
        "FILE_PATH": [filename] * len(names), "SHEET": [""] * len(names),
    }).write_csv(path)
    return path


def test_cumulative_compile_pulls_from_multiple_runs():
    compiled_folder, csvs_folder = _fresh_dirs()
    db.init_database()

    run1 = db.try_start_run("TESTCO", "2026-07-12", "manual", "tester", TEST_ROOT, 1)
    csv1 = _write_output_csv(csvs_folder, "batch1.csv", ["ALICE WONG", "BOB LEE"])
    db.write_file_log(run1, output_csv_path=csv1, output_row_count=2, file_name="batch1.csv")
    db.finish_run(run1, db.RUN_STATUS_COMPLETED, files_processed=1, files_failed=0)

    run2 = db.try_start_run("TESTCO", "2026-07-12", "manual", "tester", TEST_ROOT, 1)
    csv2 = _write_output_csv(csvs_folder, "batch2.csv", ["CAROL TAN"])
    db.write_file_log(run2, output_csv_path=csv2, output_row_count=1, file_name="batch2.csv")
    db.finish_run(run2, db.RUN_STATUS_COMPLETED, files_processed=1, files_failed=0)

    result = compiler.compile_company_date("TESTCO", "2026-07-12", "20260712", compiled_folder)

    assert result["total_rows"] == 3, f"Expected 3 rows pulled from both runs, got {result['total_rows']}"
    assert result["source_run_count"] == 2
    assert result["part_count"] == 1
    assert len(result["paths"]) == 1

    on_disk = pl.read_excel(result["paths"][0])
    assert set(on_disk["COMPLETE_NAME"].to_list()) == {"ALICE WONG", "BOB LEE", "CAROL TAN"}
    print("test_cumulative_compile_pulls_from_multiple_runs PASSED")


def test_compile_includes_successful_files_from_a_failed_run():
    """
    Direct regression test for the real bug this fix addresses: a run's
    overall status flips to 'failed' the moment even one file in the batch
    errors, even if every other file in that same run processed correctly.
    The old version of get_compilable_file_logs_for_company_date only
    pulled from runs with status='completed', which meant a single bad file
    in a large batch silently excluded every successfully-processed file in
    that run from the compiled report -- exactly the "files extracted fine,
    but no compiled output" symptom this was found from on a real 1.2GB scan.

    A file_logs row's own output_csv_path is the correct signal for "did
    this specific file succeed" -- independent of how the rest of the
    batch did. (This replaces the old test_compile_ignores_non_completed_runs,
    which verified the buggy behavior as if it were correct.)
    """
    compiled_folder, csvs_folder = _fresh_dirs()
    db.init_database()

    run1 = db.try_start_run("TESTCO2", "2026-07-12", "manual", "tester", TEST_ROOT, 2)
    good_csv = _write_output_csv(csvs_folder, "good.csv", ["ALICE WONG"])
    db.write_file_log(run1, output_csv_path=good_csv, output_row_count=1, file_name="good.csv")
    # A different file in the SAME run failed -- output_csv_path is None,
    # exactly what log_error() records for a genuinely failed file.
    db.write_file_log(run1, output_csv_path=None, file_name="bad.csv", error_msg="ValueError: simulated failure")
    # The run as a whole gets marked failed because of that one bad file --
    # this is the exact scenario that used to silently lose ALICE WONG's data.
    db.finish_run(run1, db.RUN_STATUS_FAILED, files_processed=1, files_failed=1)

    result = compiler.compile_company_date("TESTCO2", "2026-07-12", "20260712", compiled_folder)
    assert result["total_rows"] == 1, (
        f"Expected the successfully-processed file's data to be compiled despite "
        f"the run overall being marked 'failed', got: {result}"
    )
    on_disk = pl.read_excel(result["paths"][0])
    assert on_disk["COMPLETE_NAME"].to_list() == ["ALICE WONG"]
    print("test_compile_includes_successful_files_from_a_failed_run PASSED "
          "(this is the fix for the real-world missing-compiled-file issue)")


def test_compile_excludes_files_with_no_output_path():
    """
    Companion test: a file that genuinely failed (no output_csv_path at
    all) must never be pulled into the compile, regardless of the run's
    overall status -- only files with a real, valid output path get
    compiled. The fix above widens *which runs* are eligible; it doesn't
    weaken *which files* within them are eligible.
    """
    compiled_folder, csvs_folder = _fresh_dirs()
    db.init_database()

    run1 = db.try_start_run("TESTCO7", "2026-07-12", "manual", "tester", TEST_ROOT, 1)
    db.write_file_log(run1, output_csv_path=None, file_name="totally_failed.csv", error_msg="could not read file")
    db.finish_run(run1, db.RUN_STATUS_FAILED, files_processed=0, files_failed=1)

    result = compiler.compile_company_date("TESTCO7", "2026-07-12", "20260712", compiled_folder)
    assert result["total_rows"] == 0, f"Expected nothing to compile, got: {result}"
    print("test_compile_excludes_files_with_no_output_path PASSED")


def test_row_level_dedup_in_compile():
    """
    The shared _write_output_csv helper assigns a unique POLICY_NUMBER per
    row index (P0, P1, ...) -- correct for the other tests, which need
    distinct people, but wrong here: it meant the two "duplicate" rows
    actually differed on POLICY_NUMBER and were never true duplicates in the
    first place, so .unique() correctly left both and the test's own
    assertion was checking something that hadn't actually been set up. This
    writes a genuinely identical row twice, directly, instead.
    """
    compiled_folder, csvs_folder = _fresh_dirs()
    db.init_database()

    run1 = db.try_start_run("TESTCO3", "2026-07-12", "manual", "tester", TEST_ROOT, 1)
    csv1 = os.path.join(csvs_folder, "dup_test.csv")
    pl.DataFrame({
        "SURNAME": ["", ""], "FIRST_NAME": ["", ""],
        "COMPLETE_NAME": ["ALICE WONG", "ALICE WONG"], "SEX": ["M", "M"],
        "DATE_OF_BIRTH": ["01/01/1990", "01/01/1990"], "CMPY_NO": ["TESTCO3", "TESTCO3"],
        "POLICY_NUMBER": ["P0", "P0"],  # identical on every column this time -- a genuine duplicate
        "FILE_PATH": ["dup_test.csv", "dup_test.csv"], "SHEET": ["", ""],
    }).write_csv(csv1)
    db.write_file_log(run1, output_csv_path=csv1, output_row_count=2, file_name="dup_test.csv")
    db.finish_run(run1, db.RUN_STATUS_COMPLETED, files_processed=1, files_failed=0)

    result = compiler.compile_company_date("TESTCO3", "2026-07-12", "20260712", compiled_folder)
    assert result["total_rows"] == 1, f"Expected exact duplicate row collapsed, got {result['total_rows']}"
    print("test_row_level_dedup_in_compile PASSED")


def test_compile_handles_bracket_containing_filenames():
    """
    Direct regression test for a real production bug: Excel-sourced output
    CSVs are named like "file.xlsx[Sheet1]_part1_OFAC_OUTPUT.csv" -- polars'
    read_csv() treats square brackets as glob syntax by default, so it was
    failing to find files that were sitting right there on disk, in every
    real Excel scan (any text/CSV-only scan happened not to hit this, since
    those filenames never get a [SheetName] suffix -- which is exactly why
    this didn't surface until a real Excel file was actually compiled).
    Fixed with glob=False in ofac_compiler.py; this test locks it in.
    """
    compiled_folder, csvs_folder = _fresh_dirs()
    db.init_database()

    run1 = db.try_start_run("TESTCO6", "2026-07-12", "manual", "tester", TEST_ROOT, 1)
    csv1 = _write_output_csv(csvs_folder, "source_file.xlsx[Sheet1]_part1_OFAC_OUTPUT.csv", ["Test Person"])
    db.write_file_log(run1, output_csv_path=csv1, output_row_count=1, file_name="source_file.xlsx")
    db.finish_run(run1, db.RUN_STATUS_COMPLETED, files_processed=1, files_failed=0)

    result = compiler.compile_company_date("TESTCO6", "2026-07-12", "20260712", compiled_folder)
    assert result["total_rows"] == 1, f"Expected the bracket-named file to be read successfully, got: {result}"
    assert result["skipped_missing_files"] == [], f"File should not have been skipped: {result['skipped_missing_files']}"
    print("test_compile_handles_bracket_containing_filenames PASSED")


def test_compile_handles_numeric_looking_sheet_names_and_company_codes():
    """
    Direct regression test for a real production bug, found via a real
    large scan: polars' read_csv() infers each CSV's column types
    independently from its own content. Most SHEET values contain letters
    ("Checklist", "RI Rate") and get read back as text -- but some source
    files have sheets literally named things like "2601" (pure digits), so
    THAT file's SHEET column gets inferred as Int64 instead. Concatenating
    a text-SHEET frame with an Int64-SHEET frame then raises
    polars.exceptions.SchemaError: type Int64 is incompatible with expected
    type String. The same risk applies to CMPY_NO -- company codes like
    "733" are pure numbers too. Fixed by forcing every output column to
    Utf8 on read, not just POLICY_NUMBER (which already had this
    protection from an earlier, narrower version of this same class of bug).
    """
    compiled_folder, csvs_folder = _fresh_dirs()
    db.init_database()

    run1 = db.try_start_run("733", "2026-07-12", "manual", "tester", TEST_ROOT, 2)

    # File A: a sheet named with letters -- SHEET column reads back as text naturally.
    path_a = os.path.join(csvs_folder, "checklist_output.csv")
    pl.DataFrame({
        "SURNAME": [""], "FIRST_NAME": [""], "COMPLETE_NAME": ["Alice Wong"],
        "SEX": ["F"], "DATE_OF_BIRTH": ["01/01/1990"], "CMPY_NO": ["733"],
        "POLICY_NUMBER": ["P1"], "FILE_PATH": ["checklist.xlsx"], "SHEET": ["Checklist"],
    }).write_csv(path_a)
    db.write_file_log(run1, output_csv_path=path_a, output_row_count=1, file_name="checklist.xlsx")

    # File B: a sheet named purely with digits -- this is what triggers polars
    # to infer SHEET as Int64 for this file specifically, and CMPY_NO="733"
    # (this company's real code) is exactly as numeric-looking.
    path_b = os.path.join(csvs_folder, "quarterly_output.csv")
    pl.DataFrame({
        "SURNAME": [""], "FIRST_NAME": [""], "COMPLETE_NAME": ["Bob Lee"],
        "SEX": ["M"], "DATE_OF_BIRTH": ["02/02/1985"], "CMPY_NO": ["733"],
        "POLICY_NUMBER": ["P2"], "FILE_PATH": ["quarterly.xlsx"], "SHEET": ["2601"],
    }).write_csv(path_b)
    db.write_file_log(run1, output_csv_path=path_b, output_row_count=1, file_name="quarterly.xlsx")

    db.finish_run(run1, db.RUN_STATUS_COMPLETED, files_processed=2, files_failed=0)

    result = compiler.compile_company_date("733", "2026-07-12", "20260712", compiled_folder)
    assert result["total_rows"] == 2, f"Expected both rows compiled without a SchemaError, got: {result}"
    on_disk = pl.read_excel(result["paths"][0])
    assert set(on_disk["COMPLETE_NAME"].to_list()) == {"Alice Wong", "Bob Lee"}
    assert set(on_disk["SHEET"].to_list()) == {"Checklist", "2601"}, "SHEET must stay text, including the numeric-looking value"
    print("test_compile_handles_numeric_looking_sheet_names_and_company_codes PASSED")


def test_missing_output_csv_is_skipped_not_fatal():
    compiled_folder, csvs_folder = _fresh_dirs()
    db.init_database()

    run1 = db.try_start_run("TESTCO4", "2026-07-12", "manual", "tester", TEST_ROOT, 1)
    db.write_file_log(run1, output_csv_path="/does/not/exist.csv", output_row_count=5, file_name="ghost.csv")
    csv1 = _write_output_csv(csvs_folder, "real.csv", ["BOB LEE"])
    db.write_file_log(run1, output_csv_path=csv1, output_row_count=1, file_name="real.csv")
    db.finish_run(run1, db.RUN_STATUS_COMPLETED, files_processed=2, files_failed=0)

    result = compiler.compile_company_date("TESTCO4", "2026-07-12", "20260712", compiled_folder)
    assert result["total_rows"] == 1
    assert result["skipped_missing_files"] == ["/does/not/exist.csv"]
    print("test_missing_output_csv_is_skipped_not_fatal PASSED")


def test_split_at_row_limit_and_rebuild_removes_stale_part():
    """
    Forces a tiny EXCEL_MAX_ROWS so a small dataset still exercises the
    multi-part split, then simulates a correction that shrinks the data back
    to 1 part and confirms the now-stale part-2 file is actually deleted
    from disk, not just untracked in the database.
    """
    compiled_folder, csvs_folder = _fresh_dirs()
    db.init_database()
    original_limit = compiler.EXCEL_MAX_ROWS
    compiler.EXCEL_MAX_ROWS = 2  # force splitting with tiny data
    try:
        run1 = db.try_start_run("TESTCO5", "2026-07-12", "manual", "tester", TEST_ROOT, 1)
        csv1 = _write_output_csv(csvs_folder, "big.csv", ["A", "B", "C", "D"])
        db.write_file_log(run1, output_csv_path=csv1, output_row_count=4, file_name="big.csv")
        db.finish_run(run1, db.RUN_STATUS_COMPLETED, files_processed=1, files_failed=0)

        result1 = compiler.compile_company_date("TESTCO5", "2026-07-12", "20260712", compiled_folder)
        assert result1["part_count"] == 2, f"Expected 2 parts with limit=2 and 4 rows, got {result1['part_count']}"
        part2_path = result1["paths"][1]
        assert os.path.exists(part2_path)

        # Simulate the underlying data shrinking to fit in 1 part: the
        # compiler re-reads the actual CSV file content on every compile
        # (it doesn't trust the output_row_count field for this), so
        # overwriting the same path with fewer rows is enough to simulate
        # "a correction reduced the row count" on the next compile call.
        os.remove(csv1)
        _write_output_csv(csvs_folder, "big.csv", ["A"])

        result2 = compiler.compile_company_date("TESTCO5", "2026-07-12", "20260712", compiled_folder)
        assert result2["part_count"] == 1, f"Expected rebuild to shrink to 1 part, got {result2['part_count']}"
        assert not os.path.exists(part2_path), "Stale part-2 file should have been deleted from disk"
        print("test_split_at_row_limit_and_rebuild_removes_stale_part PASSED")
    finally:
        compiler.EXCEL_MAX_ROWS = original_limit


if __name__ == "__main__":
    test_cumulative_compile_pulls_from_multiple_runs()
    test_compile_includes_successful_files_from_a_failed_run()
    test_compile_excludes_files_with_no_output_path()
    test_row_level_dedup_in_compile()
    test_compile_handles_bracket_containing_filenames()
    test_compile_handles_numeric_looking_sheet_names_and_company_codes()
    test_missing_output_csv_is_skipped_not_fatal()
    test_split_at_row_limit_and_rebuild_removes_stale_part()
    print("\nALL COMPILER TESTS PASSED")
