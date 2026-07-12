# OFAC Scanner — Full Setup & Usage Guide

This covers everything: what to install, where every file goes, how to generate your config data for real, and how to run the app day to day.

---

## 1. Three folders — don't mix these up

This is the part most likely to cause confusion, so it comes first.

| Folder | What it is | Example |
|---|---|---|
| **Code folder** | Where all the `.py` files live. You run the app from here. | `C:\OFAC_Scanner\app\` |
| **App data folder** (`APP_ROOT`) | Auto-created by the app, right next to the code. Holds your config (headers/passwords), the database, and every scan's output. | `C:\OFAC_Scanner\app\OFAC_App\` (default — see below to change it) |
| **Watch folder** | Where incoming files-to-be-scanned get dropped by whoever sends them to you. You pick this during first-run setup. | `\\shared\OFAC_Input\` or a local folder |

The **code folder** never changes once set up. The **app data folder** is where everything the app *creates* lives (database, generated reports, your header/password config) — by default it sits right inside the code folder, so the whole thing is self-contained: copy `OFAC_Scanner\app\` somewhere else and your data comes with it. The **watch folder** is just an inbox you point the app at, and can be anywhere (including a shared network location).

To put the app data folder somewhere else instead (e.g. so replacing/reinstalling the code folder never touches your data, or to keep it in your user profile), set an environment variable before running anything:
```
setx OFAC_APP_ROOT "C:\Users\<you>\OFAC_App"
```
(Close and reopen your terminal after running `setx` for it to take effect.)

---

## 2. Requirements

**Python:** 3.10 or newer (3.11 or 3.12 recommended). Get it from python.org — check "Add Python to PATH" during install.

**7-Zip:** needed for `.zip` / `.7z` / `.rar` archive support. Install from 7-zip.org. The app expects it at `C:\Program Files\7-zip\7z.exe` by default; if you installed it elsewhere, set:
```
setx SEVEN_ZIP_PATH "D:\Tools\7-Zip\7z.exe"
```

**Python packages:** everything is listed in `requirements.txt` inside the code folder.

---

## 3. First-time setup — do these steps in order

### Step 1 — Put the code in place
Copy every file from the delivered `app/` folder into your code folder, e.g. `C:\OFAC_Scanner\app\`. **All files must stay together in this one folder** — they refer to each other by name (`ofac_database.py` imports `ofac_constants.py`, etc.) and that only works if they're side by side, not in subfolders.

### Step 2 — Install Python packages
Open a terminal (Command Prompt or PowerShell) in the code folder:
```
cd C:\OFAC_Scanner\app
pip install -r requirements.txt
```
A virtual environment is optional but recommended if you have other Python projects on this machine:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3 — Verify the environment works
Run every test file. Each should print `ALL ... TESTS PASSED` at the end:
```
python test_database.py
python test_header_detection.py
python test_data_cleaning.py
python test_password_retry.py
python test_password_vault.py
python test_watcher.py
python test_main.py
python test_gui_helpers.py
python test_extraction_engine.py
python test_scanner_engine.py
python test_compiler.py
python test_header_extractor_engine.py
python test_settings.py
```
If any of these fail, stop here and fix it before continuing — everything after this step depends on the environment being correct. (`test_scanner_engine.py` and a couple of others create real temporary files/folders on your machine and clean up after themselves — that's expected.)

### Step 4 — Generate your company header config
This converts the header-synonym library into the JSON files the app actually uses.
```
python parse_headers.py
```
This creates a `generated_headers` folder (inside your code folder) containing `defaults.json`, a `companies/` folder with 107 files, plus `conversion_report.md` — **read that report**, it flags 10 companies with no name column, 5 with non-standard layouts, and 4 with explicitly-unsafe generic terms that need your judgment call.

### Step 5 — Move the generated headers into the app data folder
First, make the app data folder exist by launching the app once (see Step 7) — or create the folders manually:
```
app\OFAC_App\config\headers\
app\OFAC_App\config\headers\companies\
```
(If you've set `OFAC_APP_ROOT` to somewhere else, use that location instead — see Section 1.)

Then copy:
- `generated_headers\defaults.json` → `OFAC_App\config\headers\defaults.json`
- everything in `generated_headers\companies\` → `OFAC_App\config\headers\companies\`

### Step 6 — Migrate your company passwords
```
python migrate_passwords_to_vault.py
```
This reads `company_passwords_source.tsv` (already in the code folder) and creates one plain JSON file per company with a password, directly in your app data folder under `config\passwords\companies\`. No encryption, no per-machine step — passwords are stored as plain, readable text on purpose, so the GUI can show you the actual value when picking which one to use for a file. See "A note on password storage" in Section 4 below if you want the reasoning.

### Step 7 — First launch
```
python ofac_main.py
```
Since no settings exist yet, the **Setup screen** appears — pick or create your watch folder, then **Save & Launch**. The main window opens with four tabs: Scanner, Header Scan, History, Settings.

### Step 8 (optional) — Run the background watcher
If you want "Queue for Watcher" jobs to actually get picked up automatically, the watcher needs to be running as its own process:
```
python ofac_main.py --watch
```
Leave this running in a terminal, or set it up as a Windows Scheduled Task (Task Scheduler → Create Task → Trigger: "At log on" → Action: run `pythonw.exe` with argument `C:\OFAC_Scanner\app\ofac_main.py --watch`, using `pythonw.exe` instead of `python.exe` so no console window stays open).

---

## 4. Day-to-day usage

**Scanning files:** open the app, go to the **Scanner** tab. Pick a company code (type to search, or pick a suggestion), the date, and which password(s) to try. Get files into the list either by dropping them straight onto the file list (drag from Explorer — this copies them into your watch folder automatically and checks them for you) or by placing them in the watch folder yourself and hitting Refresh. Then either:
- **Run Scanner Now** — runs immediately, right in the app.
- **Queue for Watcher** — writes a small job file and returns instantly; the background watcher (Step 8) picks it up and runs it separately. Requires the watcher to actually be running.

**Adding a new company:** just type its code — no separate "register" step needed. It starts with default headers only and no passwords until you add some via **+ New Password**.

**A note on password storage:** company passwords are stored as plain, readable JSON — no encryption. This is deliberate: an earlier version encrypted them, but that meant the picker could only show a generic "Password 1", "Password 2", which made it hard to tell which stored password was actually the right one for a given file. Now the picker shows the real value directly. Trade-off: anyone with file access to your app data folder can read `config\passwords\companies\*.json` in plain text, and "Queue for Watcher" job files also carry the real password value. One thing that's still protected regardless: the run history/database never stores the raw password even though the vault itself doesn't encrypt — it keeps a masked version (e.g. `R**********A`) in the log, since that log is more likely to get shared or exported than the vault file itself.

**Onboarding a company you've never scanned before:** use the **Header Scan** tab first — it reports what columns exist in that company's files so you know what synonyms (if any) to add to its header config.

**Checking past runs:** the **History** tab, backed by the database — no more digging through dated folders.

**Changing the watch folder or theme:** the **Settings** tab.

---

## 5. Configuring where output goes

The **Settings** tab has a dedicated **Output Folder** field. Leave it blank to use the default (inside the app data folder, alongside the database) — or point it at a shared drive if compiled reports need to be accessible to others. This is intentionally separate from the app data folder itself: the database should stay on local, reliable storage, but reports usually need to live somewhere shared. A **"Open Output Folder"** button next to it jumps straight there, and after every scan the log tells you exactly where that run's compiled report landed.

If you're running the watcher (`--watch` mode) instead of using the GUI directly, it reads the same setting from `app_settings.json` automatically — no separate configuration needed there.

## 6. Where your output ends up

For a scan of `COMPANY_A` received on `2026-07-12`, using whichever output folder is configured (default shown below):
```
<output folder>\20260712\COMPANY_A\
  CSVs\        <- per-file/sheet extraction results
  Archived\    <- original input files, moved here after successful processing
  Unzipped\    <- extracted archive contents, if any
  Compiled\    <- the final report: OFAC_ABS_Log_20260712_COMPANY_A_1.xlsx
```
The Compiled report is cumulative — running the same company+date again later adds to the same report rather than creating a separate one. It's also resilient to partial failures: if one file in a batch errors out, every other file that succeeded still gets compiled — a single bad file no longer excludes the rest of that run's output.

**What the `FILE_PATH` column in your compiled report actually means:** it's the file's location in the *watch folder* at the moment it was read — not its final Archived location. Processing happens before the move to Archived, so that's the value that gets baked into the output. Practically: that exact path stops existing shortly after (the file moves to `Archived\` right after), so `FILE_PATH` is best read as "which source file this record came from" (by name) rather than "where to find it right now" — for that, look in that date/company's `Archived\` folder for the same filename.

---

## 7. What every file actually is

**Core app (17 files — required, always together in the code folder)**
| File | What it does |
|---|---|
| `ofac_constants.py` | Every path, file-type list, and threshold — the one place to change a setting |
| `ofac_file_utils.py` | Safe file operations: unique filenames, atomic writes, retrying moves |
| `ofac_database.py` | SQLite layer: run tracking, the concurrency lock, per-file logging, history |
| `ofac_header_config.py` | Loads/merges company header JSON (defaults + per-company overrides) |
| `ofac_password_vault.py` | Per-company password storage — plain JSON, no encryption (see Section 4) |
| `ofac_header_detection.py` | Finds header rows/columns — the core "smart" detection logic |
| `ofac_data_cleaning.py` | Name cleaning, sex normalization, date parsing |
| `ofac_password_retry.py` | "Try each password, stop at first success" logic |
| `ofac_extraction_engine.py` | Builds the extracted output using the detection + cleaning above |
| `ofac_scanner_engine.py` | Reads actual Excel/CSV/archive files, including big-file chunking |
| `ofac_compiler.py` | Builds the cumulative compiled report per company+date |
| `ofac_header_extractor_engine.py` | The Header Scan tab's backend (company onboarding tool) |
| `ofac_watcher.py` | Watches for queued jobs, runs them, handles the concurrency retry |
| `ofac_main.py` | Command-line entry point (`--watch`, `--process-config`, or GUI) |
| `ofac_gui_helpers.py` | Pure logic behind the GUI (validation, filtering, config building) |
| `ofac_gui_tab_common.py` | The shared Scan/Header-Scan tab layout (your wireframe) |
| `ofac_gui_main.py` | Main window: setup screen, all four tabs, wiring to the engines |
| `ofac_settings.py` | Loads/saves app settings (watch folder, output folder, theme) — one source of truth used by the GUI, the watcher, and the entry point |

**One-time setup tools (run once during setup, not part of ongoing use)**
| File | What it does |
|---|---|
| `parse_headers.py` | Converts `company_headers_source.md` into the JSON config (Step 4) |
| `company_headers_source.md` | Source data for the above — the header synonym library |
| `migrate_passwords_to_vault.py` | Converts `company_passwords_source.tsv` into per-company password JSON files (Step 6) |
| `company_passwords_source.tsv` | Source data for the above — your company password list |

**Troubleshooting tool**
| File | What it does |
|---|---|
| `diagnose_compile.py` | Run `python diagnose_compile.py <COMPANY_CODE> <YYYY-MM-DD>` when a compiled report isn't appearing — shows every run's status, every file's result, and attempts the compile directly to surface any real error with a full traceback |

**Test suites (optional, but run them once per Step 3 — never needed for normal use afterward)**
`test_database.py`, `test_header_detection.py`, `test_data_cleaning.py`, `test_password_retry.py`, `test_password_vault.py`, `test_watcher.py`, `test_main.py`, `test_gui_helpers.py`, `test_extraction_engine.py`, `test_scanner_engine.py`, `test_compiler.py`, `test_header_extractor_engine.py`, `test_settings.py`

---

## 8. If something goes wrong

- **A test fails at Step 3** → don't proceed. Read the assertion message; it will name exactly what broke.
- **"Another run for X is already in progress"** → expected behavior, not a bug — it means two scans for the same company+date tried to run at once. The second one will retry automatically for a while; if it gives up, just try again shortly.
- **GUI looks broken or a widget errors out on launch** → this is the one part that couldn't be tested during development (no display in that environment) — check the error message and cross-reference `ofac_gui_tab_common.py` / `ofac_gui_main.py`.
- **Dragging a file onto the app does nothing** → confirm `tkinterdnd2` actually installed correctly (`pip show tkinterdnd2`); if it's missing, the app still works fine, you just place files in the watch folder manually and hit Refresh instead. This is the single least-tested code path in the whole app — worth checking first if anything GUI-related seems off.
- **7z/archive files fail to extract** → confirm 7-Zip is actually installed and `SEVEN_ZIP_PATH` points at the real `7z.exe`.
- **Individual files extracted fine (CSVs/Archived look right) but no Compiled report appears** → two separate real bugs were found and fixed here, in order:
  1. A run used to be marked "failed" the moment even one file in a batch errored, which silently excluded every other successfully-processed file in that same run from compiling.
  2. Even with that fixed, compiling could still fail with `SchemaError: type Int64 is incompatible with expected type String` — polars guesses each output CSV's column types independently when reading it back, and a sheet named purely with digits (e.g. `"2601"`) or a numeric company code (e.g. `"733"`) would get read as a number in that file but text in others, so combining them failed. Fixed by forcing every output column to text on read, not just `POLICY_NUMBER` (which already had this protection).

  If a compiled report still doesn't appear after updating, run `diagnose_compile.py <COMPANY_CODE> <YYYY-MM-DD>` (included in the code folder) — it shows every run's status, every file's individual result, and attempts the actual compile so any remaining error prints a full traceback instead of a generic message.
