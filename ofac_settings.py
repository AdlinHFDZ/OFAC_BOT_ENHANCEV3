"""
ofac_settings.py
Loads and saves the app-level settings file (watch folder, output folder,
theme). Single source of truth -- ofac_main.py, ofac_gui_main.py, and
ofac_watcher.py all import this instead of each reading/parsing
app_settings.json separately, which is what was happening before (a real
duplication risk: two independent copies of the same load/save logic that
could silently drift apart).

Output folder is deliberately a user-configurable *setting*, not a rigid
ofac_constants.py value derived only from an environment variable at import
time -- the database and config really should stay on local, reliable
storage (see ofac_database.py's docstring on why SQLite + network shares is
a bad combination), but the compiled reports people actually need to share
often belong somewhere else, like a network drive. Decoupling the two lets
you keep APP_ROOT local while pointing output wherever it needs to go.
"""

import os
import json

from ofac_constants import APP_SETTINGS_FILE, ensure_app_folders, OUTPUT_ROOT as DEFAULT_OUTPUT_ROOT


def load_settings():
    if os.path.exists(APP_SETTINGS_FILE):
        try:
            with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_settings(settings):
    ensure_app_folders()
    tmp_path = APP_SETTINGS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp_path, APP_SETTINGS_FILE)


def get_output_root(settings=None):
    """
    Returns the configured output root, falling back to the default
    (APP_ROOT/output) if the user hasn't explicitly set one. Accepts an
    already-loaded settings dict to avoid re-reading the file when the
    caller already has it (e.g. the GUI, which keeps settings in memory).
    """
    if settings is None:
        settings = load_settings()
    configured = settings.get("output_folder")
    return configured if configured else DEFAULT_OUTPUT_ROOT


def get_watch_folder(settings=None):
    if settings is None:
        settings = load_settings()
    return settings.get("watch_folder")
