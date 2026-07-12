"""
migrate_passwords_to_vault.py
One-time migration: reads a Code<TAB>Password list (blank password column
means "no password yet for this company") and creates one plain-JSON vault
file per company that has at least one password. Run this once on setup, or
again any time company_passwords_source.tsv changes.

Companies with a blank password in the source list get NO file created --
same as any company nobody has added a password for yet. They'll show "No
passwords for this company" in the GUI picker until someone uses '+ New
Password', exactly like the manual-add flow for a brand new company code.
"""

import os
import sys
from ofac_password_vault import save_company_passwords, normalize_company_code

SOURCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_passwords_source.tsv")


def parse_source(path):
    """Each line: CODE<whitespace>PASSWORD (password half may be empty)."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 1:
                parts = line.split(None, 1)
            code = parts[0].strip()
            password = parts[1].strip() if len(parts) > 1 else ""
            if code:
                rows.append((code, password))
    return rows


def main():
    rows = parse_source(SOURCE_FILE)

    with_password = [(c, p) for c, p in rows if p]
    blank = [c for c, p in rows if not p]

    print(f"Parsed {len(rows)} companies from source list.")
    print(f"  {len(with_password)} have a password to migrate")
    print(f"  {len(blank)} are blank -- no file will be created for these")

    migrated = 0
    for code, password in with_password:
        save_company_passwords(code, [{
            "password": password,
            "added_at": "2026-07-12",  # migration date, not a real "added" date
        }])
        migrated += 1

    print(f"\nMigrated {migrated} company vault files.")
    print("Blank-password companies (no file created, add later via GUI):")
    for code in sorted(blank):
        print(f"  {code}")


if __name__ == "__main__":
    main()
