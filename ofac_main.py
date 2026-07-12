"""
ofac_main.py
Top-level entry point. Three modes:

    python ofac_main.py                        Launch the GUI (setup screen
                                                  first-run, scanner GUI after)
    python ofac_main.py --watch                 Run the background watcher --
                                                  monitors the input folder for
                                                  configuration_*.json files
    python ofac_main.py --process-config <path>  Process one config file directly
                                                  (this is what the watcher spawns
                                                  as a subprocess per config)

Compared to v1/v2: there is deliberately no "watch for any raw file and
auto-pop a tagging window" mode anymore. The confirmed GUI design has a
live, manually-refreshed file list right in the Scan tab, so there's no
need to react to file arrival with a spawned window -- the person opens the
app and works from the file list directly. This removes a whole class of
"which window is currently in focus / is another instance already handling
this file" complexity that existed in v1/v2 for no benefit under the new
design.

TEST COVERAGE NOTE: argument dispatch (_parse_args) is pure logic and
tested in test_main.py, runnable here. instance_check_or_focus needs real
Win32 APIs and can't be tested outside Windows.
"""

import os
import sys

from ofac_constants import ensure_app_folders, SETUP_WINDOW_TITLE, SCANNER_WINDOW_TITLE
import ofac_database as db
import ofac_settings


def instance_check_or_focus(window_title):
    """
    If a window with this title already exists, bring it to front and exit
    this (duplicate) process instead of opening a second one. Returns True
    if this process should continue (no existing window found).
    """
    try:
        from ctypes import WinDLL
    except ImportError:
        return True  # not on Windows (e.g. this dev sandbox) -- nothing to check

    user32 = WinDLL("user32", use_last_error=True)
    hwnd = user32.FindWindowW(None, window_title)
    if hwnd:
        SW_RESTORE = 5
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        sys.exit(0)
    return True


def _parse_args(argv):
    """
    Pure dispatch logic, separated from actually doing anything, so it can
    be unit tested without needing a display, Windows APIs, or a real
    config file. Returns (mode, extra) where mode is one of
    'watch' / 'process-config' / 'gui', and extra is the config path for
    'process-config' or None otherwise. Raises ValueError for bad usage.
    """
    if len(argv) == 1:
        return "gui", None
    if argv[1] == "--watch":
        return "watch", None
    if argv[1] == "--process-config":
        if len(argv) != 3:
            raise ValueError("--process-config requires exactly one argument: the config file path")
        return "process-config", argv[2]
    raise ValueError(
        f"Unknown argument: {argv[1]!r}. Usage:\n"
        f"  python ofac_main.py                          Launch GUI\n"
        f"  python ofac_main.py --watch                  Run background watcher\n"
        f"  python ofac_main.py --process-config <path>  Process one config file"
    )


def run_watch_mode():
    import ofac_watcher as watcher
    settings = ofac_settings.load_settings()
    watch_folder = settings.get("watch_folder")
    if not watch_folder:
        print("[main] No watch folder configured yet -- run the GUI setup screen first.")
        sys.exit(1)
    watcher.start_watching(watch_folder, script_path=os.path.abspath(__file__))


def run_process_config_mode(config_path):
    import ofac_watcher as watcher
    ensure_app_folders()
    db.init_database()

    def progress(current, total, file_name):
        print(f"[{current}/{total}] {file_name}")

    result = watcher.process_config_and_scan(config_path, progress_callback=progress)
    print(f"[main] {result}")
    if result["status"] == "error":
        sys.exit(1)


def run_gui_mode():
    ensure_app_folders()
    db.init_database()
    settings = ofac_settings.load_settings()

    if settings.get("watch_folder"):
        instance_check_or_focus(SCANNER_WINDOW_TITLE)
        from ofac_gui_main import launch_scanner_gui
        launch_scanner_gui()
    else:
        instance_check_or_focus(SETUP_WINDOW_TITLE)
        from ofac_gui_main import launch_setup_gui
        launch_setup_gui()


def main(argv=None):
    argv = argv if argv is not None else sys.argv
    try:
        mode, extra = _parse_args(argv)
    except ValueError as e:
        print(str(e))
        sys.exit(2)

    if mode == "watch":
        run_watch_mode()
    elif mode == "process-config":
        run_process_config_mode(extra)
    else:
        run_gui_mode()


if __name__ == "__main__":
    main()
