"""
ofac_data_cleaning.py
Pure-Python value-cleaning functions: name text cleanup, sex normalization,
and date parsing. No polars dependency -- these get wrapped in polars
expressions by ofac_extraction_engine.py, but the logic itself is tested
here in isolation, the same way ofac_header_detection.py is.
"""

import re
from datetime import datetime
from dateutil import parser as dateutil_parser


# ==================== NAME CLEANING ====================

_NON_LETTER_OR_SPACE = re.compile(r"[^A-Za-z\s]")
_MULTI_SPACE = re.compile(r"\s+")


def clean_name_text(value):
    """
    Strip everything except letters and spaces, collapse repeated whitespace,
    and drop a trailing/embedded "DECEASED" marker some source files append
    to a name field. Returns "" for None/empty input.
    """
    if value is None:
        return ""
    text = str(value).upper()
    text = _NON_LETTER_OR_SPACE.sub(" ", text)
    words = [w for w in text.split() if w != "DECEASED"]
    return " ".join(words)


def contains_digit(value):
    if value is None:
        return False
    return any(ch.isdigit() for ch in str(value))


def is_numeric_like(value):
    """True if a single value looks like a bare number (used to help decide
    whether a candidate name/firstlastname column is actually an ID column)."""
    if value is None:
        return False
    return bool(re.match(r"^\d+$", str(value).strip()))


# ==================== SEX NORMALIZATION ====================

def normalize_sex(value):
    if value is None or str(value).strip() == "":
        return ""
    v = str(value).strip().lower()
    if v in ("male", "m"):
        return "M"
    if v in ("female", "f"):
        return "F"
    return v.upper()


# ==================== DATE PARSING ====================

_FALLBACK_DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
    "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %b %y",
    "%b-%d-%Y", "%b-%d-%y", "%b %d, %Y", "%b %d %Y",
    "%d-%B-%Y", "%d-%B-%y", "%d %B %Y", "%d %B %y",
    "%B %d, %Y", "%B %d %Y",
    "%Y-%b-%d", "%Y %b %d", "%Y-%B-%d", "%Y %B %d",
    "%y-%m-%d", "%y/%m/%d", "%d/%m/%y", "%m/%d/%y",
    "%d-%m-%y", "%m-%d-%y", "%d.%m.%y", "%m.%d.%y",
    "%Y%m%d", "%d%m%Y", "%m%d%Y",
]


_DATE_SEPARATOR_PATTERN = re.compile(r"[-/.\s]")


def _looks_like_a_date(s):
    """
    Plausibility gate before attempting ANY parse. Without this, dateutil
    happily interprets bare short numbers as dates by filling in the
    missing year/month/day from *today's* date -- e.g. parse_date_to_mmddyyyy
    used to turn "123" into "07/11/123" and "5" into today's date with
    day=5. Neither is a real date; both are dateutil guessing.

    A string is allowed through to the real parser only if it:
      - contains a letter (month names etc. -- "15 Jan 1990" needs the full parser), or
      - contains a typical date separator (-, /, ., or whitespace), or
      - is exactly 8 bare digits (YYYYMMDD / DDMMYYYY / MMDDYYYY -- matches
        the explicit formats already in the fallback list below).
    Anything else (bare 1-7 or 9+ digit numbers with no separator) is
    rejected before it ever reaches dateutil.
    """
    if any(ch.isalpha() for ch in s):
        return True
    if _DATE_SEPARATOR_PATTERN.search(s):
        return True
    if s.isdigit() and len(s) == 8:
        return True
    return False


def parse_date_to_mmddyyyy(value):
    """
    Best-effort date parse, returns 'mm/dd/yyyy' or '' if unparseable.
    Tries dateutil's general parser first (handles most real-world formats),
    then an explicit fallback list for edge cases dateutil gets wrong or
    rejects (e.g. bare 'YYYYMMDD' digit strings, which dateutil often
    misreads as something else or refuses outright). Guarded by
    _looks_like_a_date first -- see that function's docstring for why.
    """
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%m/%d/%Y")
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        # date-like object (e.g. polars/python date) without being a datetime
        try:
            return datetime(value.year, value.month, value.day).strftime("%m/%d/%Y")
        except (ValueError, TypeError):
            pass

    s = str(value).strip()
    if not s or not _looks_like_a_date(s):
        return ""

    try:
        dt = dateutil_parser.parse(s, fuzzy=False)
        return dt.strftime("%m/%d/%Y")
    except (ValueError, TypeError, OverflowError):
        pass
    except Exception:
        pass  # dateutil.parser.ParserError subclasses ValueError, this is a defensive catch-all

    for fmt in _FALLBACK_DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%m/%d/%Y")
        except ValueError:
            continue

    return ""
