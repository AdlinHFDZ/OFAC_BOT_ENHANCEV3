"""
test_watcher.py
Tests the parts of ofac_watcher.py that don't need polars or a real
filesystem watcher: config validation, is_config_file, the retry/backoff
lock logic (against the real database), and password resolution (now
trivial, since the vault is unencrypted and config files store real
password values directly -- no more dev-crypto mode needed anywhere here).
"""

import os
import json
import shutil
import tempfile

os.environ.setdefault("OFAC_APP_ROOT", os.path.join(tempfile.gettempdir(), "ofac_watcher_test_root"))

import ofac_watcher as watcher
import ofac_database as db

TEST_ROOT = os.path.join(tempfile.gettempdir(), "ofac_watcher_test_root")


def _fresh_db():
    if os.path.exists(TEST_ROOT):
        shutil.rmtree(TEST_ROOT)
    os.makedirs(TEST_ROOT, exist_ok=True)
    db.init_database()


def test_is_config_file():
    assert watcher.is_config_file("/folder/configuration_12345.json") is True
    assert watcher.is_config_file("/folder/configuration.json") is True
    assert watcher.is_config_file("/folder/random_file.json") is False
    assert watcher.is_config_file("/folder/configuration_12345.csv") is False
    assert watcher.is_config_file("/folder/CONFIGURATION_12345.json") is False  # case-sensitive by design
    print("test_is_config_file PASSED")


def test_validate_config_catches_missing_fields():
    problems = watcher.validate_config({})
    assert len(problems) >= 4, f"Expected multiple missing-field problems, got: {problems}"
    print("test_validate_config_catches_missing_fields PASSED")


def test_validate_config_catches_empty_files_list():
    config = {
        "company_code": "TESTCO", "email_received_date": "2026-07-12",
        "files": [], "passwords": ["actual_password_1"],
    }
    problems = watcher.validate_config(config)
    assert any("empty" in p for p in problems)
    print("test_validate_config_catches_empty_files_list PASSED")


def test_validate_config_catches_bad_date_format():
    config = {
        "company_code": "TESTCO", "email_received_date": "07/12/2026",  # wrong format
        "files": ["a.csv"], "passwords": [],
    }
    problems = watcher.validate_config(config)
    assert any("YYYY-MM-DD" in p for p in problems)
    print("test_validate_config_catches_bad_date_format PASSED")


def test_validate_config_accepts_well_formed_config():
    config = {
        "company_code": "TESTCO", "email_received_date": "2026-07-12",
        "files": ["a.csv", "b.xlsx"], "passwords": ["actual_password_1"],
    }
    problems = watcher.validate_config(config)
    assert problems == [], f"Expected no problems, got: {problems}"
    print("test_validate_config_accepts_well_formed_config PASSED")


def test_retry_succeeds_immediately_when_not_blocked():
    _fresh_db()
    sleep_calls = []
    run_id = watcher.try_acquire_run_with_retry(
        "TESTCO", "2026-07-12", "watcher", "tester", "test_output_folder", 1,
        sleep_fn=lambda s: sleep_calls.append(s),
    )
    assert run_id is not None
    assert sleep_calls == [], "Should not have needed to retry at all"
    print("test_retry_succeeds_immediately_when_not_blocked PASSED")


def test_retry_waits_then_succeeds_once_the_blocking_run_finishes():
    _fresh_db()
    blocking_run = db.try_start_run("TESTCO", "2026-07-12", "manual", "someone_else", "test_output_folder", 1)
    assert blocking_run is not None

    sleep_calls = []
    attempt_count = [0]

    def fake_sleep(seconds):
        sleep_calls.append(seconds)
        attempt_count[0] += 1
        if attempt_count[0] == 2:
            # simulate the other run finishing right after the 2nd retry sleep
            db.finish_run(blocking_run, db.RUN_STATUS_COMPLETED, files_processed=1, files_failed=0)

    run_id = watcher.try_acquire_run_with_retry(
        "TESTCO", "2026-07-12", "watcher", "tester", "test_output_folder", 1,
        max_retries=5, sleep_fn=fake_sleep,
    )
    assert run_id is not None, "Expected the lock to eventually be acquired"
    assert len(sleep_calls) >= 2
    print(f"test_retry_waits_then_succeeds_once_the_blocking_run_finishes PASSED ({len(sleep_calls)} retries needed)")


def test_retry_gives_up_after_max_retries_if_still_blocked():
    _fresh_db()
    blocking_run = db.try_start_run("TESTCO", "2026-07-12", "manual", "someone_else", "test_output_folder", 1)
    assert blocking_run is not None
    # deliberately never finish blocking_run

    sleep_calls = []
    run_id = watcher.try_acquire_run_with_retry(
        "TESTCO", "2026-07-12", "watcher", "tester", "test_output_folder", 1,
        max_retries=3, sleep_fn=lambda s: sleep_calls.append(s),
    )
    assert run_id is None, "Expected to give up and return None when still blocked"
    assert len(sleep_calls) == 2, f"Expected 2 sleeps between 3 attempts, got {len(sleep_calls)}"
    print("test_retry_gives_up_after_max_retries_if_still_blocked PASSED")


def test_resolve_passwords_wraps_values_directly():
    """
    resolve_passwords no longer does any vault lookup at all -- the config
    already carries the real password values, so this just wraps each into
    the (label, password) tuple shape ofac_password_retry expects, with
    label == password.
    """
    result = watcher.resolve_passwords("TESTCO", ["secret1", "secret2"])
    assert result == [("secret1", "secret1"), ("secret2", "secret2")]
    print("test_resolve_passwords_wraps_values_directly PASSED")


def test_resolve_passwords_empty_list():
    assert watcher.resolve_passwords("TESTCO", []) == []
    print("test_resolve_passwords_empty_list PASSED")


if __name__ == "__main__":
    test_is_config_file()
    test_validate_config_catches_missing_fields()
    test_validate_config_catches_empty_files_list()
    test_validate_config_catches_bad_date_format()
    test_validate_config_accepts_well_formed_config()
    test_retry_succeeds_immediately_when_not_blocked()
    test_retry_waits_then_succeeds_once_the_blocking_run_finishes()
    test_retry_gives_up_after_max_retries_if_still_blocked()
    test_resolve_passwords_wraps_values_directly()
    test_resolve_passwords_empty_list()
    print("\nALL WATCHER TESTS PASSED")
