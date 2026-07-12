"""
test_data_cleaning.py
Unit tests for ofac_data_cleaning.py.
"""

import ofac_data_cleaning as dc


def test_clean_name_text():
    assert dc.clean_name_text("John Smith") == "JOHN SMITH"
    assert dc.clean_name_text("john   smith") == "JOHN SMITH"  # collapses whitespace
    assert dc.clean_name_text("O'Brien-Smith") == "O BRIEN SMITH"  # strips punctuation
    assert dc.clean_name_text("John Smith DECEASED") == "JOHN SMITH"  # drops marker
    assert dc.clean_name_text("DECEASED") == ""
    assert dc.clean_name_text(None) == ""
    assert dc.clean_name_text("") == ""
    assert dc.clean_name_text("John123 Smith") == "JOHN SMITH"  # strips embedded digits
    print("test_clean_name_text PASSED")


def test_contains_digit():
    assert dc.contains_digit("P123456") is True
    assert dc.contains_digit("John Smith") is False
    assert dc.contains_digit(None) is False
    assert dc.contains_digit("") is False
    print("test_contains_digit PASSED")


def test_is_numeric_like():
    assert dc.is_numeric_like("123456") is True
    assert dc.is_numeric_like("123-456") is False
    assert dc.is_numeric_like("John") is False
    assert dc.is_numeric_like(None) is False
    assert dc.is_numeric_like("  789  ") is True
    print("test_is_numeric_like PASSED")


def test_normalize_sex():
    assert dc.normalize_sex("M") == "M"
    assert dc.normalize_sex("m") == "M"
    assert dc.normalize_sex("Male") == "M"
    assert dc.normalize_sex("MALE") == "M"
    assert dc.normalize_sex("F") == "F"
    assert dc.normalize_sex("female") == "F"
    assert dc.normalize_sex("") == ""
    assert dc.normalize_sex(None) == ""
    assert dc.normalize_sex("U") == "U"  # unknown/other passed through uppercased
    print("test_normalize_sex PASSED")


def test_date_parsing_common_formats():
    cases = [
        ("1990-01-15", "01/15/1990"),
        ("01/15/1990", "01/15/1990"),
        ("15/01/1990", "01/15/1990"),   # dateutil default is month-first for ambiguous US-style app
        ("15-Jan-1990", "01/15/1990"),
        ("15-Jan-90", "01/15/1990"),
        ("Jan 15, 1990", "01/15/1990"),
        ("15 January 1990", "01/15/1990"),
        ("19900115", "01/15/1990"),
        ("1990.01.15", "01/15/1990"),
    ]
    for input_val, expected in cases:
        result = dc.parse_date_to_mmddyyyy(input_val)
        assert result == expected, f"parse_date_to_mmddyyyy({input_val!r}) = {result!r}, expected {expected!r}"
    print("test_date_parsing_common_formats PASSED")


def test_date_parsing_edge_cases():
    assert dc.parse_date_to_mmddyyyy(None) == ""
    assert dc.parse_date_to_mmddyyyy("") == ""
    assert dc.parse_date_to_mmddyyyy("not a date") == ""
    assert dc.parse_date_to_mmddyyyy("N/A") == ""
    from datetime import datetime as dt
    assert dc.parse_date_to_mmddyyyy(dt(1990, 1, 15)) == "01/15/1990"
    print("test_date_parsing_edge_cases PASSED")


def test_THE_ACTUAL_BUG_bare_numbers_no_longer_become_fake_dates():
    """
    Direct regression test for the bug found while testing the header
    extractor: dateutil was filling in missing year/month/day from *today*
    for bare short numbers, so "123" silently became "07/11/123" and "5"
    became today's date with day=5 -- neither is a real date in the source
    file, both were dateutil guessing. This must return "" now.
    """
    for garbage in ["123", "456", "5", "42", "1", "99", "0"]:
        result = dc.parse_date_to_mmddyyyy(garbage)
        assert result == "", (
            f"parse_date_to_mmddyyyy({garbage!r}) = {result!r}, expected '' -- "
            f"a bare short number should never be silently turned into a fake date"
        )
    # 8-digit bare numbers are still legitimately supported (YYYYMMDD etc.)
    assert dc.parse_date_to_mmddyyyy("19900115") == "01/15/1990"
    print("test_THE_ACTUAL_BUG_bare_numbers_no_longer_become_fake_dates PASSED")


def test_date_parsing_python_date_object():
    from datetime import date
    assert dc.parse_date_to_mmddyyyy(date(1990, 1, 15)) == "01/15/1990"
    print("test_date_parsing_python_date_object PASSED")


if __name__ == "__main__":
    test_clean_name_text()
    test_contains_digit()
    test_is_numeric_like()
    test_normalize_sex()
    test_date_parsing_common_formats()
    test_date_parsing_edge_cases()
    test_THE_ACTUAL_BUG_bare_numbers_no_longer_become_fake_dates()
    test_date_parsing_python_date_object()
    print("\nALL DATA CLEANING TESTS PASSED")
