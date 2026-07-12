"""
test_extraction_engine.py
Tests for ofac_extraction_engine.py.

NOT RUN in the environment this was written in -- polars isn't installed
there and there's no network access to get it. Run this on a machine with
polars before trusting the extraction engine in production:

    pip install polars python-dateutil
    python test_extraction_engine.py

Every scenario here mirrors one already passing in test_header_detection.py
and test_data_cleaning.py, so a failure here specifically isolates a problem
in the polars glue itself (ofac_extraction_engine.py), not the underlying
detection or cleaning logic, which is already proven correct.
"""

import polars as pl

import ofac_extraction_engine as engine

HEADER_SETS = {
    "name": {"name", "insuredname", "fullname"},
    "firstlastname": {"firstname", "lastname"},
    "sex": {"sex", "gender"},
    "dob": {"dob", "dateofbirth"},
    "policynum": {"policyno", "policynumber"},
}


def _df_from_rows(rows):
    """Build a headerless polars DataFrame the same way the real pipeline
    reads Excel/CSV: has_header=False, generic column names."""
    width = max(len(r) for r in rows)
    padded = [list(r) + [None] * (width - len(r)) for r in rows]
    columns = [f"column_{i}" for i in range(width)]
    return pl.DataFrame(padded, schema=columns, orient="row")


def test_basic_extraction():
    df = _df_from_rows([
        ("Name", "Sex", "DOB", "Policy No"),
        ("John Smith", "M", "1990-01-01", "P123456"),
        ("Jane Doe", "F", "1985-05-05", "P654321"),
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    assert output_df.height == 2, f"Expected 2 output rows, got {output_df.height}"
    rows = output_df.sort("COMPLETE_NAME").to_dicts()
    assert rows[0]["COMPLETE_NAME"] == "JANE DOE"
    assert rows[0]["SEX"] == "F"
    assert rows[0]["DATE_OF_BIRTH"] == "05/05/1985"
    assert rows[0]["POLICY_NUMBER"] == "P654321"
    assert rows[1]["COMPLETE_NAME"] == "JOHN SMITH"
    assert len(meta) == 1
    assert meta[0]["output_row_count"] == 2
    print("test_basic_extraction PASSED")


def test_header_not_at_top_end_to_end():
    df = _df_from_rows([
        ("BANNER ROW",),
        ("", "", "", ""),
        ("Name", "Sex", "DOB", "Policy No"),
        ("Alice Wong", "F", "1992-03-03", "P111"),
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    assert output_df.height == 1
    assert output_df.to_dicts()[0]["COMPLETE_NAME"] == "ALICE WONG"
    print("test_header_not_at_top_end_to_end PASSED")


def test_multi_name_column_explosion():
    # One row lists two people in a single "Name" cell context via two name
    # columns both matching the "name" synonym -- e.g. joint policy.
    df = _df_from_rows([
        ("Name1", "Name2", "Policy No"),
        # header row won't match by synonym directly since "Name1"/"Name2"
        # aren't in HEADER_SETS -- use content-based-friendly explicit synonyms instead:
    ])
    # Rebuild with real matching synonyms for a cleaner explosion test
    df = _df_from_rows([
        ("Name", "Name", "Policy No"),
        ("John Smith", "Jane Smith", "P999"),
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    names = set(output_df["COMPLETE_NAME"].to_list())
    assert names == {"JOHN SMITH", "JANE SMITH"}, f"Expected both names exploded into separate rows, got: {names}"
    assert meta[0]["multiple_name"] is True
    print("test_multi_name_column_explosion PASSED")


def test_surname_firstname_pair_explosion():
    df = _df_from_rows([
        ("LastName", "FirstName", "LastName", "FirstName", "Policy No"),
        ("Smith", "John", "Doe", "Jane", "P555"),
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    names = set(output_df["COMPLETE_NAME"].to_list())
    assert names == {"SMITH JOHN", "DOE JANE"}, f"Expected paired surname/firstname exploded, got: {names}"
    print("test_surname_firstname_pair_explosion PASSED")


def test_missing_name_rows_are_dropped_and_counted():
    df = _df_from_rows([
        ("Name", "Sex", "DOB", "Policy No"),
        ("John Smith", "M", "1990-01-01", "P123456"),
        ("", "F", "1985-05-05", "P654321"),  # no name -- should be dropped
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    assert output_df.height == 1
    assert meta[0]["missing_name_count"] == 1
    print("test_missing_name_rows_are_dropped_and_counted PASSED")


def test_name_with_digit_falls_back_to_surname_firstname():
    # COMPLETE_NAME contains a digit (garbage/leaked policy number) but
    # SURNAME/FIRST_NAME are clean -- safety net should prefer those.
    df = _df_from_rows([
        ("Name", "LastName", "FirstName", "Policy No"),
        ("P123456", "Smith", "John", "P123456"),
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    assert output_df.height == 1
    assert output_df.to_dicts()[0]["COMPLETE_NAME"] == "SMITH JOHN", (
        f"Expected fallback to SURNAME+FIRST_NAME, got: {output_df.to_dicts()[0]['COMPLETE_NAME']}"
    )
    print("test_name_with_digit_falls_back_to_surname_firstname PASSED")


def test_numeric_looking_name_column_excluded():
    # A column that matches the "name" synonym by header text but is
    # actually numeric (e.g. an ID column mislabeled) should be filtered out.
    df = _df_from_rows([
        ("Name", "PolicyNo"),
        ("123456789", "P1"),
        ("987654321", "P2"),
        ("111222333", "P3"),
        ("444555666", "P4"),
        ("777888999", "P5"),
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    # With the "Name" column excluded as numeric, there's no usable name
    # source at all, so no rows should survive (all filtered as missing-name).
    assert output_df.height == 0, f"Expected numeric column to be excluded, got {output_df.height} rows"
    print("test_numeric_looking_name_column_excluded PASSED")


def test_deceased_marker_and_punctuation_stripped():
    df = _df_from_rows([
        ("Name", "Policy No"),
        ("O'Brien-Smith DECEASED", "P1"),
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    assert output_df.to_dicts()[0]["COMPLETE_NAME"] == "O BRIEN SMITH"
    print("test_deceased_marker_and_punctuation_stripped PASSED")


def test_no_matches_returns_empty_frame_with_correct_schema():
    df = _df_from_rows([
        ("Premium", "Amount"),
        ("Term Life", "50000"),
        ("Whole Life", "75000"),
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    assert output_df.height == 0
    assert output_df.columns == list(engine.OUTPUT_COLUMNS)
    assert meta == []
    print("test_no_matches_returns_empty_frame_with_correct_schema PASSED")


def test_row_level_dedup_within_extraction():
    df = _df_from_rows([
        ("Name", "Sex", "DOB", "Policy No"),
        ("John Smith", "M", "1990-01-01", "P123456"),
        ("John Smith", "M", "1990-01-01", "P123456"),  # exact duplicate row
    ])
    output_df, meta = engine.extract_from_dataframe(df, HEADER_SETS, "TESTCO", "/in/test.xlsx", "Sheet1")
    assert output_df.height == 1, f"Expected exact duplicate row collapsed, got {output_df.height}"
    print("test_row_level_dedup_within_extraction PASSED")


if __name__ == "__main__":
    test_basic_extraction()
    test_header_not_at_top_end_to_end()
    test_multi_name_column_explosion()
    test_surname_firstname_pair_explosion()
    test_missing_name_rows_are_dropped_and_counted()
    test_name_with_digit_falls_back_to_surname_firstname()
    test_numeric_looking_name_column_excluded()
    test_deceased_marker_and_punctuation_stripped()
    test_no_matches_returns_empty_frame_with_correct_schema()
    test_row_level_dedup_within_extraction()
    print("\nALL EXTRACTION ENGINE TESTS PASSED")
