"""
test_header_extractor_engine.py
NOT RUN here (no polars). Run on a machine with polars installed:
    pip install polars python-dateutil
    python test_header_extractor_engine.py
"""

import os
import shutil
import tempfile

import polars as pl
import openpyxl
import ofac_header_extractor_engine as hee


def _df_from_rows(rows):
    width = max(len(r) for r in rows)
    padded = [list(r) + [None] * (width - len(r)) for r in rows]
    columns = [f"column_{i}" for i in range(width)]
    return pl.DataFrame(padded, schema=columns, orient="row")


def test_basic_header_extraction():
    # 5+ data rows -- name-content inference deliberately won't commit to
    # "Name" below MIN_SAMPLE_FOR_NAME_INFERENCE rows (see
    # ofac_header_detection.py), by design, to avoid the false-positive bug
    # that guard was added to fix. Real files always have far more than 2
    # rows, so this matches realistic usage, not just a bigger fixture.
    df = _df_from_rows([
        ("Insured Name", "Sex", "DOB", "Policy No"),
        ("John Smith", "M", "1990-01-01", "P123456"),
        ("Jane Doe", "F", "1985-05-05", "P654321"),
        ("Robert Brown", "M", "1978-12-12", "P999999"),
        ("Maria Garcia", "F", "1982-03-15", "P111222"),
        ("Wei Chen", "M", "1995-07-30", "P333444"),
    ])
    records = hee.extract_headers_from_dataframe(df, "/in/test.xlsx", "Sheet1")
    assert len(records) == 4
    headers = {r["Header"]: r["Category"] for r in records}
    assert headers["Insured Name"] == "Name"
    assert headers["Sex"] == "Sex"
    assert headers["DOB"] == "DOB"
    assert headers["Policy No"] == "PolicyNumber"
    print("test_basic_header_extraction PASSED")


def test_multi_table_sheet_reports_both_tables():
    df = _df_from_rows([
        ("Name", "DOB", "", "Product", "Rate"),
        ("Alice", "1990-01-01", "", "TermLife", "0.05"),
        ("Bob", "1985-05-05", "", "WholeLife", "0.08"),
    ])
    records = hee.extract_headers_from_dataframe(df, "/in/test.xlsx", "Sheet1")
    tables = {r["Table"] for r in records}
    assert len(tables) == 2, f"Expected 2 distinct tables reported, got {tables}"
    print("test_multi_table_sheet_reports_both_tables PASSED")


def test_unrecognized_business_columns_get_generic_categories():
    df = _df_from_rows([
        ("Premium", "Claim ID", "Notes"),
        ("50000", "CLM-0001", "some free text here"),
        ("75000", "CLM-0002", "more free text here"),
    ])
    records = hee.extract_headers_from_dataframe(df, "/in/test.xlsx", "Sheet1")
    by_header = {r["Header"]: r["Category"] for r in records}
    assert by_header["Premium"] == "Numeric"
    print("test_unrecognized_business_columns_get_generic_categories PASSED", by_header)


def test_process_excel_file_for_headers_real_xlsx():
    """
    Closes a real gap: every other test in this file builds a polars
    DataFrame directly in memory and calls extract_headers_from_dataframe()
    on it -- none of them exercise process_excel_file_for_headers(), which
    is what actually calls pl.read_excel() against a real file in
    production. This writes a genuine .xlsx with openpyxl and runs it
    through the real function, so a dependency gap in the Excel read path
    (like the missing fastexcel package) can't hide behind a passing test
    suite again.
    """
    test_dir = tempfile.mkdtemp(prefix="ofac_header_extractor_test_")
    try:
        test_xlsx_path = os.path.join(test_dir, "real_test.xlsx")
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet.append(["Insured Name", "Sex", "DOB", "Policy No"])
        sheet.append(["John Smith", "M", "1990-01-01", "P123456"])
        sheet.append(["Jane Doe", "F", "1985-05-05", "P654321"])
        sheet.append(["Robert Brown", "M", "1978-12-12", "P999999"])
        sheet.append(["Maria Garcia", "F", "1982-03-15", "P111222"])
        sheet.append(["Wei Chen", "M", "1995-07-30", "P333444"])
        workbook.save(test_xlsx_path)

        records, error = hee.process_excel_file_for_headers(test_xlsx_path, "real_test.xlsx", [])
        assert error is None, f"Expected no error, got: {error}"
        assert len(records) == 4, f"Expected 4 header records, got {len(records)}"
        headers = {r["Header"]: r["Category"] for r in records}
        assert headers["Insured Name"] == "Name"
        assert headers["Sex"] == "Sex"
        assert headers["DOB"] == "DOB"
        assert headers["Policy No"] == "PolicyNumber"
        print("test_process_excel_file_for_headers_real_xlsx PASSED "
              "(this is the test that would have caught the missing fastexcel dependency)")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_basic_header_extraction()
    test_multi_table_sheet_reports_both_tables()
    test_unrecognized_business_columns_get_generic_categories()
    test_process_excel_file_for_headers_real_xlsx()
    print("\nALL HEADER EXTRACTOR ENGINE TESTS PASSED")
