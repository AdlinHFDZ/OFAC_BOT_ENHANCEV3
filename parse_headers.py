"""
parse_headers.py
Converts company_headers_source.md into:
  - defaults.json           (aliases common enough across companies to be baseline)
  - companies/<CODE>.json   (per-company residual aliases, name/firstlastname/sex/dob/policynum only)
  - company_notes.json      (every "Notes" caveat + special-case flag, preserved for reference)
  - conversion_report.md    (human-readable summary of everything that needs review)

Design decisions baked in here (matching what was agreed for the JSON header config):
  - Only 5 categories go into the matching JSON: name, firstlastname, sex, dob, policynum.
    Prem and Claim exist in the source data but aren't part of OFAC extraction's output
    schema, so they're captured separately for reference, not merged into the matcher.
  - An alias is promoted to defaults.json if it appears (same category, same normalized
    code) across at least DEFAULT_THRESHOLD companies -- i.e. it's genuinely common
    vocabulary, not one company's jargon. Everything else stays in that company's file.
  - Company-level free-text notes, and known-problem flags (unsafe generic terms, "not a
    one-row header", missing name column, etc.) are preserved verbatim -- never silently
    dropped and never silently acted on (e.g. never auto-excluding a flagged-unsafe alias).
"""

import re
import json
import os
from collections import defaultdict, Counter

SOURCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_headers_source.md")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_headers")
DEFAULT_THRESHOLD = 8  # alias must appear in at least this many companies to become a default

CATEGORY_MAP = {
    "Name": "name",
    "First/Last": "firstlastname",
    "Sex": "sex",
    "DOB": "dob",
    "Policy #": "policynum",
}
REFERENCE_ONLY_CATEGORIES = {"Prem": "prem", "Claim": "claim"}
SCHEMA_CATEGORIES = list(CATEGORY_MAP.values())

ALIAS_PATTERN = re.compile(r"`([^`]+)`(?:\s*→\s*([^·,\n]+))?")


def clean_for_match(text):
    return re.sub(r"[^a-z]", "", text.lower())


def parse_aliases_cell(cell_text):
    """
    Extract (code, display_text) pairs from a cell like:
      "`insname` → INS_NAME · `insnam` → INS_NAM"
    or:
      "`name`, `assuredname`, `assuredowner`"
    Returns a list of display-text strings (the raw header text to store; the app
    normalizes at load time). Falls back to the code itself if no arrow-text given,
    and takes only the first "/"-separated variant when multiple spellings are shown.
    """
    results = []
    for match in ALIAS_PATTERN.finditer(cell_text):
        code, display = match.group(1), match.group(2)
        if display:
            display = display.strip().split("/")[0].strip()
        else:
            display = code
        results.append(display)
    return results


def split_table_row(line):
    """Split a markdown table row into its cell strings, dropping the leading/trailing empties."""
    parts = [p.strip() for p in line.strip().split("|")]
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return parts


def is_separator_row(cells):
    return all(re.fullmatch(r"-+", c) for c in cells if c)


def parse_source(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    blocks = re.split(r"^## ", text, flags=re.MULTILINE)[1:]  # drop preamble before first "## "
    companies = {}

    for block in blocks:
        lines = block.splitlines()
        heading_line = lines[0].strip()
        m = re.match(r"^(\S+)\s*(?:\((.*)\))?\s*$", heading_line)
        code = m.group(1)
        company_note = m.group(2) or None

        entry = {
            "schema": defaultdict(list),      # category -> list of display-text aliases
            "reference": defaultdict(list),   # Prem/Claim -> list of raw text (best-effort)
            "notes": [],                      # per-row notes, human-readable
            "company_note": company_note,
        }

        found_table = False
        for line in lines[1:]:
            if not line.strip().startswith("|"):
                # Free text outside a table -- e.g. R29's "No fields -- legend row only..."
                stripped = line.strip()
                if stripped:
                    entry["notes"].append(stripped)
                continue

            cells = split_table_row(line)
            if not cells or is_separator_row(cells) or cells[0] == "Category":
                continue

            found_table = True
            category_label = cells[0]
            aliases_cell = cells[1] if len(cells) > 1 else ""
            notes_cell = cells[2] if len(cells) > 2 else ""

            if notes_cell and notes_cell.strip():
                entry["notes"].append(f"[{category_label}] {notes_cell.strip()}")

            if category_label == "—":
                continue  # notes-only row, already captured above

            aliases = parse_aliases_cell(aliases_cell)

            if category_label in CATEGORY_MAP:
                schema_key = CATEGORY_MAP[category_label]
                entry["schema"][schema_key].extend(aliases)
            elif category_label in REFERENCE_ONLY_CATEGORIES:
                ref_key = REFERENCE_ONLY_CATEGORIES[category_label]
                entry["reference"][ref_key].extend(aliases)
            # unrecognized category labels are silently ignored (none expected)

            if not aliases and aliases_cell and aliases_cell != "—":
                entry["notes"].append(f"[{category_label}] unparsed cell: {aliases_cell!r}")

        if not found_table:
            entry["notes"].append("No alias table found for this company (see company_note / notes).")

        companies[code] = entry

    return companies


def compute_defaults(companies):
    """
    Count how many distinct companies use each (category, normalized_code) pair.
    Anything at or above DEFAULT_THRESHOLD becomes part of defaults.json.
    Returns (defaults_dict, default_normalized_set) where default_normalized_set
    is used to strip now-redundant entries out of each company's file.
    """
    counts = defaultdict(Counter)  # category -> Counter(normalized_code -> company_count)
    representative_text = {}       # (category, normalized_code) -> a display-text sample

    for code, entry in companies.items():
        for category, aliases in entry["schema"].items():
            seen_this_company = set()
            for alias_text in aliases:
                norm = clean_for_match(alias_text)
                if not norm or norm in seen_this_company:
                    continue
                seen_this_company.add(norm)
                counts[category][norm] += 1
                representative_text.setdefault((category, norm), alias_text)

    defaults = {}
    default_normalized = defaultdict(set)
    for category in SCHEMA_CATEGORIES:
        promoted = [
            representative_text[(category, norm)]
            for norm, n in counts[category].items()
            if n >= DEFAULT_THRESHOLD
        ]
        defaults[category] = sorted(promoted, key=str.lower)
        default_normalized[category] = {clean_for_match(t) for t in promoted}

    return defaults, default_normalized


def build_company_files(companies, default_normalized):
    """
    For each company, keep only aliases NOT already covered by defaults.json
    (deduplicated within the company too). Companies whose schema ends up
    completely empty after this still get a file (possibly empty) so their
    notes aren't lost.
    """
    company_files = {}
    for code, entry in companies.items():
        out = {}
        for category in SCHEMA_CATEGORIES:
            seen = set()
            residual = []
            for alias_text in entry["schema"].get(category, []):
                norm = clean_for_match(alias_text)
                if not norm or norm in seen or norm in default_normalized[category]:
                    continue
                seen.add(norm)
                residual.append(alias_text)
            if residual:
                out[category] = sorted(residual, key=str.lower)
        company_files[code] = out
    return company_files


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "companies"), exist_ok=True)

    companies = parse_source(SOURCE_FILE)
    print(f"Parsed {len(companies)} company blocks.")

    defaults, default_normalized = compute_defaults(companies)
    with open(os.path.join(OUT_DIR, "defaults.json"), "w", encoding="utf-8") as f:
        json.dump(defaults, f, indent=2, ensure_ascii=False)
    print("defaults.json written:")
    for cat in SCHEMA_CATEGORIES:
        print(f"  {cat}: {len(defaults[cat])} aliases promoted (threshold={DEFAULT_THRESHOLD})")

    company_files = build_company_files(companies, default_normalized)
    for code, data in company_files.items():
        safe_code = re.sub(r"[^A-Za-z0-9_\-]", "_", code)
        with open(os.path.join(OUT_DIR, "companies", f"{safe_code}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ---- notes / flags for review ----
    notes_out = {}
    no_name_companies = []
    special_layout_companies = []
    unsafe_alias_flags = []

    for code, entry in companies.items():
        all_notes = list(entry["notes"])
        if entry["company_note"]:
            all_notes.insert(0, f"(company-level) {entry['company_note']}")
        if all_notes:
            notes_out[code] = all_notes

        if not entry["schema"].get("name"):
            no_name_companies.append(code)

        joined = " ".join(all_notes).lower()
        if "not one-row" in joined or "face-sheet" in joined or "vba" in joined or "legend row only" in joined:
            special_layout_companies.append(code)
        if "unsafe" in joined:
            unsafe_alias_flags.append(code)

    with open(os.path.join(OUT_DIR, "company_notes.json"), "w", encoding="utf-8") as f:
        json.dump(notes_out, f, indent=2, ensure_ascii=False)

    # ---- reference-only Prem/Claim capture (best-effort, not used for matching) ----
    reference_out = {
        code: {k: v for k, v in entry["reference"].items() if v}
        for code, entry in companies.items()
        if any(entry["reference"].values())
    }
    with open(os.path.join(OUT_DIR, "reference_prem_claim.json"), "w", encoding="utf-8") as f:
        json.dump(reference_out, f, indent=2, ensure_ascii=False)

    # ---- human-readable report ----
    report_lines = []
    report_lines.append(f"# Header Conversion Report\n")
    report_lines.append(f"Parsed **{len(companies)}** company blocks from the source document.\n")
    report_lines.append(f"## defaults.json contents (threshold: alias used by >= {DEFAULT_THRESHOLD} companies)\n")
    for cat in SCHEMA_CATEGORIES:
        report_lines.append(f"- **{cat}**: {len(defaults[cat])} aliases -- {', '.join(defaults[cat])}\n")

    report_lines.append(f"\n## Companies with NO name field found ({len(no_name_companies)})\n")
    report_lines.append("These companies cannot be matched on name via header detection at all -- OFAC screening for them depends entirely on content-based fallback detection, or needs a header library update.\n")
    for code in sorted(no_name_companies):
        report_lines.append(f"- {code}\n")

    report_lines.append(f"\n## Companies flagged as special/non-standard layout ({len(special_layout_companies)})\n")
    report_lines.append("These need manual review -- standard row-based header detection may not work as-is (face-sheet layouts, VBA-extracted claim sheets, legend-only entries).\n")
    for code in sorted(special_layout_companies):
        report_lines.append(f"- {code}: {'; '.join(notes_out.get(code, []))}\n")

    report_lines.append(f"\n## Companies with an explicitly flagged UNSAFE generic alias ({len(unsafe_alias_flags)})\n")
    report_lines.append("The source data marks these terms as ambiguous/collision-prone (e.g. \"Policy\" alone, \"Date of\" alone), but the raw alias is still included in the company's JSON as given -- no alias was silently removed. Flagging for your review rather than deciding unilaterally.\n")
    for code in sorted(unsafe_alias_flags):
        report_lines.append(f"- {code}: {'; '.join(n for n in notes_out.get(code, []) if 'unsafe' in n.lower())}\n")

    with open(os.path.join(OUT_DIR, "conversion_report.md"), "w", encoding="utf-8") as f:
        f.writelines(report_lines)

    print(f"\nWrote {len(company_files)} company JSON files to {OUT_DIR}/companies/")
    print(f"Companies with no name field: {len(no_name_companies)}")
    print(f"Companies flagged special-layout: {len(special_layout_companies)}")
    print(f"Companies with unsafe-alias flags: {len(unsafe_alias_flags)}")


if __name__ == "__main__":
    main()
