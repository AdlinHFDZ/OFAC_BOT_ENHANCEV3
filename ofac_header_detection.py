"""
ofac_header_detection.py
Pure-Python detection logic: given the raw rows of a sheet/file (as plain
Python lists, no DataFrame needed), figure out which row is the header row
and which columns are name / first-last / sex / dob / policy-number.

Deliberately dependency-free (no polars) so this -- the part of the pipeline
most prone to subtle bugs -- can be fully unit-tested in isolation. The
polars-dependent layer (ofac_extraction_engine.py) calls into this module for
all detection decisions and only uses polars for the mechanical data-pulling
once detection is already settled.

Bug fix from the code review baked in here: v2's table-block detection only
checked the first 10 rows of a sheet to decide whether a column had any data,
which silently dropped columns whose data started later (common when a file
has title/banner rows before the real header). Every function here takes the
search-depth as an explicit parameter -- there is no hidden, smaller default
that can quietly under-scan again.
"""

import re
import difflib

from ofac_constants import MAX_SEARCH_ROWS


def clean_for_match(text):
    """Lowercase, strip everything except letters. Used to compare a raw
    header cell against the header-synonym library."""
    if text is None:
        return ""
    return re.sub(r"[^a-z]", "", str(text).lower())


def is_empty_cell(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


# ==================== TABLE / COLUMN BLOCK DETECTION ====================

def find_non_empty_columns(rows, num_columns, max_rows):
    """
    rows: list of row-tuples (each a sequence of cell values), already
          limited to the sheet/chunk being searched.
    num_columns: total column count of the sheet (some rows may be shorter;
          missing cells are treated as empty).
    max_rows: how many rows to check for "does this column have any data".
          Callers should pass MAX_SEARCH_ROWS, not an arbitrary smaller
          number -- see module docstring for why this matters.

    Returns a sorted list of column indices that have at least one non-empty
    value somewhere in the first max_rows rows.
    """
    rows_to_check = rows[:max_rows]
    non_empty = set()
    for row in rows_to_check:
        for col_idx in range(num_columns):
            value = row[col_idx] if col_idx < len(row) else None
            if not is_empty_cell(value):
                non_empty.add(col_idx)
    return sorted(non_empty)


def group_into_column_blocks(non_empty_columns):
    """
    Given a sorted list of column indices with data, group adjacent indices
    into contiguous (start, end) blocks. A gap of empty columns starts a new
    block -- this is how multiple side-by-side tables on one sheet get
    separated from each other.
    """
    if not non_empty_columns:
        return []

    blocks = []
    start = prev = non_empty_columns[0]
    for col in non_empty_columns[1:]:
        if col > prev + 1:
            blocks.append((start, prev))
            start = col
        prev = col
    blocks.append((start, prev))
    return blocks


def detect_table_blocks(rows, num_columns, max_rows=MAX_SEARCH_ROWS):
    """
    Top-level entry point: find every distinct table block on a sheet.
    Returns a list of (col_start, col_end) tuples. Most sheets have exactly
    one block covering every column; multi-table sheets (two unrelated
    tables side by side) produce more than one.
    """
    non_empty = find_non_empty_columns(rows, num_columns, max_rows)
    return group_into_column_blocks(non_empty)


# ==================== EXACT HEADER-ROW MATCHING ====================

def detect_header_row_exact(rows, col_start, col_end, header_sets, max_rows=MAX_SEARCH_ROWS):
    """
    Scan rows[0:max_rows] within columns [col_start, col_end] for a row where
    at least one cell exactly matches (after cleaning) a known 'name' or
    'firstlastname' synonym. header_sets is the merged, already-normalized
    {field: set_of_normalized_aliases} from ofac_header_config.

    Returns a dict describing the match, or None if nothing matched:
      {
        "header_row_idx": int,
        "columns": {field: [col_idx, ...]},   # for every field in header_sets
        "raw_header_values": [...],           # the actual cell values on that row
      }
    """
    for row_idx, row in enumerate(rows[:max_rows]):
        row_slice = row[col_start:col_end + 1]
        cleaned_to_indices = {}
        for offset, value in enumerate(row_slice):
            cleaned = clean_for_match(value)
            if cleaned:
                cleaned_to_indices.setdefault(cleaned, []).append(offset)

        cleaned_set = set(cleaned_to_indices.keys())
        name_hit = header_sets.get("name", set()) & cleaned_set
        firstlast_hit = header_sets.get("firstlastname", set()) & cleaned_set

        if not name_hit and not firstlast_hit:
            continue

        columns = {}
        for field, alias_set in header_sets.items():
            matched_cleaned = alias_set & cleaned_set
            indices = []
            for cleaned in matched_cleaned:
                indices.extend(cleaned_to_indices[cleaned])
            columns[field] = sorted(col_start + i for i in indices)

        return {
            "header_row_idx": row_idx,
            "columns": columns,
            "raw_header_values": list(row_slice),
        }

    return None


# ==================== FUZZY HEADER-ROW MATCHING (fallback) ====================

def fuzzy_match_word(word, candidates, threshold=0.7):
    for candidate in candidates:
        if difflib.SequenceMatcher(None, word, candidate).ratio() >= threshold:
            return True
    return False


def detect_header_row_fuzzy(rows, col_start, col_end, header_sets, max_rows=MAX_SEARCH_ROWS, threshold=0.7):
    """
    Only called after detect_header_row_exact returns None. Same shape of
    result. Slower (SequenceMatcher per cell per candidate) -- that cost is
    acceptable because it only runs on the minority of files where exact
    matching failed.
    """
    for row_idx, row in enumerate(rows[:max_rows]):
        row_slice = row[col_start:col_end + 1]
        columns = {field: [] for field in header_sets}

        for offset, value in enumerate(row_slice):
            cleaned = clean_for_match(value)
            if not cleaned:
                continue
            for field, alias_set in header_sets.items():
                if fuzzy_match_word(cleaned, alias_set, threshold=threshold):
                    columns[field].append(col_start + offset)

        if columns.get("name") or columns.get("firstlastname"):
            return {
                "header_row_idx": row_idx,
                "columns": columns,
                "raw_header_values": list(row_slice),
            }

    return None


def detect_header_row(rows, col_start, col_end, header_sets, max_rows=MAX_SEARCH_ROWS):
    """Try exact matching first, fall back to fuzzy only if exact finds nothing."""
    result = detect_header_row_exact(rows, col_start, col_end, header_sets, max_rows=max_rows)
    if result is not None:
        return result
    return detect_header_row_fuzzy(rows, col_start, col_end, header_sets, max_rows=max_rows)


# ==================== CONTENT-BASED FALLBACK (no header row matched at all) ====================

_SEX_VALUES = {"m", "f", "male", "female"}
_POLICY_PATTERN = re.compile(r"^[A-Za-z0-9\-./]{6,30}$")
_NAME_PATTERN = re.compile(r"^[A-Za-z\u00C0-\u00FF'\-\. ]{2,50}$")
MIN_SAMPLE_FOR_NAME_INFERENCE = 5  # below this, there isn't enough data to trust a uniqueness check


def parse_date_loose(value):
    """Lightweight date-parse check used only for content-type inference (not
    for the real DOB parsing step -- but shares the same plausibility guard
    via ofac_data_cleaning, so a bare number like "123" isn't misread as a
    date here either). Returns True/False."""
    if value is None:
        return False
    if hasattr(value, "year") and hasattr(value, "month"):  # datetime/date-like
        return True
    import ofac_data_cleaning as cleaning
    return cleaning.parse_date_to_mmddyyyy(value) != ""


def infer_column_type_by_content(column_values, sample_size=200):
    """
    column_values: list of raw cell values from one column (data rows only,
    not the header). Returns one of "name", "sex", "dob", "policynum", or ""
    if nothing matched confidently.
    """
    sample = [v for v in column_values[:sample_size] if not is_empty_cell(v)]
    if not sample:
        return ""

    str_vals = [str(v).strip() for v in sample if str(v).strip() != ""]
    if not str_vals:
        return ""

    lower_vals = [v.lower() for v in str_vals]
    sex_ratio = sum(1 for v in lower_vals if v in _SEX_VALUES) / len(lower_vals)
    if sex_ratio > 0.7:
        return "sex"

    date_ratio = sum(1 for v in str_vals if parse_date_loose(v)) / len(str_vals)
    if date_ratio > 0.7:
        return "dob"

    policy_ratio = sum(1 for v in str_vals if _POLICY_PATTERN.match(v)) / len(str_vals)
    if policy_ratio > 0.7:
        return "policynum"

    name_ratio = sum(1 for v in str_vals if _NAME_PATTERN.match(v)) / len(str_vals)
    if name_ratio > 0.8:
        # Letters-and-spaces text alone isn't a strong enough signal on its
        # own -- short business labels ("Premium", "Reinsurance Share") match
        # the same pattern as real names. Real name lists are near-unique
        # (screening a list of distinct people); a column that repeats the
        # same handful of values is much more likely a category/label column.
        # Only trust the name classification once there's a reasonable
        # sample AND meaningful diversity in it.
        if len(str_vals) < MIN_SAMPLE_FOR_NAME_INFERENCE:
            return ""
        unique_ratio = len(set(str_vals)) / len(str_vals)
        if unique_ratio > 0.5:
            return "name"
        return ""

    return ""


def detect_columns_by_content(rows, num_columns, header_row_idx=-1, sample_size=200):
    """
    Fallback used when no header row matched at all (by exact or fuzzy
    synonym matching). Looks at what the data in each column actually looks
    like. data starts the row after header_row_idx (-1 means no header row
    was ever identified, so all rows are data).

    Returns a dict shaped like detect_header_row's "columns" field.
    """
    data_start = header_row_idx + 1
    data_rows = rows[data_start:data_start + sample_size]

    columns = {"name": [], "firstlastname": [], "sex": [], "dob": [], "policynum": []}
    name_columns = []

    for col_idx in range(num_columns):
        col_values = [row[col_idx] if col_idx < len(row) else None for row in data_rows]
        col_type = infer_column_type_by_content(col_values)
        if col_type == "name":
            name_columns.append(col_idx)
        elif col_type in columns:
            columns[col_type].append(col_idx)

    # If we found two or more name-shaped columns, treat the first two as a
    # first/last pair rather than two independent "complete name" columns --
    # mirrors the header-matched multiple-name-column handling.
    if len(name_columns) >= 2:
        columns["firstlastname"] = name_columns[:2]
        columns["name"] = name_columns[2:]
    else:
        columns["name"] = name_columns

    return columns


# ==================== TOP-LEVEL ORCHESTRATION ====================

def detect_all(rows, num_columns, header_sets, max_search_rows=MAX_SEARCH_ROWS):
    """
    Full detection pipeline for one sheet/file:
      1. Find table blocks (handles side-by-side multi-table sheets).
      2. For each block, try exact then fuzzy header-row matching.
      3. If NO block produced a name or firstlastname match anywhere,
         fall through to whole-sheet content-based detection -- this is
         the fix for the "partial match silently suppresses a better
         fallback" issue from the review: a block match only counts as
         a real match if it actually found a name-ish column, not just
         because *some* row scored non-empty.

    Returns a list of per-table match dicts (possibly from the content-based
    fallback, in which case it's a single synthetic "block" covering the
    whole sheet with header_row_idx = -1).
    """
    blocks = detect_table_blocks(rows, num_columns, max_rows=max_search_rows)
    if not blocks:
        blocks = [(0, num_columns - 1)]

    results = []
    for col_start, col_end in blocks:
        match = detect_header_row(rows, col_start, col_end, header_sets, max_rows=max_search_rows)
        if match and (match["columns"].get("name") or match["columns"].get("firstlastname")):
            match["col_start"] = col_start
            match["col_end"] = col_end
            results.append(match)

    if results:
        return results

    # Nothing usable found in any block -- fall through to content-based
    # detection over the whole sheet, not just the (possibly wrong) blocks.
    columns = detect_columns_by_content(rows, num_columns)
    if columns.get("name") or columns.get("firstlastname"):
        return [{
            "header_row_idx": -1,
            "columns": columns,
            "raw_header_values": [],
            "col_start": 0,
            "col_end": num_columns - 1,
            "content_based": True,
        }]

    return []


# ==================== HEADER-EXTRACTION TOOL SUPPORT ====================
# Used by ofac_header_extractor_engine.py (the "Extract Headers" tab's
# company-onboarding tool) -- reuses detect_table_blocks above rather than
# a separate implementation, avoiding the exact duplication flagged in the
# original v2 review (find_table_blocks vs detect_tables_in_sheet as two
# independently-maintained implementations of the same idea).

_EXTRACTION_NUMERIC_PATTERN = re.compile(r"^-?\d+(\.\d+)?$")
_EXTRACTION_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9\-_]{4,20}$")
_EXTRACTION_TEXT_PATTERN = re.compile(r"^[A-Za-z\u00C0-\u00FF'\-\.\s]{2,}$")


def detect_header_row_for_block(rows, col_start, col_end, max_rows=MAX_SEARCH_ROWS):
    """
    For the header-extraction tool (not the scanner): pick the row within
    [0, max_rows) that has the most non-empty cells in [col_start, col_end]
    -- a simple, permissive heuristic appropriate for "show me what headers
    this file has", as opposed to the scanner's stricter synonym-matching.
    Returns (row_idx, [header_values]) or (None, []) if every row is empty.
    """
    best_row_idx, best_values, best_score = None, [], -1
    for row_idx, row in enumerate(rows[:max_rows]):
        row_slice = row[col_start:col_end + 1]
        non_empty = [str(v).strip() for v in row_slice if not is_empty_cell(v)]
        if len(non_empty) > best_score:
            best_score = len(non_empty)
            best_row_idx = row_idx
            best_values = non_empty
    if best_row_idx is not None and best_values:
        return best_row_idx, best_values
    return None, []


def categorise_column_content(column_values, sample_size=200):
    """
    Broader categorization than infer_column_type_by_content -- used for the
    header-extraction report, which wants to describe *every* column
    (Numeric, Date, Identifier, Text, Empty, Unknown), not just the five
    OFAC-relevant fields. Tries the OFAC-specific categories first (with the
    same uniqueness-guarded name check), then falls back to more generic
    shape-based categories.
    """
    ofac_type = infer_column_type_by_content(column_values, sample_size=sample_size)
    if ofac_type == "sex":
        return "Sex"
    if ofac_type == "dob":
        return "DOB"
    if ofac_type == "policynum":
        return "PolicyNumber"
    if ofac_type == "name":
        return "Name"

    sample = [v for v in column_values[:sample_size] if not is_empty_cell(v)]
    if not sample:
        return "Empty"
    str_vals = [str(v).strip() for v in sample if str(v).strip() != ""]
    if not str_vals:
        return "Empty"

    numeric_ratio = sum(1 for v in str_vals if _EXTRACTION_NUMERIC_PATTERN.match(v)) / len(str_vals)
    if numeric_ratio > 0.9:
        return "Numeric"

    date_ratio = sum(1 for v in str_vals if parse_date_loose(v)) / len(str_vals)
    if date_ratio > 0.7:
        return "Date"

    identifier_ratio = sum(1 for v in str_vals if _EXTRACTION_IDENTIFIER_PATTERN.match(v)) / len(str_vals)
    if identifier_ratio > 0.7:
        return "Identifier"

    text_ratio = sum(1 for v in str_vals if _EXTRACTION_TEXT_PATTERN.match(v)) / len(str_vals)
    if text_ratio > 0.8:
        return "Text"

    return "Unknown"
