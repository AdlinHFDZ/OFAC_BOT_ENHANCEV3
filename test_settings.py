"""
test_settings.py
"""

import os
import shutil
import tempfile

TEST_ROOT = os.path.join(tempfile.gettempdir(), "ofac_settings_test_root")
os.environ["OFAC_APP_ROOT"] = TEST_ROOT

import ofac_settings as settings_module
from ofac_constants import APP_SETTINGS_FILE, OUTPUT_ROOT


def _fresh():
    if os.path.exists(TEST_ROOT):
        shutil.rmtree(TEST_ROOT)


def test_load_settings_returns_empty_dict_when_no_file_exists():
    _fresh()
    assert settings_module.load_settings() == {}
    print("test_load_settings_returns_empty_dict_when_no_file_exists PASSED")


def test_save_then_load_roundtrip():
    _fresh()
    settings_module.save_settings({"watch_folder": "/some/path", "theme": "darkly"})
    loaded = settings_module.load_settings()
    assert loaded == {"watch_folder": "/some/path", "theme": "darkly"}
    print("test_save_then_load_roundtrip PASSED")


def test_save_is_atomic_no_tmp_file_left_behind():
    _fresh()
    settings_module.save_settings({"watch_folder": "/x"})
    assert os.path.exists(APP_SETTINGS_FILE)
    assert not os.path.exists(APP_SETTINGS_FILE + ".tmp"), "Temp file should not survive a successful save"
    print("test_save_is_atomic_no_tmp_file_left_behind PASSED")


def test_get_output_root_falls_back_to_default_when_not_set():
    result = settings_module.get_output_root({"watch_folder": "/x"})  # no output_folder key at all
    assert result == OUTPUT_ROOT
    print("test_get_output_root_falls_back_to_default_when_not_set PASSED")


def test_get_output_root_falls_back_when_explicitly_empty():
    result = settings_module.get_output_root({"output_folder": ""})
    assert result == OUTPUT_ROOT, "An empty string should fall back to the default, not be used literally"
    print("test_get_output_root_falls_back_when_explicitly_empty PASSED")


def test_get_output_root_uses_configured_value_when_set():
    result = settings_module.get_output_root({"output_folder": "/shared/OFAC_Reports"})
    assert result == "/shared/OFAC_Reports"
    print("test_get_output_root_uses_configured_value_when_set PASSED")


def test_get_output_root_reads_from_disk_when_no_dict_passed():
    _fresh()
    settings_module.save_settings({"output_folder": "/custom/output"})
    result = settings_module.get_output_root()  # no argument -- should load from disk
    assert result == "/custom/output"
    print("test_get_output_root_reads_from_disk_when_no_dict_passed PASSED")


def test_get_watch_folder():
    assert settings_module.get_watch_folder({"watch_folder": "/watch"}) == "/watch"
    assert settings_module.get_watch_folder({}) is None
    print("test_get_watch_folder PASSED")


def test_corrupted_settings_file_returns_empty_dict_not_a_crash():
    _fresh()
    from ofac_constants import ensure_app_folders
    ensure_app_folders()
    with open(APP_SETTINGS_FILE, "w") as f:
        f.write("{ this is not valid json")
    assert settings_module.load_settings() == {}
    print("test_corrupted_settings_file_returns_empty_dict_not_a_crash PASSED")


if __name__ == "__main__":
    test_load_settings_returns_empty_dict_when_no_file_exists()
    test_save_then_load_roundtrip()
    test_save_is_atomic_no_tmp_file_left_behind()
    test_get_output_root_falls_back_to_default_when_not_set()
    test_get_output_root_falls_back_when_explicitly_empty()
    test_get_output_root_uses_configured_value_when_set()
    test_get_output_root_reads_from_disk_when_no_dict_passed()
    test_get_watch_folder()
    test_corrupted_settings_file_returns_empty_dict_not_a_crash()
    print("\nALL SETTINGS TESTS PASSED")
