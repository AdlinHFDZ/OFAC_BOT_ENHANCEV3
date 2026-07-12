"""
ofac_header_config.py
Loads and merges company header-synonym configuration:
  config/headers/defaults.json
  config/headers/companies/<CODE>.json

Merge rule (as agreed): union per field. A company's file only needs to list
its own additions -- anything already in defaults.json doesn't need to be
repeated. Both files are cleaned/normalized once and cached in memory, so a
scanner process doesn't re-read or re-normalize on every file it processes.

A malformed company file fails loudly for that company only (logged, and that
company falls back to defaults-only) -- it never takes down the whole app or
other companies, matching the blast-radius design decision.
"""

import os
import json
import re
import threading

from ofac_constants import HEADERS_DEFAULTS_FILE, HEADERS_COMPANIES_FOLDER, HEADER_FIELD_KEYS

_cache_lock = threading.Lock()
_defaults_cache = None
_company_cache = {}  # company_code (normalized) -> merged, normalized dict of sets


class HeaderConfigError(Exception):
    """Raised for defaults.json problems only -- these are not recoverable,
    since every company depends on defaults being valid."""


def clean_for_match(text):
    if text is None:
        return ""
    return re.sub(r"[^a-z]", "", str(text).lower())


def normalize_company_code(code):
    return (code or "").strip().upper()


def _validate_field_dict(data, source_label):
    """
    Ensure a loaded JSON object only contains known field keys, and that every
    value is a list of non-empty strings. Returns (clean_dict, warnings).
    """
    warnings = []
    if not isinstance(data, dict):
        raise HeaderConfigError(f"{source_label}: top level must be a JSON object")

    unknown_keys = set(data.keys()) - set(HEADER_FIELD_KEYS)
    if unknown_keys:
        warnings.append(f"{source_label}: ignoring unknown key(s) {sorted(unknown_keys)}")

    clean = {}
    for key in HEADER_FIELD_KEYS:
        raw_values = data.get(key, [])
        if not isinstance(raw_values, list):
            warnings.append(f"{source_label}: field '{key}' should be a list, got {type(raw_values).__name__} -- skipping field")
            clean[key] = []
            continue
        values = [v for v in raw_values if isinstance(v, str) and v.strip()]
        if len(values) != len(raw_values):
            warnings.append(f"{source_label}: field '{key}' had non-string or empty entries -- dropped them")
        clean[key] = values

    return clean, warnings


def _load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_defaults(force_reload=False):
    """
    Load and validate defaults.json. Cached after first call. Raises
    HeaderConfigError if defaults.json is missing or malformed -- unlike a
    single company file, there's no safe fallback for defaults itself.
    """
    global _defaults_cache
    with _cache_lock:
        if _defaults_cache is not None and not force_reload:
            return _defaults_cache

        if not os.path.exists(HEADERS_DEFAULTS_FILE):
            raise HeaderConfigError(f"defaults.json not found at {HEADERS_DEFAULTS_FILE}")

        try:
            raw = _load_json_file(HEADERS_DEFAULTS_FILE)
        except json.JSONDecodeError as e:
            raise HeaderConfigError(f"defaults.json is not valid JSON: {e}") from e

        clean, warnings = _validate_field_dict(raw, "defaults.json")
        for w in warnings:
            print(f"[header config] WARNING: {w}")

        _defaults_cache = {key: {clean_for_match(v) for v in values} for key, values in clean.items()}
        return _defaults_cache


def _check_cross_field_collisions(merged, source_label):
    """
    Warn (don't raise) if the same normalized alias ended up matching more
    than one field after merging defaults + company overrides -- this usually
    means a typo (an alias meant for 'dob' accidentally placed under 'sex').
    """
    seen = {}
    for field, values in merged.items():
        for v in values:
            if v in seen and seen[v] != field:
                print(f"[header config] WARNING: {source_label}: alias '{v}' matches both "
                      f"'{seen[v]}' and '{field}' -- check for a misplaced entry")
            seen[v] = field


def load_company_headers(company_code, force_reload=False):
    """
    Return the merged (defaults UNION company-specific) header sets for a
    company, as {field: set_of_normalized_aliases}. Always includes defaults
    even if the company has no override file, or the override file is broken.
    """
    normalized_code = normalize_company_code(company_code)

    with _cache_lock:
        if normalized_code in _company_cache and not force_reload:
            return _company_cache[normalized_code]

    defaults = load_defaults(force_reload=force_reload)  # may raise -- intentional, no safe fallback

    merged = {key: set(values) for key, values in defaults.items()}

    company_file = os.path.join(HEADERS_COMPANIES_FOLDER, f"{normalized_code}.json")
    if os.path.exists(company_file):
        try:
            raw = _load_json_file(company_file)
            clean, warnings = _validate_field_dict(raw, f"companies/{normalized_code}.json")
            for w in warnings:
                print(f"[header config] WARNING: {w}")
            for key, values in clean.items():
                merged[key].update(clean_for_match(v) for v in values)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[header config] ERROR loading companies/{normalized_code}.json: {e} "
                  f"-- falling back to defaults only for this company")
    # else: no company-specific file -- defaults only, which is expected and fine.

    _check_cross_field_collisions(merged, f"company={normalized_code}")

    with _cache_lock:
        _company_cache[normalized_code] = merged

    return merged


def clear_cache():
    """Call after editing header config files (e.g. from an admin UI) so the next
    load_company_headers() call picks up the change instead of serving stale data."""
    global _defaults_cache
    with _cache_lock:
        _defaults_cache = None
        _company_cache.clear()
