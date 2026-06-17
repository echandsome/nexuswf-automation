"""Desktop settings and control panel (CustomTkinter)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from config.settings import MIN_ENTRY_DURATION_HOURS, SETTINGS_PATH, Settings
from schedule.progress import ProgressStore
from ui.runner import AutomationRunner

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

_STATUS_COLORS = {
    "ready": ("gray60", "gray50"),
    "running": ("#2fa572", "#298f64"),
    "stopping": ("#e68a00", "#cc7a00"),
    "completed": ("#3b8ed0", "#36719f"),
    "stopped": ("gray55", "gray45"),
    "error": ("#d9534f", "#c9302c"),
}


class _TabGrid:
    """Two-column grid layout inside a scrollable tab."""

    def __init__(self, parent: ctk.CTkScrollableFrame) -> None:
        self.parent = parent
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        self._row = 0
        self._col = 0
        self._first_section = True

    def _newline(self) -> None:
        self._row += 1
        self._col = 0

    def section(self, title: str, *, font: ctk.CTkFont) -> None:
        if self._col:
            self._newline()
        top_pad = 0 if self._first_section else 4
        self._first_section = False
        ctk.CTkLabel(
            self.parent,
            text=title,
            font=font,
            anchor="w",
        ).grid(row=self._row, column=0, columnspan=2, sticky="w", pady=(top_pad, 6))
        self._newline()

    def slot(self) -> tuple[int, int]:
        row, col = self._row, self._col
        self._col += 1
        if self._col >= 2:
            self._newline()
        return row, col

    def span_row(self) -> int:
        if self._col:
            self._newline()
        row = self._row
        self._newline()
        return row


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("NexusWF Automation")
        self.geometry("900x840")
        self.minsize(760, 680)

        self.runner = AutomationRunner()
        self._vars: dict[str, tk.Variable] = {}
        self._font_section = ctk.CTkFont(size=14, weight="bold")
        self._font_label = ctk.CTkFont(size=13)
        self._font_hint = ctk.CTkFont(size=12)
        self._font_log = ctk.CTkFont(family="Consolas", size=12)
        self._build()
        self._load_form()
        self._poll()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(0, weight=5)
        outer.grid_rowconfigure(2, weight=2)

        settings = ctk.CTkFrame(outer, corner_radius=12)
        settings.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        settings.grid_columnconfigure(0, weight=1)
        settings.grid_rowconfigure(0, weight=1)

        self._tabview = ctk.CTkTabview(settings, corner_radius=8, border_width=0)
        self._tabview.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 0))
        self._credentials_tab(self._scrollable_tab("Credentials"))
        self._urls_tab(self._scrollable_tab("URLs"))
        self._run_tab(self._scrollable_tab("Run"))
        self._browser_tab(self._scrollable_tab("Browser"))

        actions = ctk.CTkFrame(settings, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 10))
        actions.grid_columnconfigure(0, weight=1)

        status_frame = ctk.CTkFrame(actions, fg_color="transparent")
        status_frame.grid(row=0, column=0, sticky="w")
        self._status_dot = ctk.CTkLabel(
            status_frame,
            text="\u25cf",
            font=ctk.CTkFont(size=16),
            text_color=_STATUS_COLORS["ready"][0],
            width=20,
        )
        self._status_dot.pack(side="left")
        self._status_var = tk.StringVar(value="Ready")
        ctk.CTkLabel(
            status_frame,
            textvariable=self._status_var,
            font=self._font_label,
            text_color=("gray40", "gray60"),
        ).pack(side="left", padx=(4, 0))

        btn_frame = ctk.CTkFrame(actions, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")
        self._stop_btn = ctk.CTkButton(
            btn_frame,
            text="Stop",
            width=96,
            fg_color="#d9534f",
            hover_color="#c9302c",
            state="disabled",
            command=self._stop,
        )
        self._stop_btn.pack(side="right", padx=(8, 0))
        self._start_btn = ctk.CTkButton(
            btn_frame,
            text="Start",
            width=96,
            fg_color="#2fa572",
            hover_color="#298f64",
            command=self._start,
        )
        self._start_btn.pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            btn_frame,
            text="Save settings",
            width=116,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "gray90"),
            command=self._save,
        ).pack(side="right", padx=(8, 0))

        progress = ctk.CTkFrame(outer, corner_radius=12)
        progress.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        progress.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            progress,
            text="Progress",
            font=self._font_section,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))
        self._progress_bar = ctk.CTkProgressBar(progress, height=12, corner_radius=6)
        self._progress_bar.grid(row=1, column=0, sticky="ew", padx=16)
        self._progress_bar.set(0)
        self._progress_var = tk.StringVar(value="No run in progress")
        ctk.CTkLabel(
            progress,
            textvariable=self._progress_var,
            font=self._font_hint,
            text_color=("gray40", "gray55"),
            anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(6, 12))

        log_outer = ctk.CTkFrame(outer, corner_radius=12)
        log_outer.grid(row=2, column=0, sticky="nsew")
        log_outer.grid_columnconfigure(0, weight=1)
        log_outer.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            log_outer,
            text="Log",
            font=self._font_section,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))
        self._log = ctk.CTkTextbox(
            log_outer,
            font=self._font_log,
            activate_scrollbars=True,
            wrap="word",
        )
        self._log.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        self._log.configure(state="disabled")

    def _scrollable_tab(self, name: str) -> _TabGrid:
        tab = self._tabview.add(name)
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent", corner_radius=0, border_width=0
        )
        scroll.grid(row=0, column=0, sticky="nsew")
        return _TabGrid(scroll)

    def _credentials_tab(self, grid: _TabGrid) -> None:
        grid.section("NexusWF", font=self._font_section)
        self._field(grid, "Username", "username")
        self._field(grid, "Password", "password", show="*")

        self._vars["use_same_ilsl_credentials"] = tk.BooleanVar(value=True)
        row = grid.span_row()
        ctk.CTkCheckBox(
            grid.parent,
            text="Use same credentials for ILSL portal",
            variable=self._vars["use_same_ilsl_credentials"],
            command=self._toggle_ilsl_fields,
            font=self._font_label,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))

        grid.section("ILSL Portal", font=self._font_section)
        self._ilsl_user = self._field(grid, "Username", "ilsl_username")
        self._ilsl_pass = self._field(grid, "Password", "ilsl_password", show="*")

    def _urls_tab(self, grid: _TabGrid) -> None:
        grid.section("Endpoints", font=self._font_section)
        self._field(grid, "NexusWF base URL", "base_url")
        self._field(grid, "ILSL portal URL", "ilsl_portal_url")
        row = grid.span_row()
        self._field(
            grid,
            "ILSL entry URL (optional)",
            "ilsl_entry_url",
            hint="Leave blank to use portal base + /entry",
            row=row,
            colspan=2,
        )

    def _run_tab(self, grid: _TabGrid) -> None:
        grid.section("Task schedule", font=self._font_section)
        self._number_field(
            grid,
            f"Entry duration (hours, min {MIN_ENTRY_DURATION_HOURS:g})",
            "entry_duration_hours",
            is_float=True,
        )
        self._task_count = self._number_field(
            grid, "Number of tasks", "task_count", is_float=False
        )

        self._vars["continuous_mode"] = tk.BooleanVar(value=False)
        row = grid.span_row()
        ctk.CTkCheckBox(
            grid.parent,
            text="Continuous mode (run multiple tasks one after another)",
            variable=self._vars["continuous_mode"],
            command=self._toggle_task_count,
            font=self._font_label,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))

        grid.section("After run", font=self._font_section)
        self._number_field(
            grid,
            "Keep browser open after finish (seconds)",
            "keep_open_seconds",
            is_float=False,
        )

    def _browser_tab(self, grid: _TabGrid) -> None:
        grid.section("Playwright", font=self._font_section)
        self._vars["headless"] = tk.BooleanVar(value=False)
        row = grid.span_row()
        ctk.CTkCheckBox(
            grid.parent,
            text="Headless browser",
            variable=self._vars["headless"],
            font=self._font_label,
        ).grid(row=row, column=0, columnspan=2, sticky="w")

        row = grid.span_row()
        self._field(
            grid,
            "Browser channel (optional)",
            "browser_channel",
            hint='e.g. "chrome" or "msedge"; leave blank for bundled Chromium',
            row=row,
            colspan=2,
        )

    def _place_block(
        self,
        grid: _TabGrid,
        block: ctk.CTkFrame,
        *,
        row: int | None = None,
        col: int | None = None,
        colspan: int = 1,
    ) -> None:
        if row is None:
            row, col = grid.slot()
        padx = (0, 8) if col == 0 else (8, 0) if col == 1 else 0
        block.grid(
            row=row,
            column=col or 0,
            columnspan=colspan,
            sticky="ew",
            padx=padx,
            pady=4,
        )

    def _field(
        self,
        grid: _TabGrid,
        label: str,
        key: str,
        *,
        show: str | None = None,
        hint: str = "",
        row: int | None = None,
        colspan: int = 1,
    ) -> ctk.CTkEntry:
        block = ctk.CTkFrame(grid.parent, fg_color="transparent")
        block.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(block, text=label, font=self._font_label, anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        var = tk.StringVar()
        self._vars[key] = var
        entry = ctk.CTkEntry(
            block,
            textvariable=var,
            show=show or "",
            height=34,
            corner_radius=8,
        )
        entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        if hint:
            ctk.CTkLabel(
                block,
                text=hint,
                font=self._font_hint,
                text_color=("gray50", "gray60"),
                anchor="w",
            ).grid(row=2, column=0, sticky="w", pady=(4, 0))

        if colspan > 1:
            place_row = row if row is not None else grid.span_row()
            block.grid(row=place_row, column=0, columnspan=2, sticky="ew", pady=4)
        else:
            place_row = row
            place_col = None
            if row is None:
                place_row, place_col = grid.slot()
            self._place_block(grid, block, row=place_row, col=place_col)
        return entry

    def _number_field(
        self,
        grid: _TabGrid,
        label: str,
        key: str,
        *,
        is_float: bool,
        row: int | None = None,
        colspan: int = 1,
    ) -> ctk.CTkEntry:
        block = ctk.CTkFrame(grid.parent, fg_color="transparent")
        block.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(block, text=label, font=self._font_label, anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        var = tk.DoubleVar() if is_float else tk.IntVar()
        self._vars[key] = var
        entry = ctk.CTkEntry(
            block,
            textvariable=var,
            height=34,
            corner_radius=8,
        )
        entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        if colspan > 1:
            place_row = row if row is not None else grid.span_row()
            block.grid(row=place_row, column=0, columnspan=2, sticky="ew", pady=4)
        else:
            place_row = row
            place_col = None
            if row is None:
                place_row, place_col = grid.slot()
            self._place_block(grid, block, row=place_row, col=place_col)
        return entry

    def _set_status(self, text: str, key: str = "ready") -> None:
        self._status_var.set(text)
        colors = _STATUS_COLORS.get(key, _STATUS_COLORS["ready"])
        self._status_dot.configure(text_color=colors[0])

    def _toggle_ilsl_fields(self) -> None:
        state = "disabled" if self._vars["use_same_ilsl_credentials"].get() else "normal"
        self._ilsl_user.configure(state=state)
        self._ilsl_pass.configure(state=state)

    def _toggle_task_count(self) -> None:
        state = "normal" if self._vars["continuous_mode"].get() else "disabled"
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
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self.runner.start(settings)

    def _stop(self) -> None:
        if not self.runner.is_running():
            return
        self._append_log("Stop requested — clocking out…")
        self._set_status("Stopping…", "stopping")
        self._stop_btn.configure(state="disabled")
        self.runner.stop()

    def _append_log(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _update_progress(self) -> None:
        progress_path = SETTINGS_PATH.parent / "entry_progress.json"
        if not progress_path.is_file():
            self._progress_bar.set(0)
            self._progress_var.set("No run in progress")
            return

        progress = ProgressStore(progress_path).load()
        if not progress:
            self._progress_bar.set(0)
            self._progress_var.set("No progress yet")
            return

        pct = (
            100 * progress.elapsed_seconds / progress.target_duration_seconds
            if progress.target_duration_seconds
            else 0
        )
        self._progress_bar.set(min(pct, 100) / 100)
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
            self._start_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            self.runner.status = "idle"
        elif self.runner.status == "completed":
            self._set_status("Completed", "completed")
            self._start_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            self.runner.status = "idle"
        elif self.runner.status == "error":
            self._set_status("Error", "error")
            self._start_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            self.runner.status = "idle"

        self._update_progress()
        self.after(500, self._poll)


def run_app() -> None:
    app = App()
    app.mainloop()
