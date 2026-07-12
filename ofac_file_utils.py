"""
ofac_file_utils.py
Generic, reusable file-system helpers used across the scanner engine, header
extractor, and compiler: safe unique filenames, atomic writes, retrying file
moves, and text file encoding/dialect detection.

Nothing in this file is OFAC-specific -- it could be lifted into any project.
"""

import os
import re
import time
import shutil


def get_unique_save_path(file_path):
    """
    Given a desired file path, return a path guaranteed not to already exist,
    appending _1, _2, ... if needed. Also strips characters that cause
    problems on Windows file systems, keeping the extension intact.
    """
    folder = os.path.dirname(file_path)
    base, ext = os.path.splitext(os.path.basename(file_path))
    safe_base = re.sub(r"[^a-zA-Z0-9_\-\[\]]", "_", base)[:200]

    candidate = os.path.join(folder, f"{safe_base}{ext}")
    count = 1
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{safe_base}_{count}{ext}")
        count += 1
    return candidate


def atomic_write_bytes(final_path, data: bytes):
    """
    Write bytes to final_path atomically: write to a temp file in the same
    folder, then os.replace() it into place. Guarantees nobody -- including
    this app if it crashes mid-write -- ever sees a partially written file
    at final_path. Use this for the compiled report and per-run log exports.
    """
    tmp_path = final_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)
    os.replace(tmp_path, final_path)


def atomic_write_text(final_path, text: str, encoding="utf-8"):
    atomic_write_bytes(final_path, text.encode(encoding))


def move_file_to_archived(src_path, archived_folder, retries=3, retry_delay_seconds=10):
    """
    Move src_path into archived_folder, retrying on Windows file-lock errors
    (e.g. the file is still open in another program, or briefly locked by
    antivirus/sync software). Returns the final destination path, uniquified
    if a name collision occurs. Raises after repeated failure so the caller
    can log it rather than silently losing track of the file.
    """
    os.makedirs(archived_folder, exist_ok=True)
    dest = get_unique_save_path(os.path.join(archived_folder, os.path.basename(src_path)))

    last_error = None
    for _ in range(retries):
        try:
            shutil.move(src_path, dest)
            return dest
        except (PermissionError, OSError) as e:
            last_error = e
            time.sleep(retry_delay_seconds)

    raise RuntimeError(
        f"Failed to move {src_path} to {archived_folder} after {retries} attempts"
    ) from last_error


def get_all_files(directory):
    """Return the set of all file paths under directory, recursively."""
    return {
        os.path.join(root, f)
        for root, _, files in os.walk(directory)
        for f in files
    }


def detect_encoding_and_dialect(file_path, sample_bytes=10000):
    """
    Detect a text file's encoding (chardet) and CSV dialect (clevercsv).
    Returns (encoding, delimiter, quotechar).

    Imports are local to this function -- chardet/clevercsv are only needed
    for text-file processing, not for the atomic-write/move helpers above,
    so the rest of this module works even in environments (like a bare CI
    container) where those two packages aren't installed.
    """
    import chardet
    import clevercsv

    with open(file_path, "rb") as f:
        raw = f.read(sample_bytes)
    encoding = chardet.detect(raw)["encoding"] or "utf-8"

    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        sample = f.read(sample_bytes)
    dialect = clevercsv.Sniffer().sniff(sample)

    return encoding, dialect.delimiter, dialect.quotechar
