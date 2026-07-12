"""
ofac_password_vault.py
Per-company password storage: plain JSON, one file per company, no
encryption.

This is a deliberate simplification, made on request. An earlier version
encrypted passwords with Windows DPAPI, but that meant the GUI could only
ever show a generic "Password 1", "Password 2" in the picker (the real
value was only ever decrypted at the moment of use) -- which made it hard
to tell which stored password was actually the right one to pick for a
given file. Plain storage means the GUI can show the actual password text
directly, so picking the right one is just reading it.

Trade-off worth knowing: config/passwords/companies/<CODE>.json now holds
readable passwords on disk, and the "Queue for Watcher" job files
(configuration_*.json) also carry the real password value now rather than
an opaque label -- there's no separate resolve-at-scan-time step anymore.
If you ever want encryption back, the per-company file structure is
unchanged; only an encrypt/decrypt step would need to be reintroduced.

One thing this file still deliberately protects: the *database run log*
(file_logs.password_label) never stores the raw matched password, even
though the vault itself is now unencrypted -- see mask_password() below.
That log is more likely to be shared/exported than the vault file itself,
so it keeps a masked value rather than silently starting to accumulate
plaintext secrets as a side effect of this simplification.
"""

import os
import json
import re
from datetime import date

from ofac_constants import PASSWORDS_COMPANIES_FOLDER
from ofac_file_utils import atomic_write_text


class VaultError(Exception):
    pass


def normalize_company_code(code):
    return (code or "").strip().upper()


def _company_file_path(company_code):
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", normalize_company_code(company_code))
    return os.path.join(PASSWORDS_COMPANIES_FOLDER, f"{safe}.json")


def load_company_passwords(company_code):
    """
    Returns the list of password entries for a company:
      [{"password": "...", "added_at": "2026-01-15"}, ...]
    Returns an empty list if the company has no password file yet -- the
    normal, expected state for a company nobody has added a password for.
    """
    path = _company_file_path(company_code)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        wrapper = json.load(f)
    return wrapper.get("passwords", [])


def save_company_passwords(company_code, entries):
    normalized_code = normalize_company_code(company_code)
    wrapper = {"company_code": normalized_code, "passwords": entries}
    os.makedirs(PASSWORDS_COMPANIES_FOLDER, exist_ok=True)
    path = _company_file_path(normalized_code)
    atomic_write_text(path, json.dumps(wrapper, indent=2, ensure_ascii=False))


def add_password(company_code, password):
    """
    Convenience wrapper for the GUI's '+ New Password' button. Silently does
    nothing if that exact password is already stored for this company,
    rather than creating a duplicate entry.
    """
    entries = load_company_passwords(company_code)
    if any(e["password"] == password for e in entries):
        return
    entries.append({"password": password, "added_at": date.today().isoformat()})
    save_company_passwords(company_code, entries)


def remove_password(company_code, password):
    entries = load_company_passwords(company_code)
    remaining = [e for e in entries if e["password"] != password]
    if len(remaining) == len(entries):
        raise VaultError(f"Password not found for company {company_code!r}")
    save_company_passwords(company_code, remaining)


def list_passwords(company_code):
    """
    The actual password values, for showing directly in the GUI picker --
    there's no separate label to resolve anymore, since hiding the value
    behind a generic "Password N" was exactly the usability problem this
    module exists to fix.
    """
    return [e["password"] for e in load_company_passwords(company_code)]


def mask_password(password):
    """
    Used only for the database run log (file_logs.password_label), never
    for the GUI picker. Keeps enough shape to distinguish entries in a
    troubleshooting context without writing the real secret into a log that
    might get shared or exported more widely than the vault file itself.
    "RGA2014SEPOA" -> "R**********A". Anything 2 characters or shorter
    becomes all asterisks (nothing safe to reveal at that length).
    """
    if not password:
        return None
    if len(password) <= 2:
        return "*" * len(password)
    return password[0] + "*" * (len(password) - 2) + password[-1]
