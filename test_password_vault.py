"""
test_password_vault.py
Unlike the earlier DPAPI-based version of this module, this one has zero
external/platform dependencies -- fully testable here, no caveats, no
dev-mode flag needed.
"""

import os
import shutil
import tempfile

TEST_ROOT = os.path.join(tempfile.gettempdir(), "ofac_password_vault_test_root")
os.environ["OFAC_APP_ROOT"] = TEST_ROOT

import ofac_password_vault as vault


def _fresh():
    if os.path.exists(TEST_ROOT):
        shutil.rmtree(TEST_ROOT)


def test_new_company_has_no_passwords():
    _fresh()
    assert vault.load_company_passwords("NEWCO") == []
    assert vault.list_passwords("NEWCO") == []
    print("test_new_company_has_no_passwords PASSED")


def test_add_and_list_password():
    _fresh()
    vault.add_password("TESTCO", "secret1")
    assert vault.list_passwords("TESTCO") == ["secret1"]
    print("test_add_and_list_password PASSED")


def test_add_multiple_passwords_preserves_order():
    _fresh()
    vault.add_password("TESTCO", "first")
    vault.add_password("TESTCO", "second")
    vault.add_password("TESTCO", "third")
    assert vault.list_passwords("TESTCO") == ["first", "second", "third"]
    print("test_add_multiple_passwords_preserves_order PASSED")


def test_adding_exact_duplicate_is_a_no_op():
    _fresh()
    vault.add_password("TESTCO", "secret1")
    vault.add_password("TESTCO", "secret1")  # same value again
    assert vault.list_passwords("TESTCO") == ["secret1"], "Should not create a duplicate entry"
    print("test_adding_exact_duplicate_is_a_no_op PASSED")


def test_remove_password():
    _fresh()
    vault.add_password("TESTCO", "keep_me")
    vault.add_password("TESTCO", "remove_me")
    vault.remove_password("TESTCO", "remove_me")
    assert vault.list_passwords("TESTCO") == ["keep_me"]
    print("test_remove_password PASSED")


def test_remove_nonexistent_password_raises():
    _fresh()
    vault.add_password("TESTCO", "real_password")
    try:
        vault.remove_password("TESTCO", "not_actually_stored")
        assert False, "Expected VaultError"
    except vault.VaultError:
        pass
    print("test_remove_nonexistent_password_raises PASSED")


def test_passwords_are_isolated_per_company():
    _fresh()
    vault.add_password("COMPANY_A", "a_password")
    vault.add_password("COMPANY_B", "b_password")
    assert vault.list_passwords("COMPANY_A") == ["a_password"]
    assert vault.list_passwords("COMPANY_B") == ["b_password"]
    print("test_passwords_are_isolated_per_company PASSED")


def test_company_code_normalization():
    _fresh()
    vault.add_password("testco", "secret1")
    assert vault.list_passwords("TESTCO") == ["secret1"]
    assert vault.list_passwords("  TestCo  ") == ["secret1"]
    print("test_company_code_normalization PASSED")


def test_stored_file_is_actually_plain_readable_json():
    """Confirms the deliberate design: no encryption, the file itself is
    just readable JSON -- this is the whole point of the simplification."""
    _fresh()
    vault.add_password("TESTCO", "my_real_password")
    from ofac_constants import PASSWORDS_COMPANIES_FOLDER
    path = os.path.join(PASSWORDS_COMPANIES_FOLDER, "TESTCO.json")
    with open(path, "r", encoding="utf-8") as f:
        raw_content = f.read()
    assert "my_real_password" in raw_content, "Password should be plainly readable in the file"
    import json
    parsed = json.loads(raw_content)  # also confirm it's valid, well-formed JSON
    assert parsed["passwords"][0]["password"] == "my_real_password"
    print("test_stored_file_is_actually_plain_readable_json PASSED")


def test_save_is_atomic_no_tmp_file_left_behind():
    _fresh()
    vault.add_password("TESTCO", "secret1")
    from ofac_constants import PASSWORDS_COMPANIES_FOLDER
    path = os.path.join(PASSWORDS_COMPANIES_FOLDER, "TESTCO.json")
    assert os.path.exists(path)
    assert not os.path.exists(path + ".tmp"), "Temp file should not survive a successful save"
    print("test_save_is_atomic_no_tmp_file_left_behind PASSED")


def test_mask_password_typical_case():
    assert vault.mask_password("RGA2014SEPOA") == "R**********A"
    print("test_mask_password_typical_case PASSED")


def test_mask_password_short_values():
    assert vault.mask_password("a") == "*"
    assert vault.mask_password("ab") == "**"
    assert vault.mask_password("abc") == "a*c"
    print("test_mask_password_short_values PASSED")


def test_mask_password_empty_or_none():
    assert vault.mask_password("") is None
    assert vault.mask_password(None) is None
    print("test_mask_password_empty_or_none PASSED")


def test_mask_password_never_contains_the_original_middle_characters():
    password = "SuperSecretValue123"
    masked = vault.mask_password(password)
    assert password[1:-1] not in masked
    assert masked[0] == password[0]
    assert masked[-1] == password[-1]
    print("test_mask_password_never_contains_the_original_middle_characters PASSED")


if __name__ == "__main__":
    test_new_company_has_no_passwords()
    test_add_and_list_password()
    test_add_multiple_passwords_preserves_order()
    test_adding_exact_duplicate_is_a_no_op()
    test_remove_password()
    test_remove_nonexistent_password_raises()
    test_passwords_are_isolated_per_company()
    test_company_code_normalization()
    test_stored_file_is_actually_plain_readable_json()
    test_save_is_atomic_no_tmp_file_left_behind()
    test_mask_password_typical_case()
    test_mask_password_short_values()
    test_mask_password_empty_or_none()
    test_mask_password_never_contains_the_original_middle_characters()
    print("\nALL PASSWORD VAULT TESTS PASSED")
