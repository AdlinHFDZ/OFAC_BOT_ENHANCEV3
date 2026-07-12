"""
ofac_extraction_engine.py
The polars-dependent layer: given a raw DataFrame (no header) and a header-
synonym set for a company, detects the header row/columns (via
ofac_header_detection, already unit-tested without polars) and builds the
final OUTPUT_COLUMNS DataFrame, cleaning values via ofac_data_cleaning
(also already unit-tested).

IMPORTANT -- test coverage note:
This file could not be executed in the environment it was written in (no
network access to install polars). Every non-trivial piece of *logic* it
depends on (header/column detection, name cleaning, date parsing, sex
normalization) is fully unit-tested in ofac_header_detection.py and
ofac_data_cleaning.py -- this file's job is comparatively mechanical: call
those tested functions and assemble a DataFrame with polars' documented
API. Still, run test_extraction_engine.py (included) on a machine with
polars installed before trusting this in production. That test file is
ready to run as-is; it just couldn't be run here.

Deliberate perf/correctness tradeoff, documented rather than hidden: name
cleaning, sex normalization, and date parsing are applied via
`pl.col(...).map_elements(...)` calling the tested pure-Python functions,
not hand-vectorized polars string expressions. map_elements is slower
(a Python function call per value) but guarantees the behavior matches what
was actually tested. If profiling on real large files shows this is a
throughput bottleneck, clean_name_text specifically can be vectorized as:
    pl.col(c).cast(pl.Utf8).str.to_uppercase()
      .str.replace_all(r"[^A-Z\\s]", " ")
      .str.replace_all(r"\\bDECEASED\\b", "")
      .str.replace_all(r"\\s+", " ").str.strip_chars()
-- but only after adding a differential test proving it produces identical
output to ofac_data_cleaning.clean_name_text on a representative sample,
so the swap doesn't quietly reintroduce a behavior mismatch.
"""

import polars as pl

from ofac_constants import OUTPUT_COLUMNS, MAX_SEARCH_ROWS
import ofac_header_detection as detection
import ofac_data_cleaning as cleaning


NUMERIC_COLUMN_THRESHOLD = 0.9   # fraction of sampled values that must look numeric to exclude a column
NUMERIC_SAMPLE_SIZE = 100


def _column_name(df, col_idx):
    return df.columns[col_idx]


def _is_column_mostly_numeric(df, col_idx, data_start_row, threshold=NUMERIC_COLUMN_THRESHOLD):
    """
    Sample a candidate name/firstlastname column and check whether it's
    actually numeric-looking data (e.g. a policy or ID column that
    coincidentally matched a name synonym). Uses the tested is_numeric_like
    per value; the sampling/aggregation here is mechanical.
    """
    col_name = _column_name(df, col_idx)
    sample = (
        df.slice(data_start_row)
        .select(pl.col(col_name).cast(pl.Utf8))
        .head(NUMERIC_SAMPLE_SIZE)
        .to_series()
        .drop_nulls()
        .to_list()
    )
    if not sample:
        return False
    numeric_count = sum(1 for v in sample if cleaning.is_numeric_like(v))
    return (numeric_count / len(sample)) >= threshold


def _filter_numeric_columns(df, col_indices, data_start_row):
    return [
        idx for idx in col_indices
        if not _is_column_mostly_numeric(df, idx, data_start_row)
    ]


def _clean_name_column_expr(col_name):
    return (
        pl.col(col_name)
        .map_elements(cleaning.clean_name_text, return_dtype=pl.Utf8)
    )


def _sex_column_expr(col_name):
    return pl.col(col_name).map_elements(cleaning.normalize_sex, return_dtype=pl.Utf8)


def _dob_column_expr(col_name):
    return pl.col(col_name).map_elements(cleaning.parse_date_to_mmddyyyy, return_dtype=pl.Utf8)


def _finalize_complete_name(result_df, digit_check_col=None):
    """
    COMPLETE_NAME = COMPLETE_NAME_RAW if non-empty, else SURNAME + FIRST_NAME.

    Safety net: if the ORIGINAL, uncleaned source text for the name column
    contained a digit (garbage data -- e.g. a policy number that leaked into
    a name column), fall back to SURNAME + FIRST_NAME instead.

    digit_check_col, if given, is the name of an *uncleaned* column to check
    for digits -- NOT COMPLETE_NAME itself. Checking COMPLETE_NAME here would
    never find anything: by the time this runs, COMPLETE_NAME has already
    been through clean_name_text, which strips digits as part of cleaning.
    "P123456" becomes "P" during cleaning, and "P" contains no digit -- so a
    check against the cleaned value can never trigger, regardless of what the
    original data looked like. This is why digit_check_col must be the raw,
    unmodified source text instead.

    Only _build_standard passes digit_check_col: it's the only code path
    with a meaningful independent SURNAME/FIRST_NAME to fall back to. The
    explode paths (_explode_complete_names, _explode_name_pairs) don't pass
    it and get no digit-safety-net -- their SURNAME/FIRST_NAME are either
    null or reconstructed from the same source, so there's no useful
    fallback for them to fall back to.
    """
    result_df = result_df.with_columns(
        pl.when(pl.col("COMPLETE_NAME_RAW").is_not_null() & (pl.col("COMPLETE_NAME_RAW") != ""))
        .then(pl.col("COMPLETE_NAME_RAW"))
        .otherwise(
            pl.concat_str([pl.col("SURNAME"), pl.col("FIRST_NAME")], separator=" ").str.strip_chars()
        )
        .alias("COMPLETE_NAME")
    )

    if digit_check_col is not None and digit_check_col in result_df.columns:
        result_df = result_df.with_columns(
            pl.when(pl.col(digit_check_col).str.contains(r"\d"))
            .then(pl.concat_str([pl.col("SURNAME"), pl.col("FIRST_NAME")], separator=" ").str.strip_chars())
            .otherwise(pl.col("COMPLETE_NAME"))
            .alias("COMPLETE_NAME")
        )
        result_df = result_df.drop(digit_check_col)

    return result_df


def _explode_complete_names(data_df, name_col_names, policy_col_name, company_code, file_path, sheet_name):
    """Multiple name columns each holding one full name -> one output row per name."""
    clean_exprs = [_clean_name_column_expr(c) for c in name_col_names]
    df_with_names = data_df.select(
        pl.concat_list(clean_exprs).list.eval(pl.element().filter(pl.element() != "")).alias("names_list"),
        pl.all().exclude(name_col_names),
    )
    df_multi = df_with_names.filter(pl.col("names_list").list.len() > 1).explode("names_list")
    if df_multi.is_empty():
        return None

    result = df_multi.select([
        pl.lit(None, dtype=pl.Utf8).alias("SURNAME"),
        pl.lit(None, dtype=pl.Utf8).alias("FIRST_NAME"),
        pl.col("names_list").alias("COMPLETE_NAME_RAW"),
        pl.lit("U").alias("SEX"),
        pl.lit("").alias("DATE_OF_BIRTH"),
        pl.lit(company_code).alias("CMPY_NO"),
        (pl.col(policy_col_name).cast(pl.Utf8) if policy_col_name else pl.lit(None, dtype=pl.Utf8)).alias("POLICY_NUMBER"),
        pl.lit(file_path).alias("FILE_PATH"),
        pl.lit(sheet_name).alias("SHEET"),
    ])
    return _finalize_complete_name(result)


def _explode_name_pairs(data_df, firstlast_col_names, policy_col_name, company_code, file_path, sheet_name):
    """More than one surname/firstname pair on the same row (e.g. joint life
    policies) -> one output row per pair."""
    pair_frames = []
    for i in range(0, len(firstlast_col_names) - 1, 2):
        surname_col, firstname_col = firstlast_col_names[i], firstlast_col_names[i + 1]
        pair = data_df.select([
            _clean_name_column_expr(surname_col).alias("SURNAME"),
            _clean_name_column_expr(firstname_col).alias("FIRST_NAME"),
            (pl.col(policy_col_name).cast(pl.Utf8) if policy_col_name else pl.lit(None, dtype=pl.Utf8)).alias("POLICY_NUMBER"),
        ]).filter((pl.col("SURNAME") != "") | (pl.col("FIRST_NAME") != ""))
        pair_frames.append(pair)

    if not pair_frames:
        return None
    combined = pl.concat(pair_frames, how="vertical")
    if combined.is_empty():
        return None

    result = combined.select([
        pl.col("SURNAME"),
        pl.col("FIRST_NAME"),
        pl.concat_str([pl.col("SURNAME"), pl.col("FIRST_NAME")], separator=" ").str.strip_chars().alias("COMPLETE_NAME_RAW"),
        pl.lit("U").alias("SEX"),
        pl.lit("").alias("DATE_OF_BIRTH"),
        pl.lit(company_code).alias("CMPY_NO"),
        pl.col("POLICY_NUMBER"),
        pl.lit(file_path).alias("FILE_PATH"),
        pl.lit(sheet_name).alias("SHEET"),
    ])
    return _finalize_complete_name(result)


def _build_standard(data_df, name_col_names, firstlast_col_names, sex_col_name, dob_col_name,
                     policy_col_name, company_code, file_path, sheet_name):
    """One output row per input row -- the common case."""
    surname_expr = _clean_name_column_expr(firstlast_col_names[0]) if firstlast_col_names else pl.lit("", dtype=pl.Utf8)
    firstname_expr = _clean_name_column_expr(firstlast_col_names[1]) if len(firstlast_col_names) > 1 else pl.lit("", dtype=pl.Utf8)
    complete_name_expr = _clean_name_column_expr(name_col_names[0]) if name_col_names else pl.lit("", dtype=pl.Utf8)
    sex_expr = _sex_column_expr(sex_col_name) if sex_col_name else pl.lit("", dtype=pl.Utf8)
    dob_expr = _dob_column_expr(dob_col_name) if dob_col_name else pl.lit("", dtype=pl.Utf8)
    policy_expr = pl.col(policy_col_name).cast(pl.Utf8) if policy_col_name else pl.lit(None, dtype=pl.Utf8)

    # Uncleaned source text for the name column, ONLY for the digit safety
    # net check below -- never used as an output value. See
    # _finalize_complete_name's docstring for why this must be the raw text.
    name_source_expr = (
        pl.col(name_col_names[0]).cast(pl.Utf8).fill_null("")
        if name_col_names else pl.lit("", dtype=pl.Utf8)
    )

    result = data_df.select([
        surname_expr.alias("SURNAME"),
        firstname_expr.alias("FIRST_NAME"),
        complete_name_expr.alias("COMPLETE_NAME_RAW"),
        sex_expr.alias("SEX"),
        dob_expr.alias("DATE_OF_BIRTH"),
        pl.lit(company_code).alias("CMPY_NO"),
        policy_expr.alias("POLICY_NUMBER"),
        pl.lit(file_path).alias("FILE_PATH"),
        pl.lit(sheet_name).alias("SHEET"),
        name_source_expr.alias("_NAME_SOURCE_FOR_DIGIT_CHECK"),
    ])
    return _finalize_complete_name(result, digit_check_col="_NAME_SOURCE_FOR_DIGIT_CHECK")


def build_output_df(df, match, company_code, file_path, sheet_name):
    """
    df: full raw polars DataFrame for the sheet/file (no header row removed yet).
    match: one result dict from ofac_header_detection.detect_all().
    Returns (output_df, missing_name_count) where output_df has exactly
    OUTPUT_COLUMNS and missing_name_count is how many rows were dropped for
    having no usable name at all (for logging/remarks, not an error).
    """
    header_row_idx = match["header_row_idx"]
    columns = match["columns"]
    data_start_row = header_row_idx + 1 if header_row_idx >= 0 else 0

    data_df = df.slice(data_start_row)

    name_indices = _filter_numeric_columns(df, columns.get("name", []), data_start_row)
    firstlast_indices = _filter_numeric_columns(df, columns.get("firstlastname", []), data_start_row)
    sex_indices = columns.get("sex", [])
    dob_indices = columns.get("dob", [])
    policy_indices = columns.get("policynum", [])

    name_col_names = [_column_name(df, i) for i in name_indices]
    firstlast_col_names = [_column_name(df, i) for i in firstlast_indices]
    sex_col_name = _column_name(df, sex_indices[0]) if sex_indices else None
    dob_col_name = _column_name(df, dob_indices[0]) if dob_indices else None
    policy_col_name = _column_name(df, policy_indices[0]) if policy_indices else None

    multiple_name = len(name_col_names) >= 2 or len(firstlast_col_names) > 2

    result = None
    if multiple_name:
        if name_col_names:
            result = _explode_complete_names(data_df, name_col_names, policy_col_name, company_code, file_path, sheet_name)
        if result is None and len(firstlast_col_names) > 2:
            result = _explode_name_pairs(data_df, firstlast_col_names, policy_col_name, company_code, file_path, sheet_name)

    if result is None:
        result = _build_standard(
            data_df, name_col_names, firstlast_col_names, sex_col_name, dob_col_name,
            policy_col_name, company_code, file_path, sheet_name,
        )

    total_rows = result.height
    result = result.filter(pl.col("COMPLETE_NAME").is_not_null() & (pl.col("COMPLETE_NAME") != ""))
    missing_name_count = total_rows - result.height

    output_df = result.select(OUTPUT_COLUMNS)
    return output_df, missing_name_count


def extract_from_dataframe(df, header_sets, company_code, file_path, sheet_name, max_search_rows=MAX_SEARCH_ROWS):
    """
    Top-level entry point for one sheet/file already loaded as a headerless
    polars DataFrame. Runs detection, then builds output for every table
    block found (usually one), concatenating results.

    Returns (output_df, detection_metadata) where detection_metadata is a
    list of dicts (one per table block) with enough detail for the caller to
    write a file_logs row: header_row_idx, which raw header values matched,
    whether content-based fallback was used, multiple_name flag, missing
    name count.
    """
    sample_rows = df.head(min(df.height, max_search_rows)).rows()
    matches = detection.detect_all(sample_rows, df.width, header_sets, max_search_rows=max_search_rows)

    if not matches:
        empty = pl.DataFrame(schema={col: pl.Utf8 for col in OUTPUT_COLUMNS})
        return empty, []

    output_frames = []
    metadata = []
    for table_idx, match in enumerate(matches):
        table_sheet_name = f"{sheet_name}_table{table_idx + 1}" if len(matches) > 1 else sheet_name
        output_df, missing_name_count = build_output_df(df, match, company_code, file_path, table_sheet_name)
        output_frames.append(output_df)

        name_cols_used = [df.columns[i] for i in match["columns"].get("name", [])]
        firstlast_cols_used = [df.columns[i] for i in match["columns"].get("firstlastname", [])]
        metadata.append({
            "sheet_name": table_sheet_name,
            "header_row_idx": match["header_row_idx"],
            "content_based": match.get("content_based", False),
            "identified_headers": ", ".join(str(v) for v in match.get("raw_header_values", []) if v),
            "multiple_name": len(name_cols_used) >= 2 or len(firstlast_cols_used) > 2,
            "full_name_header": ", ".join(name_cols_used) if name_cols_used else None,
            "first_last_name_header": ", ".join(firstlast_cols_used) if firstlast_cols_used else None,
            "sex_header": df.columns[match["columns"]["sex"][0]] if match["columns"].get("sex") else None,
            "dob_header": df.columns[match["columns"]["dob"][0]] if match["columns"].get("dob") else None,
            "policy_number_header": df.columns[match["columns"]["policynum"][0]] if match["columns"].get("policynum") else None,
            "row_count": df.height,
            "output_row_count": output_df.height,
            "missing_name_count": missing_name_count,
        })

    combined = pl.concat(output_frames, how="vertical") if len(output_frames) > 1 else output_frames[0]
    combined = combined.unique()  # row-level dedup, per the confirmed (deferred cross-file) design decision

    return combined, metadata
