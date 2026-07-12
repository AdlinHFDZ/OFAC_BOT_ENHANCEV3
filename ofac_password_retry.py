"""
ofac_password_retry.py
The "try each password in order, stop at first success" control flow, pulled
out on its own so it can be unit-tested without needing real Excel
decryption or 7-Zip -- both the msoffcrypto and 7z password-trying loops in
ofac_scanner_engine.py are thin wrappers around this.
"""


def try_passwords(password_entries, attempt_fn):
    """
    password_entries: list of (label, password) tuples, in the order to try.
    attempt_fn: callable(password) -> bool. Should return True on a
        successful attempt and False (or raise) on failure -- both are
        treated as "try the next one".

    Returns the (label, password) tuple that succeeded, or None if every
    attempt failed. This is also the hook point for a future optimization
    (try the last-successful password for this company first): the caller
    just needs to order password_entries accordingly before calling this --
    no change needed here.
    """
    for label, password in password_entries:
        try:
            if attempt_fn(password):
                return label, password
        except Exception:
            continue
    return None
