"""
ofac_gui_helpers.py
Pure-logic pieces of the GUI, pulled out so they're testable without tkinter
(which isn't installed in the environment this was built in -- see
ofac_gui_main.py's docstring for the full testing situation). Widget code
calls into these; none of these functions touch a widget.
"""

import os
from datetime import datetime

from ofac_constants import FILE_EXTENSIONS_EXCEL, FILE_EXTENSIONS_TEXT, FILE_EXTENSIONS_ARCHIVE


def build_watcher_config(company_code, email_received_date, files, passwords, user, input_folder):
    """
    Assembles the dict written to configuration_<timestamp>.json for
    "Queue for Watcher". Stores the actual selected password values --
    the vault itself is unencrypted (see ofac_password_vault.py's
    docstring for why), so there's no separate label to resolve at scan
    time anymore; the config file is self-contained.
    """
    return {
        "processed_at": datetime.now().isoformat(),
        "user": user,
        "company_code": company_code,
        "email_received_date": email_received_date,
        "files": list(files),
        "passwords": list(passwords),
        "input_folder": input_folder,
    }


def format_date_for_config(date_obj):
    """date/datetime -> 'YYYY-MM-DD' string, the format ofac_watcher.validate_config expects."""
    return date_obj.strftime("%Y-%m-%d")


def parse_config_date_for_display(date_str):
    """'YYYY-MM-DD' -> a datetime.date, for pre-populating a date picker (e.g. re-opening a draft)."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def filter_by_search(items, search_term):
    """Case-insensitive substring filter, used for both the company-code
    search box and the password search box."""
    if not search_term:
        return list(items)
    term = search_term.strip().lower()
    return [item for item in items if term in item.lower()]


def filter_files_by_extension(filenames, show_excel=True, show_text=True, show_archive=True):
    """
    Applies the three filter checkboxes (Excel / CSV-Text / Archive) to a
    file name list. Files with an unrecognized extension are always
    excluded (nothing in the app knows how to process them).
    """
    result = []
    for name in filenames:
        ext = os.path.splitext(name)[1].lower().lstrip(".")
        if ext in FILE_EXTENSIONS_EXCEL and show_excel:
            result.append(name)
        elif ext in FILE_EXTENSIONS_TEXT and show_text:
            result.append(name)
        elif ext in FILE_EXTENSIONS_ARCHIVE and show_archive:
            result.append(name)
    return result


def file_type_label(filename):
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext in FILE_EXTENSIONS_EXCEL:
        return "Excel"
    if ext in FILE_EXTENSIONS_TEXT:
        return "Text"
    if ext in FILE_EXTENSIONS_ARCHIVE:
        return "Archive"
    return "Unknown"


def format_file_size(size_bytes):
    """Human-readable file size, e.g. 1536 -> '1.5 KB'."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.1f} KB"
    size_mb = size_kb / 1024
    if size_mb < 1024:
        return f"{size_mb:.1f} MB"
    return f"{size_mb / 1024:.1f} GB"


def list_known_company_codes():
    """
    Union of every company code that has either a header override file or a
    password vault file. A code not in this list isn't an error -- typing a
    brand new code just means "defaults.json only, no passwords yet", both
    perfectly valid starting states. This replaces v1/v2's CSV-row-scanning
    approach now that headers/passwords are per-company JSON files.
    """
    from ofac_constants import HEADERS_COMPANIES_FOLDER, PASSWORDS_COMPANIES_FOLDER

    codes = set()
    for folder in [HEADERS_COMPANIES_FOLDER, PASSWORDS_COMPANIES_FOLDER]:
        if os.path.isdir(folder):
            for fname in os.listdir(folder):
                if fname.endswith(".json"):
                    codes.add(fname[:-len(".json")])
    return sorted(codes)


def parse_dnd_file_list(raw_drop_data):
    """
    Parses the raw string tkinterdnd2 hands back on a file-drop event.
    Format: paths are space-separated, EXCEPT a path containing spaces
    (very common on Windows -- "C:\\Users\\Jo Smith\\file.xlsx") gets
    wrapped in curly braces instead: "{C:\\Users\\Jo Smith\\file.xlsx} C:\\other.csv".
    This is a well-known tkinterdnd2 quirk, not something specific to this
    app -- getting it wrong means any dropped file with a space in its path
    silently gets mangled into multiple bogus paths.
    """
    paths = []
    i = 0
    n = len(raw_drop_data)
    while i < n:
        if raw_drop_data[i] == " ":
            i += 1
            continue
        if raw_drop_data[i] == "{":
            end = raw_drop_data.find("}", i)
            if end == -1:
                paths.append(raw_drop_data[i + 1:])
                break
            paths.append(raw_drop_data[i + 1:end])
            i = end + 1
        else:
            end = raw_drop_data.find(" ", i)
            if end == -1:
                paths.append(raw_drop_data[i:])
                break
            paths.append(raw_drop_data[i:end])
            i = end
    return paths


def validate_scan_request(company_code, selected_passwords, selected_files):
    """
    Shared validation for both 'Run Now' and 'Queue for Watcher' buttons on
    the Scan tab, and 'Extract Headers' on the Header Scan tab (which doesn't
    require selected_passwords to be non-empty -- header extraction can run
    against unencrypted files too; use validate_scan_request_with_password
    for the flows that do require at least one password).
    Returns a list of problem strings; empty list means valid.
    """
    problems = []
    if not company_code or not company_code.strip():
        problems.append("Select a company code.")
    if not selected_files:
        problems.append("Select at least one file.")
    return problems


def validate_scan_request_with_password(company_code, selected_passwords, selected_files):
    problems = validate_scan_request(company_code, selected_passwords, selected_files)
    if not selected_passwords:
        problems.append("Select at least one password (or add one if this company has none yet).")
    return problems
