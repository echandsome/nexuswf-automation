"""Desktop settings and control panel (tkinter)."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from config.settings import MIN_ENTRY_DURATION_HOURS, SETTINGS_PATH, Settings
from schedule.progress import ProgressStore
from schedule.run_state import RunStateStore
from ui.runner import AutomationRunner


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("NexusWF Automation")
        self.geometry("920x780")
        self.minsize(800, 640)

        self.runner = AutomationRunner()
        self._vars: dict[str, tk.Variable] = {}
        self._build()
        self._load_form()
        self._poll()

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(outer)
        notebook.pack(fill=tk.BOTH, expand=True)

        notebook.add(self._credentials_tab(notebook), text="Credentials")
        notebook.add(self._urls_tab(notebook), text="URLs")
        notebook.add(self._run_tab(notebook), text="Run")
        notebook.add(self._browser_tab(notebook), text="Browser")

        actions = ttk.Frame(outer)
        actions.pack(fill=tk.X, pady=(10, 6))

        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(actions, textvariable=self._status_var).pack(side=tk.LEFT)

        ttk.Button(actions, text="Save settings", command=self._save).pack(
            side=tk.RIGHT, padx=(6, 0)
        )
        self._start_btn = ttk.Button(actions, text="Start", command=self._start)
        self._start_btn.pack(side=tk.RIGHT, padx=(6, 0))
        self._stop_btn = ttk.Button(
            actions, text="Stop", command=self._stop, state=tk.DISABLED
        )
        self._stop_btn.pack(side=tk.RIGHT, padx=(6, 0))

        progress = ttk.LabelFrame(outer, text="Progress", padding=8)
        progress.pack(fill=tk.X, pady=(0, 8))
        self._progress_var = tk.StringVar(value="No run in progress")
        ttk.Label(progress, textvariable=self._progress_var).pack(anchor=tk.W)

        log_frame = ttk.LabelFrame(outer, text="Log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self._log = scrolledtext.ScrolledText(
            log_frame, height=14, state=tk.DISABLED, wrap=tk.WORD
        )
        self._log.pack(fill=tk.BOTH, expand=True)

    def _credentials_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=12)
        self._field(frame, "NexusWF username", "username", 0)
        self._field(frame, "NexusWF password", "password", 1, show="*")

        self._vars["use_same_ilsl_credentials"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Use same credentials for ILSL portal",
            variable=self._vars["use_same_ilsl_credentials"],
            command=self._toggle_ilsl_fields,
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(12, 4))

        self._ilsl_user = self._field(frame, "ILSL username", "ilsl_username", 3)
        self._ilsl_pass = self._field(frame, "ILSL password", "ilsl_password", 4, show="*")
        frame.columnconfigure(1, weight=1)
        return frame

    def _urls_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=12)
        self._field(frame, "NexusWF base URL", "base_url", 0)
        self._field(frame, "ILSL portal URL", "ilsl_portal_url", 1)
        self._field(
            frame,
            "ILSL entry URL (optional)",
            "ilsl_entry_url",
            2,
            hint="Leave blank to use portal base + /entry",
        )
        frame.columnconfigure(1, weight=1)
        return frame

    def _run_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=12)
        self._spin(
            frame,
            f"Entry duration (hours, min {MIN_ENTRY_DURATION_HOURS:g})",
            "entry_duration_hours",
            0,
            from_=MIN_ENTRY_DURATION_HOURS,
            to=24,
            increment=0.5,
        )

        self._vars["continuous_mode"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Continuous mode (run multiple tasks one after another)",
            variable=self._vars["continuous_mode"],
            command=self._toggle_task_count,
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(12, 4))

        self._task_count = self._spin(
            frame, "Number of tasks", "task_count", 2, from_=1, to=20, increment=1
        )
        self._spin(
            frame,
            "Keep browser open after finish (seconds)",
            "keep_open_seconds",
            3,
            from_=0,
            to=300,
            increment=5,
        )
        frame.columnconfigure(1, weight=1)
        return frame

    def _browser_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=12)
        self._vars["headless"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Headless browser", variable=self._vars["headless"]
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W)

        self._field(
            frame,
            "Browser channel (optional)",
            "browser_channel",
            1,
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
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        var = tk.StringVar()
        self._vars[key] = var
        entry = ttk.Entry(parent, textvariable=var, show=show or "")
        entry.grid(row=row, column=1, sticky=tk.EW, padx=(12, 0), pady=4)
        if hint:
            ttk.Label(parent, text=hint, foreground="#666").grid(
                row=row + 1, column=1, sticky=tk.W, padx=(12, 0)
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
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
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
        spin.grid(row=row, column=1, sticky=tk.W, padx=(12, 0), pady=4)
        return spin

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
        self._status_var.set("Running…")
        self._start_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.NORMAL)
        self.runner.start(settings)

    def _stop(self) -> None:
        if not self.runner.is_running():
            return
        self._append_log("Stop requested — clocking out…")
        self._status_var.set("Stopping…")
        self._stop_btn.configure(state=tk.DISABLED)
        self.runner.stop()

    def _append_log(self, text: str) -> None:
        self._log.configure(state=tk.NORMAL)
        self._log.insert(tk.END, text + "\n")
        self._log.see(tk.END)
        self._log.configure(state=tk.DISABLED)

    def _update_progress(self) -> None:
        parts: list[str] = []
        if SETTINGS_PATH.parent.joinpath("entry_progress.json").is_file():
            progress = ProgressStore(SETTINGS_PATH.parent / "entry_progress.json").load()
            if progress:
                pct = (
                    100 * progress.elapsed_seconds / progress.target_duration_seconds
                    if progress.target_duration_seconds
                    else 0
                )
                parts.append(
                    f"Records: {progress.completed_count} done, "
                    f"{progress.elapsed_seconds / 3600:.2f} h elapsed "
                    f"({pct:.0f}% of task target)"
                )
        run_path = SETTINGS_PATH.parent / "run_state.json"
        if run_path.is_file():
            run_state = RunStateStore(run_path).load()
            parts.append(f"Tasks completed: {run_state.completed_tasks}")
        self._progress_var.set(" | ".join(parts) if parts else "No progress yet")

    def _poll(self) -> None:
        for line in self.runner.drain_logs():
            self._append_log(line)

        if self.runner.is_running():
            self._status_var.set("Running…")
        elif self.runner.status == "stopped":
            self._status_var.set("Stopped")
            self._start_btn.configure(state=tk.NORMAL)
            self._stop_btn.configure(state=tk.DISABLED)
            self.runner.status = "idle"
        elif self.runner.status == "completed":
            self._status_var.set("Completed")
            self._start_btn.configure(state=tk.NORMAL)
            self._stop_btn.configure(state=tk.DISABLED)
            self.runner.status = "idle"
        elif self.runner.status == "error":
            self._status_var.set(f"Error: {self.runner.error}")
            self._start_btn.configure(state=tk.NORMAL)
            self._stop_btn.configure(state=tk.DISABLED)
            self.runner.status = "idle"

        self._update_progress()
        self.after(500, self._poll)


def run_app() -> None:
    app = App()
    app.mainloop()
