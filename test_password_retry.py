"""
test_password_retry.py
"""
from ofac_password_retry import try_passwords


def test_first_password_succeeds():
    calls = []
    def attempt(pw):
        calls.append(pw)
        return pw == "correct1"
    result = try_passwords([("Password 1", "correct1"), ("Password 2", "correct2")], attempt)
    assert result == ("Password 1", "correct1")
    assert calls == ["correct1"], "Should stop after first success, not try Password 2"
    print("test_first_password_succeeds PASSED")


def test_second_password_succeeds_after_first_fails():
    calls = []
    def attempt(pw):
        calls.append(pw)
        return pw == "correct2"
    result = try_passwords([("Password 1", "wrong"), ("Password 2", "correct2")], attempt)
    assert result == ("Password 2", "correct2")
    assert calls == ["wrong", "correct2"]
    print("test_second_password_succeeds_after_first_fails PASSED")


def test_no_password_works():
    result = try_passwords([("Password 1", "a"), ("Password 2", "b")], lambda pw: False)
    assert result is None
    print("test_no_password_works PASSED")


def test_empty_password_list():
    result = try_passwords([], lambda pw: True)
    assert result is None
    print("test_empty_password_list PASSED")


def test_exception_during_attempt_is_treated_as_failure_not_crash():
    def attempt(pw):
        if pw == "bad":
            raise ValueError("simulated decrypt failure")
        return pw == "good"
    result = try_passwords([("Password 1", "bad"), ("Password 2", "good")], attempt)
    assert result == ("Password 2", "good"), "Should recover from an exception and keep trying"
    print("test_exception_during_attempt_is_treated_as_failure_not_crash PASSED")


if __name__ == "__main__":
    test_first_password_succeeds()
    test_second_password_succeeds_after_first_fails()
    test_no_password_works()
    test_empty_password_list()
    test_exception_during_attempt_is_treated_as_failure_not_crash()
    print("\nALL PASSWORD RETRY TESTS PASSED")
