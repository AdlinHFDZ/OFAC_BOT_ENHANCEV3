"""
test_main.py
Tests _parse_args -- pure dispatch logic, no GUI/Windows/DB needed.
"""

from ofac_main import _parse_args


def test_no_args_means_gui_mode():
    mode, extra = _parse_args(["ofac_main.py"])
    assert mode == "gui"
    assert extra is None
    print("test_no_args_means_gui_mode PASSED")


def test_watch_flag():
    mode, extra = _parse_args(["ofac_main.py", "--watch"])
    assert mode == "watch"
    assert extra is None
    print("test_watch_flag PASSED")


def test_process_config_with_path():
    mode, extra = _parse_args(["ofac_main.py", "--process-config", "/tmp/configuration_123.json"])
    assert mode == "process-config"
    assert extra == "/tmp/configuration_123.json"
    print("test_process_config_with_path PASSED")


def test_process_config_missing_path_raises():
    try:
        _parse_args(["ofac_main.py", "--process-config"])
        assert False, "Expected ValueError for missing config path"
    except ValueError as e:
        assert "requires exactly one argument" in str(e)
    print("test_process_config_missing_path_raises PASSED")


def test_process_config_too_many_args_raises():
    try:
        _parse_args(["ofac_main.py", "--process-config", "a.json", "extra"])
        assert False, "Expected ValueError for too many arguments"
    except ValueError:
        pass
    print("test_process_config_too_many_args_raises PASSED")


def test_unknown_flag_raises_with_helpful_usage():
    try:
        _parse_args(["ofac_main.py", "--bogus"])
        assert False, "Expected ValueError for unknown flag"
    except ValueError as e:
        assert "Unknown argument" in str(e)
        assert "--watch" in str(e), "Usage message should mention valid options"
    print("test_unknown_flag_raises_with_helpful_usage PASSED")


if __name__ == "__main__":
    test_no_args_means_gui_mode()
    test_watch_flag()
    test_process_config_with_path()
    test_process_config_missing_path_raises()
    test_process_config_too_many_args_raises()
    test_unknown_flag_raises_with_helpful_usage()
    print("\nALL MAIN ENTRY POINT TESTS PASSED")
