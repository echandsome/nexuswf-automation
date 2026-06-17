"""Desktop settings and control panel (tkinter)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from config.settings import MIN_ENTRY_DURATION_HOURS, SETTINGS_PATH, Settings
from schedule.progress import ProgressStore
from ui.runner import AutomationRunner

# Palette
_BG = "#f0f2f5"
_SURFACE = "#ffffff"
_TEXT = "#1a1a1a"
_MUTED = "#5c6370"
_BORDER = "#d8dde6"
_LOG_BG = "#1e1e1e"
_LOG_FG = "#d4d4d4"
_ACCENT = "#0078d4"

_STATUS_COLORS = {
    "ready": "#9e9e9e",
    "running": "#2e7d32",
    "stopping": "#ef6c00",
    "completed": "#1565c0",
    "stopped": "#757575",
    "error": "#c62828",
}


def _apply_theme(root: tk.Tk) -> ttk.Style:
    style = ttk.Style(root)
    for theme in ("vista", "clam", "default"):
        try:
            style.theme_use(theme)
            break
        except tk.TclError:
            continue

    root.configure(bg=_BG)

    font = ("Segoe UI", 10)
    font_bold = ("Segoe UI Semibold", 10)
    font_title = ("Segoe UI Semibold", 16)
    font_subtitle = ("Segoe UI", 10)

    style.configure(".", background=_BG, font=font)
    style.configure("TFrame", background=_BG)
    style.configure("Surface.TFrame", background=_SURFACE)
    style.configure("TLabel", background=_BG, foreground=_TEXT)
    style.configure("Surface.TLabel", background=_SURFACE, foreground=_TEXT)
    style.configure("Header.TLabel", background=_SURFACE, foreground=_TEXT, font=font_title)
    style.configure("Subtitle.TLabel", background=_SURFACE, foreground=_MUTED, font=font_subtitle)
    style.configure("Section.TLabel", background=_BG, foreground=_TEXT, font=font_bold)
    style.configure("Hint.TLabel", background=_BG, foreground=_MUTED, font=("Segoe UI", 9))
    style.configure("Status.TLabel", background=_BG, foreground=_MUTED, font=font)
    style.configure("TCheckbutton", background=_BG)
    style.configure("TNotebook", background=_BG, padding=2)
    style.configure("TNotebook.Tab", padding=(14, 8), font=font)
    style.configure("TButton", font=font, padding=(14, 7))
    style.configure("Accent.TButton", font=font_bold)
    style.configure("TLabelframe", background=_BG)
    style.configure("TLabelframe.Label", background=_BG, font=font_bold)
    style.configure("TEntry", padding=4)
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=_BORDER,
        background=_ACCENT,
        thickness=10,
    )

    return style


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("NexusWF Automation")
        self.geometry("920x800")
        self.minsize(800, 660)

        _apply_theme(self)
        self.runner = AutomationRunner()
        self._vars: dict[str, tk.Variable] = {}
        self._build()
        self._load_form()
        self._poll()

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer, style="Surface.TFrame", padding=(16, 14))
        header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header, text="NexusWF Automation", style="Header.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            header,
            text="Configure credentials, schedule runs, and monitor automation progress.",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(4, 0))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill=tk.BOTH, expand=True)

        notebook.add(self._credentials_tab(notebook), text="  Credentials  ")
        notebook.add(self._urls_tab(notebook), text="  URLs  ")
        notebook.add(self._run_tab(notebook), text="  Run  ")
        notebook.add(self._browser_tab(notebook), text="  Browser  ")

        actions = ttk.Frame(outer)
        actions.pack(fill=tk.X, pady=(14, 10))

        status_frame = ttk.Frame(actions)
        status_frame.pack(side=tk.LEFT)
        self._status_dot = tk.Label(
            status_frame,
            text="\u25cf",
            fg=_STATUS_COLORS["ready"],
            bg=_BG,
            font=("Segoe UI", 11),
        )
        self._status_dot.pack(side=tk.LEFT, padx=(0, 6))
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self._status_var, style="Status.TLabel").pack(
            side=tk.LEFT
        )

        ttk.Button(actions, text="Save settings", command=self._save).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        self._start_btn = ttk.Button(
            actions, text="Start", style="Accent.TButton", command=self._start
        )
        self._start_btn.pack(side=tk.RIGHT, padx=(8, 0))
        self._stop_btn = ttk.Button(
            actions, text="Stop", command=self._stop, state=tk.DISABLED
        )
        self._stop_btn.pack(side=tk.RIGHT, padx=(8, 0))

        progress = ttk.LabelFrame(outer, text="Progress", padding=(12, 10))
        progress.pack(fill=tk.X, pady=(0, 10))
        self._progress_bar = ttk.Progressbar(
            progress, orient=tk.HORIZONTAL, mode="determinate", maximum=100
        )
        self._progress_bar.pack(fill=tk.X, pady=(0, 6))
        self._progress_var = tk.StringVar(value="No run in progress")
        ttk.Label(progress, textvariable=self._progress_var, style="Hint.TLabel").pack(
            anchor=tk.W
        )

        log_frame = ttk.LabelFrame(outer, text="Log", padding=(10, 8))
        log_frame.pack(fill=tk.BOTH, expand=True)
        self._log = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=_LOG_BG,
            fg=_LOG_FG,
            insertbackground=_LOG_FG,
            relief=tk.FLAT,
            borderwidth=0,
            padx=8,
            pady=8,
        )
        self._log.pack(fill=tk.BOTH, expand=True)

    def _section(self, parent: ttk.Frame, row: int, title: str) -> int:
        ttk.Label(parent, text=title, style="Section.TLabel").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 8)
        )
        return row + 1

    def _credentials_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=(16, 14))
        row = self._section(frame, 0, "NexusWF")
        self._field(frame, "Username", "username", row)
        row += 1
        self._field(frame, "Password", "password", row, show="*")
        row += 1

        self._vars["use_same_ilsl_credentials"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Use same credentials for ILSL portal",
            variable=self._vars["use_same_ilsl_credentials"],
            command=self._toggle_ilsl_fields,
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(16, 4))
        row += 1

        row = self._section(frame, row, "ILSL Portal")
        self._ilsl_user = self._field(frame, "Username", "ilsl_username", row)
        row += 1
        self._ilsl_pass = self._field(frame, "Password", "ilsl_password", row, show="*")
        frame.columnconfigure(1, weight=1)
        return frame

    def _urls_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=(16, 14))
        row = self._section(frame, 0, "Endpoints")
        self._field(frame, "NexusWF base URL", "base_url", row)
        row += 1
        self._field(frame, "ILSL portal URL", "ilsl_portal_url", row)
        row += 1
        self._field(
            frame,
            "ILSL entry URL (optional)",
            "ilsl_entry_url",
            row,
            hint="Leave blank to use portal base + /entry",
        )
        frame.columnconfigure(1, weight=1)
        return frame

    def _run_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=(16, 14))
        row = self._section(frame, 0, "Task schedule")
        self._spin(
            frame,
            f"Entry duration (hours, min {MIN_ENTRY_DURATION_HOURS:g})",
            "entry_duration_hours",
            row,
            from_=MIN_ENTRY_DURATION_HOURS,
            to=24,
            increment=0.5,
        )
        row += 1

        self._vars["continuous_mode"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Continuous mode (run multiple tasks one after another)",
            variable=self._vars["continuous_mode"],
            command=self._toggle_task_count,
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(16, 4))
        row += 1

        self._task_count = self._spin(
            frame, "Number of tasks", "task_count", row, from_=1, to=20, increment=1
        )
        row += 1

        row = self._section(frame, row, "After run")
        self._spin(
            frame,
            "Keep browser open after finish (seconds)",
            "keep_open_seconds",
            row,
            from_=0,
            to=300,
            increment=5,
        )
        frame.columnconfigure(1, weight=1)
        return frame

    def _browser_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=(16, 14))
        row = self._section(frame, 0, "Playwright")
        self._vars["headless"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Headless browser", variable=self._vars["headless"]
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))
        row += 1

        self._field(
            frame,
            "Browser channel (optional)",
            "browser_channel",
            row,
            hint='e.g. "chrome" or "msedge"; leave blank for bundled Chromium',
        )
        frame.columnconfigure(1, weight=1)
        return frame

    def _field(
        self,
        parent: ttk.Frame,
        label: str,
        key: str,
        row: int,
        *,
        show: str | None = None,
        hint: str = "",
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=5)
        var = tk.StringVar()
        self._vars[key] = var
        entry = ttk.Entry(parent, textvariable=var, show=show or "")
        entry.grid(row=row, column=1, sticky=tk.EW, padx=(16, 0), pady=5)
        if hint:
            ttk.Label(parent, text=hint, style="Hint.TLabel").grid(
                row=row + 1, column=1, sticky=tk.W, padx=(16, 0), pady=(0, 4)
            )
        return entry

    def _spin(
        self,
        parent: ttk.Frame,
        label: str,
        key: str,
        row: int,
        *,
        from_: float,
        to: float,
        increment: float,
    ) -> ttk.Spinbox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=5)
        var = tk.DoubleVar() if isinstance(increment, float) and increment != 1 else tk.IntVar()
        self._vars[key] = var
        spin = ttk.Spinbox(
            parent,
            textvariable=var,
            from_=from_,
            to=to,
            increment=increment,
            width=12,
        )
        spin.grid(row=row, column=1, sticky=tk.W, padx=(16, 0), pady=5)
        return spin

    def _set_status(self, text: str, key: str = "ready") -> None:
        self._status_var.set(text)
        color = _STATUS_COLORS.get(key, _STATUS_COLORS["ready"])
        self._status_dot.configure(fg=color)

    def _toggle_ilsl_fields(self) -> None:
        state = tk.DISABLED if self._vars["use_same_ilsl_credentials"].get() else tk.NORMAL
        self._ilsl_user.configure(state=state)
        self._ilsl_pass.configure(state=state)

    def _toggle_task_count(self) -> None:
        state = tk.NORMAL if self._vars["continuous_mode"].get() else tk.DISABLED
        self._task_count.configure(state=state)

    def _load_form(self) -> None:
        data = Settings._read_file(SETTINGS_PATH)
        for key, var in self._vars.items():
            if key in data:
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(data[key]))
                elif isinstance(var, (tk.IntVar, tk.DoubleVar)):
                    var.set(data[key])
                else:
                    var.set(str(data[key]))
        self._toggle_ilsl_fields()
        self._toggle_task_count()

    def _collect(self) -> dict:
        data: dict = {}
        for key, var in self._vars.items():
            value = var.get()
            if isinstance(var, tk.BooleanVar):
                data[key] = bool(value)
            elif isinstance(var, tk.IntVar):
                data[key] = int(value)
            elif isinstance(var, tk.DoubleVar):
                data[key] = float(value)
            else:
                data[key] = str(value).strip()
        return data

    def _save(self, *, silent: bool = False) -> bool:
        data = self._collect()
        try:
            Settings.save(data)
            Settings.load()
        except (ValueError, TypeError) as exc:
            if not silent:
                messagebox.showerror("Invalid settings", str(exc))
            return False
        if not silent:
            messagebox.showinfo("Saved", "Settings saved.")
        return True

    def _start(self) -> None:
        if self.runner.is_running():
            messagebox.showinfo("Running", "Automation is already running.")
            return
        if not self._save(silent=True):
            return
        try:
            settings = Settings.load()
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return

        self._append_log(
            f"Starting — {settings.entry_duration_hours:g} h/task, "
            f"{settings.task_count if settings.continuous_mode else 1} task(s)"
        )
        self._set_status("Running…", "running")
        self._start_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.NORMAL)
        self.runner.start(settings)

    def _stop(self) -> None:
        if not self.runner.is_running():
            return
        self._append_log("Stop requested — clocking out…")
        self._set_status("Stopping…", "stopping")
        self._stop_btn.configure(state=tk.DISABLED)
        self.runner.stop()

    def _append_log(self, text: str) -> None:
        self._log.configure(state=tk.NORMAL)
        self._log.insert(tk.END, text + "\n")
        self._log.see(tk.END)
        self._log.configure(state=tk.DISABLED)

    def _update_progress(self) -> None:
        progress_path = SETTINGS_PATH.parent / "entry_progress.json"
        if not progress_path.is_file():
            self._progress_bar["value"] = 0
            self._progress_var.set("No run in progress")
            return

        progress = ProgressStore(progress_path).load()
        if not progress:
            self._progress_bar["value"] = 0
            self._progress_var.set("No progress yet")
            return

        pct = (
            100 * progress.elapsed_seconds / progress.target_duration_seconds
            if progress.target_duration_seconds
            else 0
        )
        self._progress_bar["value"] = min(pct, 100)
        self._progress_var.set(
            f"Records: {progress.completed_count} done · "
            f"{progress.elapsed_seconds / 3600:.2f} h elapsed · "
            f"{pct:.0f}% of task target"
        )

    def _poll(self) -> None:
        for line in self.runner.drain_logs():
            self._append_log(line)

        if self.runner.is_running():
            self._set_status("Running…", "running")
        elif self.runner.status == "stopped":
            self._set_status("Stopped", "stopped")
            self._start_btn.configure(state=tk.NORMAL)
            self._stop_btn.configure(state=tk.DISABLED)
            self.runner.status = "idle"
        elif self.runner.status == "completed":
            self._set_status("Completed", "completed")
            self._start_btn.configure(state=tk.NORMAL)
            self._stop_btn.configure(state=tk.DISABLED)
            self.runner.status = "idle"
        elif self.runner.status == "error":
            self._set_status(f"Error: {self.runner.error}", "error")
            self._start_btn.configure(state=tk.NORMAL)
            self._stop_btn.configure(state=tk.DISABLED)
            self.runner.status = "idle"

        self._update_progress()
        self.after(500, self._poll)


def run_app() -> None:
    app = App()
    app.mainloop()
