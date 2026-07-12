"""
ofac_gui_tab_common.py
Builds the shared two-column layout confirmed in the wireframe:

    +--------------+----------------------------------------+
    | Company Code |  File Filters + File List + Refresh     |
    |  Selection   |  (auto-refresh on by default)           |
    +--------------+                                          |
    |    Date      |                                          |
    +--------------+----------------------------------------+
    |              |  [Action buttons]                       |
    |  Password    +----------------------------------------+
    |    List      |                                          |
    |  (scrolls    |           Log Output                    |
    |  internally) |                                          |
    +--------------+----------------------------------------+

Used by both the Scan tab (3 action buttons: Run Now / Queue for Watcher /
Stop) and the Header Scan tab (1 action button: Extract Headers) -- built
once and parameterized, rather than duplicated twice, since the two tabs are
otherwise identical. This class only builds widgets and exposes simple
getter/setter methods; all business logic (validation, config building,
search filtering) lives in ofac_gui_helpers.py and is called from here, not
reimplemented here.

TEST COVERAGE NOTE: tkinter isn't installed in the environment this was
built in (no network access to get python3-tk -- see the project's other
"not run here" notes for the same underlying constraint). This file is
syntax-checked only. Every non-trivial decision it makes (what counts as a
valid request, how to filter/search, how to build the watcher config) is
delegated to ofac_gui_helpers.py, which IS fully tested. Smoke-test this
file on a real machine before trusting it: open both tabs, confirm the file
list/password list populate and scroll independently, and confirm Run Now /
Queue for Watcher / Extract Headers all produce the expected calls.
"""

import os
import shutil
import tkinter as tk
from datetime import date, datetime

import ttkbootstrap as tb
from ttkbootstrap.constants import *

try:
    from ttkbootstrap.widgets import ScrolledText
except ImportError:
    from tkinter.scrolledtext import ScrolledText

try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

import ofac_gui_helpers as gh
import ofac_password_vault as vault
from ofac_file_utils import get_unique_save_path


class ScanStyleTab:
    """
    mode: "scan" or "header_extract" -- controls which action button(s) appear
    and what happens when they're clicked.
    on_run_now, on_queue_for_watcher, on_extract_headers: callbacks provided
    by the caller (ofac_gui_main.py), so this class doesn't need to know
    about the scanner/watcher/header-extractor engines directly.
    """

    def __init__(self, parent, mode, on_run_now=None, on_queue_for_watcher=None,
                 on_extract_headers=None, on_stop=None, get_watch_folder=None):
        self.parent = parent
        self.mode = mode
        self.on_run_now = on_run_now
        self.on_queue_for_watcher = on_queue_for_watcher
        self.on_extract_headers = on_extract_headers
        self.on_stop = on_stop
        self.get_watch_folder = get_watch_folder or (lambda: None)

        self.file_vars = {}          # filename -> tk.IntVar (checkbox state)
        self.password_vars = {}      # password value -> tk.IntVar (checkbox state)

        self.frame = tb.Frame(parent)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=0, minsize=260)  # sidebar, fixed-ish width
        self.frame.grid_columnconfigure(1, weight=1)               # main area, fills remaining space

        self._build_sidebar()
        self._build_main_area()

        self.refresh_file_list()

    # ---------------------------------------------------------------- sidebar
    def _build_sidebar(self):
        sidebar = tb.Frame(self.frame)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        sidebar.grid_rowconfigure(2, weight=1)  # password list gets the remaining vertical space
        sidebar.grid_columnconfigure(0, weight=1)

        # --- Company Code Selection ---
        code_frame = tb.LabelFrame(sidebar, text="Company Code Selection")
        code_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.company_var = tk.StringVar()
        self.company_var.trace_add("write", lambda *a: self._on_company_changed())
        self.company_entry = tb.Entry(code_frame, textvariable=self.company_var, bootstyle="info")
        self.company_entry.pack(fill=X, padx=8, pady=8)

        self.company_suggestions = tk.Listbox(code_frame, height=4, exportselection=False)
        self.company_suggestions.pack(fill=X, padx=8, pady=(0, 8))
        self.company_suggestions.bind("<<ListboxSelect>>", self._on_company_suggestion_selected)
        self._refresh_company_suggestions()

        # --- Date ---
        date_frame = tb.LabelFrame(sidebar, text="Date")
        date_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        try:
            from ttkbootstrap.widgets import DateEntry
            self.date_entry = DateEntry(date_frame, width=16)
            self.date_entry.set_date(date.today())
        except ImportError:
            self.date_entry = tk.Entry(date_frame, width=16)
            self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.pack(padx=8, pady=8)

        # --- Password List (fills remaining sidebar height, scrolls internally) ---
        pass_frame = tb.LabelFrame(sidebar, text="Password List")
        pass_frame.grid(row=2, column=0, sticky="nsew")
        pass_frame.grid_rowconfigure(1, weight=1)
        pass_frame.grid_columnconfigure(0, weight=1)

        search_row = tb.Frame(pass_frame)
        search_row.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.password_search_var = tk.StringVar()
        self.password_search_var.trace_add("write", lambda *a: self._render_password_list())
        tb.Entry(search_row, textvariable=self.password_search_var, bootstyle="info").pack(fill=X)

        pass_canvas = tk.Canvas(pass_frame, highlightthickness=0)
        pass_scrollbar = tb.Scrollbar(pass_frame, orient="vertical", command=pass_canvas.yview)
        pass_canvas.configure(yscrollcommand=pass_scrollbar.set)
        pass_canvas.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 4))
        pass_scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 4))

        self.password_inner = tb.Frame(pass_canvas)
        pass_canvas.create_window((0, 0), window=self.password_inner, anchor="nw")
        self.password_inner.bind("<Configure>", lambda e: pass_canvas.configure(scrollregion=pass_canvas.bbox("all")))
        pass_canvas.bind("<Configure>", lambda e: pass_canvas.itemconfig(1, width=e.width))
        pass_canvas.bind_all("<MouseWheel>", lambda e: pass_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"), add="+")

        pass_btn_row = tb.Frame(pass_frame)
        pass_btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        tb.Button(pass_btn_row, text="+ New Password", command=self._add_new_password, bootstyle="success").pack(side=LEFT)

    def _on_company_changed(self):
        self._render_password_list()
        self._refresh_company_suggestions()

    def _refresh_company_suggestions(self):
        all_codes = gh.list_known_company_codes()
        matches = gh.filter_by_search(all_codes, self.company_var.get())
        self.company_suggestions.delete(0, tk.END)
        for code in matches[:20]:
            self.company_suggestions.insert(tk.END, code)

    def _on_company_suggestion_selected(self, event):
        selection = self.company_suggestions.curselection()
        if selection:
            self.company_var.set(self.company_suggestions.get(selection[0]))

    def _render_password_list(self):
        for widget in self.password_inner.winfo_children():
            widget.destroy()
        self.password_vars.clear()

        company_code = self.company_var.get().strip()
        if not company_code:
            tb.Label(self.password_inner, text="Enter a company code first", foreground="gray").pack(pady=10)
            return

        try:
            passwords = vault.list_passwords(company_code)
        except Exception as e:
            tb.Label(self.password_inner, text=f"Could not load passwords: {e}", foreground="red").pack(pady=10)
            return

        filtered = gh.filter_by_search(passwords, self.password_search_var.get())

        if not passwords:
            tb.Label(self.password_inner, text="No passwords for this company yet", foreground="gray").pack(pady=10)
            return
        if not filtered:
            tb.Label(self.password_inner, text="No passwords match your search", foreground="gray").pack(pady=10)
            return

        for password_value in filtered:
            var = tk.IntVar(value=0)
            self.password_vars[password_value] = var
            row = tb.Frame(self.password_inner)
            row.pack(fill=X, pady=1)
            tb.Checkbutton(row, variable=var, bootstyle="primary").pack(side=LEFT, padx=4)
            tb.Label(row, text=password_value, anchor="w").pack(side=LEFT, fill=X, expand=True)

    def _add_new_password(self):
        company_code = self.company_var.get().strip()
        if not company_code:
            tk.messagebox.showwarning("Warning", "Enter a company code first.")
            return

        dialog = tb.Toplevel(self.parent)
        dialog.title("New Password")
        dialog.geometry("320x150")
        dialog.attributes("-topmost", True)
        tb.Label(dialog, text=f"New password for {company_code}:").pack(pady=8)
        pwd_entry = tb.Entry(dialog, show="*")
        pwd_entry.pack(pady=4, padx=10, fill=X)

        def save():
            pwd = pwd_entry.get().strip()
            if pwd:
                vault.add_password(company_code, pwd)
                self._render_password_list()
                dialog.destroy()

        tb.Button(dialog, text="Save", command=save, bootstyle="success").pack(pady=10)
        dialog.transient(self.parent)
        dialog.grab_set()

    # ------------------------------------------------------------- main area
    def _build_main_area(self):
        main = tb.Frame(self.frame)
        main.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        main.grid_rowconfigure(0, weight=2)  # file list panel
        main.grid_rowconfigure(2, weight=1)  # log output panel
        main.grid_columnconfigure(0, weight=1)

        self._build_file_list_panel(main)
        self._build_button_bar(main)
        self._build_log_panel(main)

    def _build_file_list_panel(self, main):
        panel = tb.LabelFrame(main, text="Files")
        panel.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        filter_row = tb.Frame(panel)
        filter_row.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self.filter_excel = tk.BooleanVar(value=True)
        self.filter_text = tk.BooleanVar(value=True)
        self.filter_archive = tk.BooleanVar(value=True)
        for label, var in [("Excel", self.filter_excel), ("CSV/Text", self.filter_text), ("Archive", self.filter_archive)]:
            tb.Checkbutton(filter_row, text=label, variable=var, bootstyle="primary",
                           command=self.refresh_file_list).pack(side=LEFT, padx=(0, 10))
        tb.Button(filter_row, text="Refresh", command=self.refresh_file_list, bootstyle="secondary").pack(side=LEFT, padx=(10, 0))
        self.auto_refresh_var = tk.BooleanVar(value=True)  # confirmed default: on
        tb.Checkbutton(filter_row, text="Auto-refresh", variable=self.auto_refresh_var, bootstyle="primary").pack(side=LEFT, padx=(10, 0))
        if DND_AVAILABLE:
            tb.Label(filter_row, text="(or drag files here)", foreground="gray").pack(side=LEFT, padx=(10, 0))

        list_canvas = tk.Canvas(panel, highlightthickness=0)
        list_scrollbar = tb.Scrollbar(panel, orient="vertical", command=list_canvas.yview)
        list_canvas.configure(yscrollcommand=list_scrollbar.set)
        list_canvas.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        list_scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 8))
        self._register_drop_target(list_canvas)

        self.file_list_inner = tb.Frame(list_canvas)
        list_canvas.create_window((0, 0), window=self.file_list_inner, anchor="nw")
        self.file_list_inner.bind("<Configure>", lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_canvas.bind("<Configure>", lambda e: list_canvas.itemconfig(1, width=e.width))

        select_row = tb.Frame(panel)
        select_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        tb.Button(select_row, text="Select All", command=self._select_all_files, bootstyle="info").pack(side=LEFT, padx=(0, 5))
        tb.Button(select_row, text="Clear All", command=self._clear_all_files, bootstyle="secondary").pack(side=LEFT)

    def _build_button_bar(self, main):
        bar = tb.Frame(main)
        bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        if self.mode == "scan":
            tb.Button(bar, text="Run Scanner Now", command=self._handle_run_now, bootstyle="primary", width=18).pack(side=LEFT, padx=(0, 5))
            tb.Button(bar, text="Queue for Watcher", command=self._handle_queue_for_watcher, bootstyle="warning", width=18).pack(side=LEFT, padx=5)
            self.stop_btn = tb.Button(bar, text="Stop", command=self._handle_stop, bootstyle="danger", width=12, state=DISABLED)
            self.stop_btn.pack(side=LEFT, padx=5)
        else:
            tb.Button(bar, text="Extract Headers", command=self._handle_extract_headers, bootstyle="success", width=18).pack(side=LEFT)

        self.progress = tb.Progressbar(bar, bootstyle="success", mode="determinate")
        self.progress.pack(side=LEFT, fill=X, expand=True, padx=(15, 0))

    def _build_log_panel(self, main):
        panel = tb.LabelFrame(main, text="Log Output")
        panel.grid(row=2, column=0, sticky="nsew")
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        self.log_text = ScrolledText(panel, wrap=WORD)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    # ------------------------------------------------------------ file list
    def refresh_file_list(self):
        watch_folder = self.get_watch_folder()
        if not watch_folder or not os.path.isdir(watch_folder):
            return

        previously_checked = {f for f, v in self.file_vars.items() if v.get() == 1}
        for widget in self.file_list_inner.winfo_children():
            widget.destroy()
        self.file_vars.clear()

        try:
            all_names = [f for f in os.listdir(watch_folder)
                        if os.path.isfile(os.path.join(watch_folder, f)) and not f.endswith(".json")]
        except OSError as e:
            self.log(f"Could not list watch folder: {e}")
            return

        filtered = gh.filter_files_by_extension(
            sorted(all_names), self.filter_excel.get(), self.filter_text.get(), self.filter_archive.get()
        )

        for name in filtered:
            full_path = os.path.join(watch_folder, name)
            try:
                size = os.path.getsize(full_path)
                mtime = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M:%S")
            except OSError:
                size, mtime = 0, ""

            var = tk.IntVar(value=1 if name in previously_checked else 0)
            self.file_vars[name] = var
            row = tb.Frame(self.file_list_inner)
            row.pack(fill=X, pady=1)
            tb.Checkbutton(row, variable=var, bootstyle="primary").pack(side=LEFT, padx=4)
            tb.Label(row, text=name, anchor="w").pack(side=LEFT, fill=X, expand=True, padx=4)
            tb.Label(row, text=f"{gh.format_file_size(size)}  |  {mtime}  |  {gh.file_type_label(name)}",
                    foreground="gray").pack(side=RIGHT, padx=4)

    def _select_all_files(self):
        for var in self.file_vars.values():
            var.set(1)

    def _clear_all_files(self):
        for var in self.file_vars.values():
            var.set(0)

    # -------------------------------------------------------- drag-and-drop
    def _register_drop_target(self, widget):
        """No-op if tkinterdnd2 isn't installed -- drag-and-drop is a
        convenience on top of the existing file list, never required."""
        if not DND_AVAILABLE:
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._handle_file_drop)
        except Exception as e:
            self.log(f"Drag-and-drop unavailable: {e}")

    def _handle_file_drop(self, event):
        """
        Copies dropped files into the watch folder (never moves the
        original -- the source might still be needed elsewhere), refreshes
        the file list, and auto-checks the newly added files. Folders and
        anything that isn't a real file are silently skipped rather than
        erroring the whole drop.
        """
        watch_folder = self.get_watch_folder()
        if not watch_folder or not os.path.isdir(watch_folder):
            tk.messagebox.showwarning("No watch folder", "Set a watch folder in Settings before dropping files.")
            return

        dropped_paths = gh.parse_dnd_file_list(event.data)
        added_names = []
        skipped = []

        for src_path in dropped_paths:
            if not os.path.isfile(src_path):
                continue
            dest_path = os.path.join(watch_folder, os.path.basename(src_path))
            if os.path.abspath(src_path) == os.path.abspath(dest_path):
                added_names.append(os.path.basename(dest_path))
                continue
            if os.path.exists(dest_path):
                dest_path = get_unique_save_path(dest_path)
            try:
                shutil.copy2(src_path, dest_path)
                added_names.append(os.path.basename(dest_path))
            except OSError as e:
                skipped.append((os.path.basename(src_path), str(e)))

        self.refresh_file_list()
        for name in added_names:
            if name in self.file_vars:
                self.file_vars[name].set(1)

        if added_names:
            self.log(f"Added via drag-and-drop: {', '.join(added_names)}")
        for name, error in skipped:
            self.log(f"Could not add {name}: {error}")

    def get_selected_files(self):
        return [name for name, var in self.file_vars.items() if var.get() == 1]

    def get_selected_passwords(self):
        return [label for label, var in self.password_vars.items() if var.get() == 1]

    def get_company_code(self):
        return self.company_var.get().strip()

    def get_date_string(self):
        try:
            d = self.date_entry.get_date()
        except AttributeError:
            d = datetime.strptime(self.date_entry.get(), "%Y-%m-%d").date()
        return gh.format_date_for_config(d)

    # --------------------------------------------------------------- logging
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def update_progress(self, current, total):
        self.progress.configure(maximum=total, value=current)

    # --------------------------------------------------------------- actions
    def _handle_run_now(self):
        problems = gh.validate_scan_request_with_password(
            self.get_company_code(), self.get_selected_passwords(), self.get_selected_files()
        )
        if problems:
            tk.messagebox.showerror("Cannot start scan", "\n".join(problems))
            return
        if self.on_run_now:
            self.stop_btn.configure(state=NORMAL)
            self.on_run_now(self)

    def _handle_queue_for_watcher(self):
        problems = gh.validate_scan_request_with_password(
            self.get_company_code(), self.get_selected_passwords(), self.get_selected_files()
        )
        if problems:
            tk.messagebox.showerror("Cannot queue", "\n".join(problems))
            return
        if self.on_queue_for_watcher:
            self.on_queue_for_watcher(self)

    def _handle_stop(self):
        if self.on_stop:
            self.on_stop(self)
        self.stop_btn.configure(state=DISABLED)

    def _handle_extract_headers(self):
        problems = gh.validate_scan_request(self.get_company_code(), [], self.get_selected_files())
        if problems:
            tk.messagebox.showerror("Cannot extract headers", "\n".join(problems))
            return
        if self.on_extract_headers:
            self.on_extract_headers(self)

    def scan_finished(self):
        if hasattr(self, "stop_btn"):
            self.stop_btn.configure(state=DISABLED)
        self.progress.configure(value=0)
