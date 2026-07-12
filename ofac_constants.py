"""
ofac_constants.py
Shared constants for the OFAC Scanner application: folder layout, supported
file types, processing thresholds, and the extraction output schema.

Every other module imports paths and limits from here instead of hardcoding
them, so there is exactly one place to change if a threshold or location
needs to move.
"""

import os

# ==================== APP FOLDER LAYOUT ====================
# Root folder for the whole app -- defaults to a folder right next to this
# file (i.e. inside the code folder), the same convention parse_headers.py
# and migrate_passwords_to_vault.py already use for their own outputs. This
# makes the app self-contained: copy the whole code folder somewhere else
# and your config/database/output come with it.
#
# Override with OFAC_APP_ROOT if you'd rather keep data separate from code
# (e.g. so reinstalling/replacing the code folder never touches your data,
# or to match a more traditional per-user-profile convention) -- both are
# valid choices, this default just optimizes for "everything in one place"
# since that's what most people expect from a self-contained tool.
APP_ROOT = os.environ.get(
    "OFAC_APP_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "OFAC_App"),
)

CONFIG_FOLDER = os.path.join(APP_ROOT, "config")

HEADERS_FOLDER = os.path.join(CONFIG_FOLDER, "headers")
HEADERS_DEFAULTS_FILE = os.path.join(HEADERS_FOLDER, "defaults.json")
HEADERS_COMPANIES_FOLDER = os.path.join(HEADERS_FOLDER, "companies")

PASSWORDS_FOLDER = os.path.join(CONFIG_FOLDER, "passwords")
PASSWORDS_COMPANIES_FOLDER = os.path.join(PASSWORDS_FOLDER, "companies")

APP_SETTINGS_FILE = os.path.join(CONFIG_FOLDER, "app_settings.json")

DATA_FOLDER = os.path.join(APP_ROOT, "data")
DATABASE_PATH = os.path.join(DATA_FOLDER, "ofac_runs.db")

OUTPUT_ROOT = os.path.join(APP_ROOT, "output")

SEVEN_ZIP_PATH = os.environ.get("SEVEN_ZIP_PATH", r"C:\Program Files\7-zip\7z.exe")


def ensure_app_folders():
    """Create every folder the app needs on disk, if missing. Call once at startup."""
    for folder in [
        APP_ROOT, CONFIG_FOLDER, HEADERS_FOLDER, HEADERS_COMPANIES_FOLDER,
        PASSWORDS_FOLDER, PASSWORDS_COMPANIES_FOLDER, DATA_FOLDER, OUTPUT_ROOT,
    ]:
        os.makedirs(folder, exist_ok=True)


def company_output_folder(email_received_date_display, company_code, output_root=None):
    """
    Standard per-run output location: <output_root>/<YYYYMMDD>/<COMPANY_CODE>/
    email_received_date_display must already be formatted as YYYYMMDD.

    output_root defaults to OUTPUT_ROOT (APP_ROOT/output) if not given, but
    callers that care about the user's configured output location should
    pass ofac_settings.get_output_root() explicitly -- see ofac_settings.py
    for why this is a user setting rather than a fixed constant.
    """
    root = output_root if output_root else OUTPUT_ROOT
    return os.path.join(root, email_received_date_display, company_code)


# ==================== WINDOW TITLES ====================
# Single source of truth -- both ofac_main.py (instance_check_or_focus) and
# ofac_gui_main.py (the windows themselves) import these, so they can never
# drift out of sync with each other.
SETUP_WINDOW_TITLE = "OFAC Scanner Setup"
SCANNER_WINDOW_TITLE = "OFAC Scanner"


# ==================== SUPPORTED FILE TYPES ====================
FILE_EXTENSIONS_EXCEL = ["xlsx", "xls", "xlsm", "xlsb"]
FILE_EXTENSIONS_TEXT = ["csv", "txt", "rpt"]
FILE_EXTENSIONS_ARCHIVE = ["zip", "zipx", "tar", "7z", "rar"]
SUPPORTED_FILE_TYPES = FILE_EXTENSIONS_EXCEL + FILE_EXTENSIONS_TEXT + FILE_EXTENSIONS_ARCHIVE

# ==================== PROCESSING THRESHOLDS ====================
EXCEL_MAX_ROWS = 1_000_000                 # hard Excel row limit (compiled report split point)
MAX_ROWS_PER_OUTPUT_CSV = 500_000          # per-file/sheet output CSV split point

TEXT_SIZE_TO_CHUNK = 100 * 1024 * 1024     # text files above this size are read in batches
EXCEL_SIZE_TO_CHUNK = 200 * 1024 * 1024    # Excel files above this size are read in batches
CHUNK_ROWS = 10_000                        # rows per batch when chunking either format

MAX_SEARCH_ROWS = 50                       # rows scanned when looking for a header row

# ==================== HEADER SYNONYM CATEGORIES ====================
# The five fields every header-synonym file (defaults.json + per-company overrides) may define.
HEADER_FIELD_KEYS = ["name", "firstlastname", "sex", "dob", "policynum"]

# ==================== EXTRACTION OUTPUT SCHEMA ====================
OUTPUT_COLUMNS = [
    "SURNAME", "FIRST_NAME", "COMPLETE_NAME", "SEX", "DATE_OF_BIRTH",
    "CMPY_NO", "POLICY_NUMBER", "FILE_PATH", "SHEET",
]
