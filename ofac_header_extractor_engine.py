"""
ofac_header_extractor_engine.py
The "Extract Headers" tab's backend: scans a batch of files and reports
every column's header text, position, and a best-guess content category
(Name, Sex, DOB, PolicyNumber, Numeric, Date, Identifier, Text, Empty,
Unknown) -- used for onboarding a new company (figuring out what synonyms to
add to its header JSON) before it can be scanned for real.

Deliberately reuses ofac_header_detection's table-block detection and
categorise_column_content rather than a second implementation -- this is the
fix for the exact duplication flagged in the original v2 review, where
header_extractor_core.py and ofac_scanner_core.py each had their own,
independently-maintained "find contiguous non-empty column blocks" logic.

TEST COVERAGE NOTE: same situation as the other polars-dependent files.
Everything this calls into (detect_table_blocks, detect_header_row_for_block,
categorise_column_content) is already unit-tested in
test_header_detection.py. This file's own job -- iterating columns and
assembling records -- is mechanical. Run test_header_extractor_engine.py on
a machine with polars before trusting it in production.
"""

import os

import polars as pl

from ofac_constants import MAX_SEARCH_ROWS, FILE_EXTENSIONS_EXCEL, FILE_EXTENSIONS_TEXT
import ofac_header_detection as detection
from ofac_scanner_engine import unlock_excel_file  # reuse, not reimplement
from ofac_file_utils import detect_encoding_and_dialect


def extract_headers_from_dataframe(df, file_path, sheet_name, max_search_rows=MAX_SEARCH_ROWS):
    """
    Returns a list of dicts, one per detected header cell:
      {Header, File Path, Sheet Name, Table, Column Index, Row Index, Category}
    """
    sample_rows = df.head(min(df.height, max_search_rows)).rows()
    blocks = detection.detect_table_blocks(sample_rows, df.width, max_rows=max_search_rows)
    if not blocks:
        return []

    records = []
    for table_idx, (col_start, col_end) in enumerate(blocks, start=1):
        header_row_idx, header_values = detection.detect_header_row_for_block(
            sample_rows, col_start, col_end, max_rows=max_search_rows
        )
        if header_row_idx is None:
            continue

        data_start = header_row_idx + 1
        for offset, header_text in enumerate(header_values):
            col_idx = col_start + offset
            col_name = df.columns[col_idx]
            column_data = df.slice(data_start)[col_name].to_list()
            category = detection.categorise_column_content(column_data)
            records.append({
                "Header": header_text,
                "File Path": file_path,
                "Sheet Name": sheet_name,
                "Table": f"Table {table_idx}",
                "Column Index": col_idx,
                "Row Index": header_row_idx,
                "Category": category,
            })

    return records


def process_excel_file_for_headers(file_path, file_name, password_entries):
    try:
        readable, _label = unlock_excel_file(file_path, password_entries)
    except ValueError:
        return [], f"Could not decrypt {file_name} with any provided password"

    try:
        sheets = pl.read_excel(readable, has_header=False, sheet_id=0, raise_if_empty=False)
    except Exception as e:
        return [], f"Failed to read {file_name}: {e}"

    all_records = []
    for sheet_name, df in sheets.items():
        if df.is_empty():
            continue
        all_records.extend(extract_headers_from_dataframe(df, file_path, sheet_name))

    return all_records, None


def process_text_file_for_headers(file_path, file_name):
    try:
        encoding, delimiter, quotechar = detect_encoding_and_dialect(file_path)
        df = pl.read_csv(file_path, has_header=False, encoding=encoding, separator=delimiter,
                          quote_char=quotechar, truncate_ragged_lines=True)
    except Exception as e:
        return [], f"Failed to read {file_name}: {e}"

    if df.is_empty():
        return [], None

    return extract_headers_from_dataframe(df, file_path, ""), None


def run_header_extraction(file_paths, password_entries, progress_callback=None):
    """
    file_paths: list of full paths to Excel/text files (archives should
    already be extracted by the caller -- this function doesn't recurse
    into archives itself, keeping it focused on the header-reading part).

    Returns (all_records, errors) where errors is a list of
    {file, message} dicts for files that couldn't be read at all.
    """
    all_records = []
    errors = []

    for idx, file_path in enumerate(file_paths):
        file_name = os.path.basename(file_path)
        if progress_callback:
            progress_callback(idx + 1, len(file_paths), file_name)

        ext = os.path.splitext(file_name)[1].lower().lstrip(".")
        if ext in FILE_EXTENSIONS_EXCEL:
            records, error = process_excel_file_for_headers(file_path, file_name, password_entries)
        elif ext in FILE_EXTENSIONS_TEXT:
            records, error = process_text_file_for_headers(file_path, file_name)
        else:
            continue

        all_records.extend(records)
        if error:
            errors.append({"file": file_name, "message": error})

    return all_records, errors


def write_header_report(records, output_path):
    """
    Writes the collected header records to an Excel file, sorted for
    readability (by file, then sheet, then column position). Atomic write,
    same pattern as the compiler.
    """
    if not records:
        pl.DataFrame(schema={
            "Header": pl.Utf8, "File Path": pl.Utf8, "Sheet Name": pl.Utf8,
            "Table": pl.Utf8, "Column Index": pl.Int64, "Row Index": pl.Int64, "Category": pl.Utf8,
        }).write_excel(output_path)
        return

    df = pl.DataFrame(records)
    df = df.sort(["File Path", "Sheet Name", "Table", "Column Index"])
    tmp_path = output_path + ".tmp"
    df.write_excel(tmp_path)
    os.replace(tmp_path, output_path)
