"""
test_gui_helpers.py
"""

import os
import ofac_gui_helpers as gh


def test_build_watcher_config_stores_real_password_values():
    """
    Config used to store an opaque label, never the raw password (vault was
    DPAPI-encrypted then). The vault is unencrypted now, by request -- the
    config file is correspondingly simpler too: it just carries the actual
    selected password values directly, no separate resolve-at-scan-time
    step. This test's old name/assertions checked the opposite of current,
    intended behavior; rewritten to match reality.
    """
    config = gh.build_watcher_config(
        "TESTCO", "2026-07-12", ["a.xlsx", "b.csv"], ["actual_password_1"], "jdoe", "/watch"
    )
    assert config["company_code"] == "TESTCO"
    assert config["files"] == ["a.xlsx", "b.csv"]
    assert config["passwords"] == ["actual_password_1"], "Config should carry the real password value directly"
    print("test_build_watcher_config_stores_real_password_values PASSED")


def test_format_and_parse_date_roundtrip():
    from datetime import date
    d = date(2026, 7, 12)
    formatted = gh.format_date_for_config(d)
    assert formatted == "2026-07-12"
    parsed = gh.parse_config_date_for_display(formatted)
    assert parsed == d
    print("test_format_and_parse_date_roundtrip PASSED")


def test_filter_by_search_case_insensitive():
    items = ["Company A", "Company B", "company c", "COMPANY D"]
    assert gh.filter_by_search(items, "company") == items
    assert gh.filter_by_search(items, "company b") == ["Company B"]
    assert gh.filter_by_search(items, "d") == ["COMPANY D"]
    assert gh.filter_by_search(items, "") == items
    assert gh.filter_by_search(items, "zzz") == []
    print("test_filter_by_search_case_insensitive PASSED")


def test_filter_files_by_extension():
    files = ["report.xlsx", "data.csv", "archive.zip", "notes.txt", "unknown.xyz"]
    assert gh.filter_files_by_extension(files, show_excel=True, show_text=False, show_archive=False) == ["report.xlsx"]
    assert set(gh.filter_files_by_extension(files, True, True, False)) == {"report.xlsx", "data.csv", "notes.txt"}
    assert gh.filter_files_by_extension(files, False, False, False) == []
    assert "unknown.xyz" not in gh.filter_files_by_extension(files, True, True, True)
    print("test_filter_files_by_extension PASSED")


def test_file_type_label():
    assert gh.file_type_label("report.xlsx") == "Excel"
    assert gh.file_type_label("data.csv") == "Text"
    assert gh.file_type_label("archive.zip") == "Archive"
    assert gh.file_type_label("unknown.xyz") == "Unknown"
    print("test_file_type_label PASSED")


def test_format_file_size():
    assert gh.format_file_size(500) == "500 B"
    assert gh.format_file_size(1536) == "1.5 KB"
    assert gh.format_file_size(1024 * 1024 * 2) == "2.0 MB"
    assert gh.format_file_size(1024 * 1024 * 1024 * 3) == "3.0 GB"
    print("test_format_file_size PASSED")


def test_list_known_company_codes_unions_both_folders():
    """
    OFAC_APP_ROOT is only read once, when ofac_constants first imports --
    which already happened at the top of this test file, via `import
    ofac_gui_helpers`. Setting the env var here would be too late and would
    silently test against the wrong (default) directory. Instead, directly
    patch the folder-path attributes on the already-imported ofac_constants
    module -- list_known_company_codes() does its `from ofac_constants
    import ...` INSIDE the function body, so it re-reads these attributes
    fresh on every call and picks up the patched paths correctly.
    """
    import shutil
    import tempfile
    import ofac_constants

    test_root = os.path.join(tempfile.gettempdir(), "ofac_gui_helper_test_suite")
    if os.path.exists(test_root):
        shutil.rmtree(test_root)
    headers_companies = os.path.join(test_root, "headers", "companies")
    passwords_companies = os.path.join(test_root, "passwords", "companies")
    os.makedirs(headers_companies, exist_ok=True)
    os.makedirs(passwords_companies, exist_ok=True)

    original_headers = ofac_constants.HEADERS_COMPANIES_FOLDER
    original_passwords = ofac_constants.PASSWORDS_COMPANIES_FOLDER
    ofac_constants.HEADERS_COMPANIES_FOLDER = headers_companies
    ofac_constants.PASSWORDS_COMPANIES_FOLDER = passwords_companies
    try:
        # COMPANY_A: header file only. COMPANY_B: password file only. COMPANY_C: both.
        open(os.path.join(headers_companies, "COMPANY_A.json"), "w").write("{}")
        open(os.path.join(passwords_companies, "COMPANY_B.json"), "w").write("{}")
        open(os.path.join(headers_companies, "COMPANY_C.json"), "w").write("{}")
        open(os.path.join(passwords_companies, "COMPANY_C.json"), "w").write("{}")

        codes = gh.list_known_company_codes()
        assert codes == ["COMPANY_A", "COMPANY_B", "COMPANY_C"], f"Got: {codes}"
        print("test_list_known_company_codes_unions_both_folders PASSED")
    finally:
        ofac_constants.HEADERS_COMPANIES_FOLDER = original_headers
        ofac_constants.PASSWORDS_COMPANIES_FOLDER = original_passwords


def test_parse_dnd_file_list_simple_paths_no_spaces():
    result = gh.parse_dnd_file_list("C:/data/a.xlsx C:/data/b.csv")
    assert result == ["C:/data/a.xlsx", "C:/data/b.csv"]
    print("test_parse_dnd_file_list_simple_paths_no_spaces PASSED")


def test_parse_dnd_file_list_single_path_with_spaces():
    # This is THE case that breaks a naive .split(" ") implementation --
    # Windows paths very commonly contain spaces (user folder names, etc.)
    result = gh.parse_dnd_file_list("{C:/Users/Jo Smith/Documents/report file.xlsx}")
    assert result == ["C:/Users/Jo Smith/Documents/report file.xlsx"]
    print("test_parse_dnd_file_list_single_path_with_spaces PASSED")


def test_parse_dnd_file_list_mixed_braced_and_unbraced():
    result = gh.parse_dnd_file_list("{C:/Users/Jo Smith/a.xlsx} C:/data/b.csv {D:/My Files/c.zip}")
    assert result == ["C:/Users/Jo Smith/a.xlsx", "C:/data/b.csv", "D:/My Files/c.zip"]
    print("test_parse_dnd_file_list_mixed_braced_and_unbraced PASSED")


def test_parse_dnd_file_list_single_file_no_braces():
    result = gh.parse_dnd_file_list("C:/data/single_file.csv")
    assert result == ["C:/data/single_file.csv"]
    print("test_parse_dnd_file_list_single_file_no_braces PASSED")


def test_parse_dnd_file_list_empty_string():
    assert gh.parse_dnd_file_list("") == []
    print("test_parse_dnd_file_list_empty_string PASSED")


def test_parse_dnd_file_list_extra_whitespace_between_paths():
    result = gh.parse_dnd_file_list("C:/a.csv   C:/b.csv")
    assert result == ["C:/a.csv", "C:/b.csv"]
    print("test_parse_dnd_file_list_extra_whitespace_between_paths PASSED")


def test_validate_scan_request():
    assert gh.validate_scan_request("", [], []) == ["Select a company code.", "Select at least one file."]
    assert gh.validate_scan_request("TESTCO", [], ["a.csv"]) == []
    print("test_validate_scan_request PASSED")


def test_validate_scan_request_with_password():
    problems = gh.validate_scan_request_with_password("TESTCO", [], ["a.csv"])
    assert len(problems) == 1
    assert "password" in problems[0].lower()

    assert gh.validate_scan_request_with_password("TESTCO", ["Password 1"], ["a.csv"]) == []
    print("test_validate_scan_request_with_password PASSED")


if __name__ == "__main__":
    test_build_watcher_config_stores_real_password_values()
    test_format_and_parse_date_roundtrip()
    test_filter_by_search_case_insensitive()
    test_filter_files_by_extension()
    test_file_type_label()
    test_format_file_size()
    test_list_known_company_codes_unions_both_folders()
    test_parse_dnd_file_list_simple_paths_no_spaces()
    test_parse_dnd_file_list_single_path_with_spaces()
    test_parse_dnd_file_list_mixed_braced_and_unbraced()
    test_parse_dnd_file_list_single_file_no_braces()
    test_parse_dnd_file_list_empty_string()
    test_parse_dnd_file_list_extra_whitespace_between_paths()
    test_validate_scan_request()
    test_validate_scan_request_with_password()
    print("\nALL GUI HELPER TESTS PASSED")
