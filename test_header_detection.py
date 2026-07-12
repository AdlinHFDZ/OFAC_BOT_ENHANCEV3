"""
test_header_detection.py
Unit tests for ofac_header_detection.py -- pure Python, no polars needed.
Includes a direct reproduction of the v2 code-review bug (10-row cap
silently dropping columns whose data starts later).
"""

import os
import tempfile
os.environ.setdefault("OFAC_APP_ROOT", os.path.join(tempfile.gettempdir(), "ofac_header_detection_test_root"))

import ofac_header_detection as det

HEADER_SETS = {
    "name": {"name", "insuredname", "fullname"},
    "firstlastname": {"firstname", "lastname"},
    "sex": {"sex", "gender"},
    "dob": {"dob", "dateofbirth"},
    "policynum": {"policyno", "policynumber"},
}


def test_basic_header_detection():
    rows = [
        ("Name", "Sex", "DOB", "Policy No"),
        ("John Smith", "M", "1990-01-01", "P123456"),
        ("Jane Doe", "F", "1985-05-05", "P654321"),
    ]
    result = det.detect_all(rows, num_columns=4, header_sets=HEADER_SETS)
    assert len(result) == 1
    match = result[0]
    assert match["header_row_idx"] == 0
    assert match["columns"]["name"] == [0]
    assert match["columns"]["sex"] == [1]
    assert match["columns"]["dob"] == [2]
    assert match["columns"]["policynum"] == [3]
    print("test_basic_header_detection PASSED")


def test_header_row_not_at_top():
    # 5 blank/banner rows, then the real header at row 5
    rows = [
        ("COMPANY REPORT",),
        ("Generated 2026-01-01",),
        ("", "", "", ""),
        ("", "", "", ""),
        ("", "", "", ""),
        ("Name", "Sex", "DOB", "Policy No"),
        ("John Smith", "M", "1990-01-01", "P123456"),
    ]
    result = det.detect_all(rows, num_columns=4, header_sets=HEADER_SETS)
    assert len(result) == 1
    assert result[0]["header_row_idx"] == 5
    print("test_header_row_not_at_top PASSED")


def test_THE_ACTUAL_REVIEW_BUG_data_starts_after_row_10():
    """
    This is a direct reproduction of the exact bug flagged in the code
    review: v2's find_non_empty_columns only checked the first 10 rows to
    decide if a column had data, silently dropping a policy-number column
    whose values only started at row 12. With MAX_SEARCH_ROWS=50 passed
    through everywhere (no hardcoded smaller default), this must now work.
    """
    rows = [("Title row",)] * 3
    rows += [("", "", "", "")] * 8            # rows 3-10: all blank
    rows.append(("Name", "Sex", "DOB", "Policy No"))  # row 11: real header
    rows.append(("John Smith", "M", "1990-01-01", "P123456"))  # row 12: data
    # total: header at row_idx 11, first data at row_idx 12 -- both well
    # past the old buggy 10-row cap.

    result = det.detect_all(rows, num_columns=4, header_sets=HEADER_SETS)
    assert len(result) == 1, f"Expected the header block to be found, got: {result}"
    match = result[0]
    assert match["header_row_idx"] == 11
    assert match["columns"]["policynum"] == [3], (
        f"Policy Number column was dropped -- this is exactly the bug from the review. "
        f"Got columns: {match['columns']}"
    )
    print("test_THE_ACTUAL_REVIEW_BUG_data_starts_after_row_10 PASSED "
          "(confirmed fixed: policy# column found despite data starting at row 12)")


def test_multi_table_side_by_side():
    # Two unrelated tables on one sheet, separated by a blank column
    rows = [
        ("Name", "DOB", "", "Product", "Rate"),
        ("Alice", "1990-01-01", "", "TermLife", "0.05"),
        ("Bob", "1985-05-05", "", "WholeLife", "0.08"),
    ]
    result = det.detect_all(rows, num_columns=5, header_sets=HEADER_SETS)
    # Only the left block (cols 0-1) has name/dob-shaped headers; the right
    # block (cols 3-4) has no name/firstlastname match, so it should NOT
    # produce a spurious result.
    assert len(result) == 1, f"Expected exactly 1 usable table block, got {len(result)}: {result}"
    assert result[0]["col_start"] == 0
    assert result[0]["columns"]["name"] == [0]
    print("test_multi_table_side_by_side PASSED")


def test_fuzzy_fallback_catches_near_miss_header():
    # "Insured Nme" is a typo of "Insured Name" -- not an exact match, should
    # be caught by the fuzzy fallback.
    rows = [
        ("Insured Nme", "Sex", "DOB", "Policy No"),
        ("John Smith", "M", "1990-01-01", "P123456"),
    ]
    result = det.detect_all(rows, num_columns=4, header_sets=HEADER_SETS)
    assert len(result) == 1, f"Expected fuzzy match to succeed, got: {result}"
    assert result[0]["columns"]["name"] == [0]
    print("test_fuzzy_fallback_catches_near_miss_header PASSED")


def test_content_based_fallback_when_no_header_matches_at_all():
    # No row anywhere looks like a recognizable header at all -- headerless
    # export. Content-based detection should still find name-shaped data.
    # (5+ rows: below MIN_SAMPLE_FOR_NAME_INFERENCE the uniqueness check
    # can't run at all, by design -- see infer_column_type_by_content.)
    rows = [
        ("John Smith", "M", "1990-01-01", "P123456"),
        ("Jane Doe", "F", "1985-05-05", "P654321"),
        ("Robert Brown", "M", "1978-12-12", "P999999"),
        ("Maria Garcia", "F", "1982-03-15", "P111222"),
        ("Wei Chen", "M", "1995-07-30", "P333444"),
    ]
    result = det.detect_all(rows, num_columns=4, header_sets=HEADER_SETS)
    assert len(result) == 1, f"Expected content-based fallback to kick in, got: {result}"
    assert result[0]["header_row_idx"] == -1
    assert result[0].get("content_based") is True
    assert result[0]["columns"]["name"] == [0]
    assert result[0]["columns"]["sex"] == [1]
    print("test_content_based_fallback_when_no_header_matches_at_all PASSED")


def test_no_name_column_anywhere_returns_empty():
    # A sheet that genuinely has no name-shaped data at all (mirrors real
    # companies like N96 from the header library conversion) should return
    # no results, not a false positive. Repeated category labels (not
    # unique per row, unlike a real name list) -- this is what specifically
    # exercises the uniqueness check, not just the minimum-sample floor.
    rows = [
        ("Premium", "Amount"),
        ("Term Life", "50000"),
        ("Whole Life", "75000"),
        ("Term Life", "50000"),
        ("Whole Life", "82000"),
        ("Term Life", "61000"),
    ]
    result = det.detect_all(rows, num_columns=2, header_sets=HEADER_SETS)
    assert result == [], f"Expected no match for a name-less sheet, got: {result}"
    print("test_no_name_column_anywhere_returns_empty PASSED")


def test_numeric_looking_policy_column_not_misread_as_name():
    rows = [
        ("Name", "PolicyNo"),
        ("John Smith", "123456789"),
        ("Jane Doe", "987654321"),
    ]
    result = det.detect_all(rows, num_columns=2, header_sets=HEADER_SETS)
    assert result[0]["columns"]["policynum"] == [1]
    assert result[0]["columns"]["name"] == [0]
    print("test_numeric_looking_policy_column_not_misread_as_name PASSED")


def test_detect_header_row_for_block_picks_densest_row():
    rows = [
        ("Report generated 2026-01-01",),
        ("",),
        ("Name", "Sex", "DOB", "Policy No"),
        ("John Smith", "M", "1990-01-01", "P123456"),
    ]
    row_idx, values = det.detect_header_row_for_block(rows, col_start=0, col_end=3)
    assert row_idx == 2, f"Expected the 4-cell header row (idx 2) to win, got {row_idx}"
    assert values == ["Name", "Sex", "DOB", "Policy No"]
    print("test_detect_header_row_for_block_picks_densest_row PASSED")


def test_detect_header_row_for_block_all_empty_returns_none():
    rows = [("", "", ""), ("", "", "")]
    row_idx, values = det.detect_header_row_for_block(rows, col_start=0, col_end=2)
    assert row_idx is None
    assert values == []
    print("test_detect_header_row_for_block_all_empty_returns_none PASSED")


def test_categorise_column_content_variants():
    assert det.categorise_column_content(["M", "F", "M", "F", "M"]) == "Sex"
    assert det.categorise_column_content(["1990-01-01", "1985-05-05", "1978-12-12", "1982-03-15", "1995-07-30"]) == "DOB"
    assert det.categorise_column_content(["123", "456", "789", "111", "222"]) == "Numeric"
    assert det.categorise_column_content(["ABC_1234", "XYZ_5678", "DEF_9012", "GHI_3456", "JKL_7890"]) == "Identifier"
    assert det.categorise_column_content(["", "", ""]) == "Empty"
    print("test_categorise_column_content_variants PASSED")


def test_categorise_column_content_name_uses_same_uniqueness_guard():
    # Should NOT be misclassified as Name -- same false-positive scenario
    # as the earlier content-based-fallback bug, now guarded here too since
    # this reuses infer_column_type_by_content.
    repeated_labels = ["Term Life", "Whole Life", "Term Life", "Whole Life", "Term Life", "Whole Life"]
    result = det.categorise_column_content(repeated_labels)
    assert result != "Name", f"Expected repeated category labels not classified as Name, got {result}"
    print("test_categorise_column_content_name_uses_same_uniqueness_guard PASSED")


if __name__ == "__main__":
    test_basic_header_detection()
    test_header_row_not_at_top()
    test_THE_ACTUAL_REVIEW_BUG_data_starts_after_row_10()
    test_multi_table_side_by_side()
    test_fuzzy_fallback_catches_near_miss_header()
    test_content_based_fallback_when_no_header_matches_at_all()
    test_no_name_column_anywhere_returns_empty()
    test_numeric_looking_policy_column_not_misread_as_name()
    test_detect_header_row_for_block_picks_densest_row()
    test_detect_header_row_for_block_all_empty_returns_none()
    test_categorise_column_content_variants()
    test_categorise_column_content_name_uses_same_uniqueness_guard()
    print("\nALL HEADER DETECTION TESTS PASSED")
