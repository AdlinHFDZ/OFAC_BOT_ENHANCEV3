"""
ofac_gui_main.py
Top-level GUI window. Two entry points, both called from ofac_main.py:
  launch_setup_gui()    -- first-run: pick a watch folder, then launches the scanner GUI
  launch_scanner_gui()  -- the main window: Scanner / Header Scan / History / Settings tabs

Threading pattern (matches your v2 code, which already used it correctly):
every long-running action (scan, header extraction) runs in a background
thread so the UI stays responsive; every UI update FROM that thread goes
through `root.after(0, lambda: ...)`, since tkinter widgets can only be
touched from the main thread.

TEST COVERAGE NOTE: same situation as ofac_gui_tab_common.py -- no tkinter
in this environment, syntax-checked only. Smoke-test on a real machine:
launch, confirm the setup screen writes settings correctly, confirm both
scan and header-extract flows run end to end against a small real file.
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *

from ofac_constants import ensure_app_folders, company_output_folder, SETUP_WINDOW_TITLE, SCANNER_WINDOW_TITLE
import ofac_database as db
import ofac_header_config as header_config
import ofac_gui_helpers as gh
import ofac_settings
from ofac_gui_tab_common import ScanStyleTab

try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


def _make_root_window():
    """
    Creates the root window with drag-and-drop support if tkinterdnd2 is
    installed, falling back to a plain ttkbootstrap window otherwise (the
    app works fully either way -- drag-and-drop is a convenience on top of
    the existing file list, not a required input path).

    Combining ttkbootstrap's Window with tkinterdnd2's DnD capability needs
    a specific mixin pattern (both subclass tkinter.Tk; DnD support is added
    by loading a Tcl extension into that Tk instance via
    TkinterDnD._require). This is a known community pattern for combining
    the two libraries, but could not be exercised in the environment this
    was built in -- verify a drag-and-drop actually works as the first
    smoke test on a real machine.
    """
    if not DND_AVAILABLE:
        return tb.Window()

    class DnDWindow(tb.Window, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            tb.Window.__init__(self, *args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)

    return DnDWindow()


# ==================== SETUP GUI (first run) ====================

class SetupGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(SETUP_WINDOW_TITLE)
        self.root.geometry("600x300")

        frame = tb.Frame(root, padding=30)
        frame.pack(fill=BOTH, expand=YES)

        tb.Label(frame, text="OFAC Scanner Setup", font=("Helvetica", 16, "bold")).pack(pady=(0, 20))
        tb.Label(frame, text="Watch Folder Path:").pack(anchor=W)

        row = tb.Frame(frame)
        row.pack(fill=X, pady=(5, 20))
        self.folder_var = tk.StringVar()
        tb.Entry(row, textvariable=self.folder_var, bootstyle="info").pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        tb.Button(row, text="Browse", command=self._browse, bootstyle="secondary").pack(side=RIGHT)

        tb.Button(frame, text="Save & Launch", command=self._save_and_launch, bootstyle="success", width=20).pack()

    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_var.set(path)

    def _save_and_launch(self):
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder.")
            return
        ofac_settings.save_settings({"watch_folder": folder, "theme": "flatly"})
        self.root.destroy()
        launch_scanner_gui()


def launch_setup_gui():
    root = _make_root_window()
    SetupGUI(root)
    root.mainloop()


# ==================== MAIN SCANNER GUI ====================

class ScannerMainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(SCANNER_WINDOW_TITLE)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass
        self.root.minsize(1000, 650)

        self.settings = ofac_settings.load_settings()
        try:
            self.root.style.theme_use(self.settings.get("theme", "flatly"))
        except Exception:
            pass

        self.watch_folder = self.settings.get("watch_folder")
        self.output_root = ofac_settings.get_output_root(self.settings)

        notebook = tb.Notebook(root)
        notebook.pack(fill=BOTH, expand=YES, padx=8, pady=8)

        scan_frame_holder = tb.Frame(notebook)
        notebook.add(scan_frame_holder, text="Scanner")
        self.scan_tab = ScanStyleTab(
            scan_frame_holder, mode="scan",
            on_run_now=self._handle_scan_run_now,
            on_queue_for_watcher=self._handle_scan_queue_for_watcher,
            on_stop=self._handle_scan_stop,
            get_watch_folder=lambda: self.watch_folder,
        )
        self.scan_tab.frame.pack(fill=BOTH, expand=YES)

        header_frame_holder = tb.Frame(notebook)
        notebook.add(header_frame_holder, text="Header Scan")
        self.header_tab = ScanStyleTab(
            header_frame_holder, mode="header_extract",
            on_extract_headers=self._handle_extract_headers,
            get_watch_folder=lambda: self.watch_folder,
        )
        self.header_tab.frame.pack(fill=BOTH, expand=YES)

        history_frame = tb.Frame(notebook)
        notebook.add(history_frame, text="History")
        self._build_history_tab(history_frame)

        settings_frame = tb.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        self._build_settings_tab(settings_frame)

        self._scan_stop_flags = {}  # run_id -> {"stopped": bool}, per in-flight scan

        self.root.after(2000, self._auto_refresh_loop)

    # ------------------------------------------------------------- Scan tab
    def _handle_scan_run_now(self, tab):
        company_code = tab.get_company_code()
        files = tab.get_selected_files()
        selected_passwords = tab.get_selected_passwords()
        date_str = tab.get_date_string()
        tab.log(f"Starting scan for {company_code}, {len(files)} file(s)...")

        def worker():
            stop_state = {"stopped": False}
            try:
                header_sets = header_config.load_company_headers(company_code)
                # (label, password) tuples for ofac_password_retry -- label ==
                # password now that the vault stores plain values, see
                # ofac_password_vault.py's docstring for why.
                password_entries = [(pwd, pwd) for pwd in selected_passwords]

                date_display = date_str.replace("-", "")
                output_folder = company_output_folder(date_display, company_code, output_root=self.output_root)
                csv_folder = os.path.join(output_folder, "CSVs")
                archived_folder = os.path.join(output_folder, "Archived")
                unzipped_folder = os.path.join(output_folder, "Unzipped")
                compiled_folder = os.path.join(output_folder, "Compiled")
                for d in [csv_folder, archived_folder, unzipped_folder, compiled_folder]:
                    os.makedirs(d, exist_ok=True)

                run_id = db.try_start_run(company_code, date_str, "manual",
                                          os.environ.get("USERNAME", "user"), output_folder, len(files))
                if run_id is None:
                    self.root.after(0, lambda: tab.log(
                        f"Another run for {company_code} / {date_str} is already in progress. Try again shortly."
                    ))
                    return

                self._scan_stop_flags[run_id] = stop_state

                import ofac_scanner_engine as scanner
                job = scanner.ScanJob(
                    run_id=run_id, company_code=company_code, csv_folder=csv_folder,
                    archived_folder=archived_folder, unzipped_folder=unzipped_folder,
                    passwords=password_entries, stop_flag=lambda: stop_state["stopped"],
                )
                file_paths = [os.path.join(self.watch_folder, f) for f in files]

                def progress(current, total, file_name):
                    self.root.after(0, lambda: (tab.update_progress(current, total), tab.log(f"[{current}/{total}] {file_name}")))

                files_processed, files_failed = scanner.run_scan_job(job, file_paths, header_sets, password_entries, progress)
                status = db.RUN_STATUS_STOPPED if stop_state["stopped"] else (
                    db.RUN_STATUS_COMPLETED if files_failed == 0 else db.RUN_STATUS_FAILED
                )
                db.finish_run(run_id, status, files_processed=files_processed, files_failed=files_failed)

                import ofac_compiler as compiler
                compile_result = compiler.compile_company_date(company_code, date_str, date_display, compiled_folder)

                self.root.after(0, lambda: tab.log(
                    f"Done. Processed {files_processed}, failed {files_failed}. "
                    f"Compiled report: {compile_result['total_rows']} rows across {compile_result['part_count']} file(s). "
                    f"Location: {compiled_folder}"
                ))
            except Exception as e:
                self.root.after(0, lambda: tab.log(f"Error: {e}"))
            finally:
                self.root.after(0, tab.scan_finished)
                self.root.after(0, tab.refresh_file_list)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_scan_queue_for_watcher(self, tab):
        company_code = tab.get_company_code()
        files = tab.get_selected_files()
        selected_passwords = tab.get_selected_passwords()
        date_str = tab.get_date_string()

        config = gh.build_watcher_config(
            company_code, date_str, files, selected_passwords,
            os.environ.get("USERNAME", "user"), self.watch_folder,
        )
        import time
        config_path = os.path.join(self.watch_folder, f"configuration_{int(time.time())}.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        tab.log(f"Queued: {os.path.basename(config_path)}. The watcher will pick this up automatically.")
        tab.refresh_file_list()

    def _handle_scan_stop(self, tab):
        for stop_state in self._scan_stop_flags.values():
            stop_state["stopped"] = True
        tab.log("Stop requested -- will halt after the current file finishes.")

    # ------------------------------------------------------- Header Scan tab
    def _handle_extract_headers(self, tab):
        company_code = tab.get_company_code()
        files = tab.get_selected_files()
        selected_passwords = tab.get_selected_passwords()
        tab.log(f"Extracting headers from {len(files)} file(s)...")

        def worker():
            try:
                password_entries = [(pwd, pwd) for pwd in selected_passwords]
                import ofac_header_extractor_engine as hee

                file_paths = [os.path.join(self.watch_folder, f) for f in files]

                def progress(current, total, file_name):
                    self.root.after(0, lambda: (tab.update_progress(current, total), tab.log(f"[{current}/{total}] {file_name}")))

                records, errors = hee.run_header_extraction(file_paths, password_entries, progress)

                import datetime as dt
                date_display = dt.datetime.now().strftime("%Y%m%d")
                output_folder = company_output_folder(date_display, company_code, output_root=self.output_root)
                os.makedirs(output_folder, exist_ok=True)
                report_path = os.path.join(output_folder, f"HeaderExtract_{date_display}_{company_code}.xlsx")
                hee.write_header_report(records, report_path)

                self.root.after(0, lambda: tab.log(
                    f"Done. Found {len(records)} header(s) across {len(files)} file(s), {len(errors)} error(s). "
                    f"Report: {report_path}"
                ))
                for err in errors:
                    self.root.after(0, lambda e=err: tab.log(f"  Error in {e['file']}: {e['message']}"))
            except Exception as e:
                self.root.after(0, lambda: tab.log(f"Error: {e}"))
            finally:
                self.root.after(0, tab.scan_finished)

        threading.Thread(target=worker, daemon=True).start()

    # --------------------------------------------------------------- shared
    def _auto_refresh_loop(self):
        if getattr(self.scan_tab, "auto_refresh_var", None) and self.scan_tab.auto_refresh_var.get():
            self.scan_tab.refresh_file_list()
        if getattr(self.header_tab, "auto_refresh_var", None) and self.header_tab.auto_refresh_var.get():
            self.header_tab.refresh_file_list()
        self.root.after(2000, self._auto_refresh_loop)

    # ------------------------------------------------------------- History
    def _build_history_tab(self, parent):
        frame = tb.Frame(parent, padding=10)
        frame.pack(fill=BOTH, expand=YES)

        tb.Button(frame, text="Refresh", command=lambda: self._load_history(tree), bootstyle="primary").pack(anchor=W, pady=(0, 8))

        columns = ("run_id", "company", "date", "status", "processed", "failed", "started")
        tree = tb.Treeview(frame, columns=columns, show="headings", bootstyle="primary")
        headings = {
            "run_id": "Run ID", "company": "Company", "date": "Date", "status": "Status",
            "processed": "Processed", "failed": "Failed", "started": "Started At",
        }
        for col, text in headings.items():
            tree.heading(col, text=text)
            tree.column(col, width=110)
        tree.pack(fill=BOTH, expand=YES)

        self._load_history(tree)

    def _load_history(self, tree):
        for item in tree.get_children():
            tree.delete(item)
        for run in db.get_recent_runs(limit=200):
            tree.insert("", tk.END, values=(
                run["run_id"], run["company_code"], run["email_received_date"], run["status"],
                run["files_processed"], run["files_failed"], run["started_at"],
            ))

    # ------------------------------------------------------------- Settings
    def _build_settings_tab(self, parent):
        frame = tb.Frame(parent, padding=20)
        frame.pack(fill=BOTH, expand=YES)

        tb.Label(frame, text="Watch Folder", font=("Helvetica", 11, "bold")).pack(anchor=W)
        tb.Label(frame, text="Where incoming files to be scanned get dropped.",
                foreground="gray").pack(anchor=W, pady=(0, 4))
        folder_row = tb.Frame(frame)
        folder_row.pack(fill=X, pady=(0, 20))
        self.watch_folder_var = tk.StringVar(value=self.watch_folder or "")
        tb.Entry(folder_row, textvariable=self.watch_folder_var, bootstyle="info").pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        tb.Button(folder_row, text="Change", command=self._change_watch_folder, bootstyle="warning").pack(side=RIGHT)

        tb.Label(frame, text="Output Folder", font=("Helvetica", 11, "bold")).pack(anchor=W)
        tb.Label(frame, text="Where scan results and compiled reports are written. Leave blank to use "
                            "the default (inside the app data folder). Point this at a shared drive if "
                            "reports need to be accessible to others -- this can be different from where "
                            "the app's database lives, and that's the recommended setup.",
                foreground="gray", wraplength=600, justify=LEFT).pack(anchor=W, pady=(0, 4))
        output_row = tb.Frame(frame)
        output_row.pack(fill=X, pady=(0, 5))
        self.output_folder_var = tk.StringVar(value=self.settings.get("output_folder", ""))
        tb.Entry(output_row, textvariable=self.output_folder_var, bootstyle="info").pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        tb.Button(output_row, text="Change", command=self._change_output_folder, bootstyle="warning").pack(side=RIGHT)
        default_hint_row = tb.Frame(frame)
        default_hint_row.pack(fill=X, pady=(0, 20))
        tb.Label(default_hint_row, text=f"Current default if left blank: {ofac_settings.get_output_root({})}",
                foreground="gray", font=("Helvetica", 8)).pack(side=LEFT)
        tb.Button(default_hint_row, text="Open Output Folder", command=self._open_output_folder, bootstyle="info").pack(side=RIGHT)

        tb.Label(frame, text="Theme", font=("Helvetica", 11, "bold")).pack(anchor=W)
        theme_row = tb.Frame(frame)
        theme_row.pack(fill=X, pady=(5, 20))
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "flatly"))
        themes = ["flatly", "darkly", "cyborg", "journal", "litera", "minty", "solar", "superhero"]
        tb.Combobox(theme_row, values=themes, textvariable=self.theme_var, bootstyle="primary").pack(side=LEFT, fill=X, expand=True)
        tb.Button(theme_row, text="Apply", command=self._apply_theme, bootstyle="info").pack(side=RIGHT, padx=(5, 0))

        tb.Button(frame, text="Save Settings", command=self._save_settings_tab, bootstyle="success", width=20).pack(pady=10)

    def _change_output_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.output_folder_var.set(path)

    def _open_output_folder(self):
        target = self.output_folder_var.get().strip() or self.output_root
        os.makedirs(target, exist_ok=True)
        try:
            os.startfile(target)
        except AttributeError:
            messagebox.showinfo("Output Folder", f"Output folder: {target}")
        except OSError as e:
            messagebox.showerror("Error", f"Could not open {target}: {e}")

    def _change_watch_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.watch_folder_var.set(path)

    def _apply_theme(self):
        try:
            self.root.style.theme_use(self.theme_var.get())
        except Exception as e:
            messagebox.showerror("Theme Error", str(e))

    def _save_settings_tab(self):
        new_watch_folder = self.watch_folder_var.get().strip()
        if not new_watch_folder or not os.path.isdir(new_watch_folder):
            messagebox.showerror("Error", "Please select a valid watch folder.")
            return

        new_output_folder = self.output_folder_var.get().strip()
        if new_output_folder and not os.path.isdir(new_output_folder):
            create = messagebox.askyesno(
                "Create folder?", f"{new_output_folder} doesn't exist yet. Create it?"
            )
            if create:
                os.makedirs(new_output_folder, exist_ok=True)
            else:
                return

        self.watch_folder = new_watch_folder
        self.settings["watch_folder"] = new_watch_folder
        self.settings["output_folder"] = new_output_folder  # "" means "use the default"
        self.settings["theme"] = self.theme_var.get()
        ofac_settings.save_settings(self.settings)

        self.output_root = ofac_settings.get_output_root(self.settings)
        messagebox.showinfo("Settings", "Settings saved.")


def launch_scanner_gui():
    ensure_app_folders()
    db.init_database()
    root = _make_root_window()
    ScannerMainWindow(root)
    root.mainloop()
