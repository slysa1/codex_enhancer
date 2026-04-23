#!/usr/bin/env python3
"""Windows-friendly GUI wrapper for the Codex Enhancer installer."""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
except ImportError as error:  # pragma: no cover - depends on local Python install
    tk = None
    filedialog = None
    messagebox = None
    scrolledtext = None
    ttk = None
    TK_IMPORT_ERROR = error
else:
    TK_IMPORT_ERROR = None

from scripts.install_enhancer import (
    SOURCE_ROOT,
    InstallPlan,
    apply_install_plan,
    build_install_plan,
    format_next_steps,
    overwrite_paths,
)


WINDOW_TITLE = "Codex Enhancer Installer"
PRODUCT_README = SOURCE_ROOT / "README.md"
MODE_CHOICES = (
    ("Auto (recommended)", "auto"),
    ("New repo", "new"),
    ("Existing repo", "existing"),
)


def open_product_readme() -> None:
    """Open the product README after install so the user lands on usage guidance."""

    if os.name == "nt":  # pragma: no branch - Windows is the primary target
        os.startfile(str(PRODUCT_README))  # type: ignore[attr-defined]
        return
    webbrowser.open(PRODUCT_README.resolve().as_uri())


def build_plan_preview(plan: InstallPlan) -> str:
    """Render a GUI-friendly preview of the pending install."""

    create_paths = [item.destination.as_posix() for item in plan.writes if item.action == "create"]
    overwrite_items = [item.destination.as_posix() for item in plan.writes if item.action == "overwrite"]
    proposal_items = [
        f"{item.write_path.as_posix()} (for {item.destination.as_posix()})"
        for item in plan.writes
        if item.action == "proposal"
    ]

    lines = [
        f"Target folder: {plan.target}",
        f"Install mode: {plan.mode}",
        (
            "Conflict handling: overwrite colliding enhancer files"
            if plan.force
            else "Conflict handling: write proposals for colliding enhancer files"
        ),
        "",
        "Files to create:",
        *format_section_entries(create_paths),
        "",
        "Files to overwrite:",
        *format_section_entries(overwrite_items),
        "",
        "Proposal files:",
        *format_section_entries(proposal_items),
        "",
        ".gitignore update:",
    ]

    if plan.gitignore.missing_lines:
        lines.extend(f"- add {line}" for line in plan.gitignore.missing_lines)
    else:
        lines.append("- already contains the required enhancer entries")

    lines.extend(("", "After install:", *format_next_steps(plan, write=True)))
    return "\n".join(lines)


def format_section_entries(entries: list[str]) -> list[str]:
    if not entries:
        return ["- none"]
    return [f"- {entry}" for entry in entries]


class InstallerApp:
    """Small Tkinter app for previewing and applying the enhancer install."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.minsize(760, 620)

        self.target_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="auto")
        self.force_var = tk.BooleanVar(value=False)
        self.confirm_overwrite_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(
            value="Choose a repository folder, review the plan, then run the installer."
        )

        self.current_plan: InstallPlan | None = None

        self._build_layout()
        self._wire_events()
        self._refresh_install_button()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(4, weight=1)

        ttk.Label(frame, text=WINDOW_TITLE, style="InstallerTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            frame,
            text=(
                "Preview the enhancer install, confirm any overwrites, and install into a "
                "new or existing repository."
            ),
            wraplength=700,
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))

        target_frame = ttk.LabelFrame(frame, text="Target repository", padding=12)
        target_frame.grid(row=2, column=0, sticky="ew")
        target_frame.columnconfigure(1, weight=1)

        ttk.Label(target_frame, text="Folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.target_entry = ttk.Entry(target_frame, textvariable=self.target_var)
        self.target_entry.grid(row=0, column=1, sticky="ew")
        self.browse_button = ttk.Button(target_frame, text="Browse...", command=self._browse_for_target)
        self.browse_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))

        ttk.Label(target_frame, text="Mode").grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 8))
        self.mode_combo = ttk.Combobox(
            target_frame,
            state="readonly",
            values=[label for label, _value in MODE_CHOICES],
        )
        self.mode_combo.current(0)
        self.mode_combo.grid(row=1, column=1, sticky="w", pady=(10, 0))

        self.force_check = ttk.Checkbutton(
            target_frame,
            text="Overwrite colliding enhancer files instead of writing proposals",
            variable=self.force_var,
        )
        self.force_check.grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))

        action_frame = ttk.Frame(frame)
        action_frame.grid(row=3, column=0, sticky="ew", pady=(14, 12))
        action_frame.columnconfigure(0, weight=1)

        self.review_button = ttk.Button(action_frame, text="Review install plan", command=self._review_plan)
        self.review_button.grid(row=0, column=0, sticky="w")

        self.install_button = ttk.Button(action_frame, text="Install enhancer", command=self._install)
        self.install_button.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.confirm_check = ttk.Checkbutton(
            action_frame,
            text="I understand the listed overwrite actions.",
            variable=self.confirm_overwrite_var,
        )
        self.confirm_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        preview_frame = ttk.LabelFrame(frame, text="Install preview", padding=12)
        preview_frame.grid(row=4, column=0, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview = scrolledtext.ScrolledText(preview_frame, wrap="word", height=20)
        self.preview.grid(row=0, column=0, sticky="nsew")
        self.preview.insert(
            "1.0",
            "No install plan yet.\n\nPick a folder and click 'Review install plan' to see exactly what will happen.",
        )
        self.preview.configure(state="disabled")

        status_frame = ttk.Frame(frame)
        status_frame.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        status_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, wraplength=700)
        self.status_label.grid(row=0, column=0, sticky="w")

        self.progress = ttk.Progressbar(status_frame, mode="determinate", maximum=1, value=0)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        style = ttk.Style(self.root)
        style.configure("InstallerTitle.TLabel", font=("Segoe UI", 16, "bold"))

        self.target_entry.focus_set()

    def _wire_events(self) -> None:
        self.target_var.trace_add("write", self._on_inputs_changed)
        self.force_var.trace_add("write", self._on_inputs_changed)
        self.confirm_overwrite_var.trace_add("write", self._on_confirm_changed)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_inputs_changed)

    def _mode_value(self) -> str:
        label = self.mode_combo.get()
        for candidate_label, candidate_value in MODE_CHOICES:
            if candidate_label == label:
                return candidate_value
        return "auto"

    def _set_preview_text(self, text: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def _on_inputs_changed(self, *_args: object) -> None:
        self.current_plan = None
        self.confirm_overwrite_var.set(False)
        self.confirm_check.configure(state="disabled")
        self.status_var.set("Inputs changed. Review the install plan again before installing.")
        self.progress.configure(value=0, maximum=1)
        self._refresh_install_button()

    def _on_confirm_changed(self, *_args: object) -> None:
        self._refresh_install_button()

    def _refresh_install_button(self) -> None:
        plan = self.current_plan
        if plan is None:
            self.install_button.configure(state="disabled")
            return

        requires_confirmation = bool(overwrite_paths(plan))
        allow_install = (not requires_confirmation) or self.confirm_overwrite_var.get()
        self.install_button.configure(state="normal" if allow_install else "disabled")

    def _browse_for_target(self) -> None:
        chosen = filedialog.askdirectory(
            parent=self.root,
            title="Choose the repository folder for Codex Enhancer",
            mustexist=False,
        )
        if chosen:
            self.target_var.set(chosen)

    def _review_plan(self) -> None:
        raw_target = self.target_var.get().strip()
        if not raw_target:
            messagebox.showerror(WINDOW_TITLE, "Choose or type a repository folder first.")
            return

        try:
            plan = build_install_plan(
                Path(raw_target),
                mode=self._mode_value(),
                force=self.force_var.get(),
            )
        except ValueError as error:
            self.current_plan = None
            self._set_preview_text("No valid install plan is available yet.")
            self.status_var.set(str(error))
            self.progress.configure(value=0, maximum=1)
            self._refresh_install_button()
            messagebox.showerror(WINDOW_TITLE, str(error))
            return

        self.current_plan = plan
        self._set_preview_text(build_plan_preview(plan))
        self.progress.configure(value=0, maximum=len(plan.writes) + 1)

        overwrite_list = overwrite_paths(plan)
        if overwrite_list:
            self.confirm_check.configure(state="normal")
            self.confirm_overwrite_var.set(False)
            self.status_var.set(
                "Review the overwrite list carefully, tick the confirmation box, then run the installer."
            )
        else:
            self.confirm_check.configure(state="disabled")
            self.confirm_overwrite_var.set(True)
            self.status_var.set("Install plan looks ready.")

        self._refresh_install_button()

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.review_button.configure(state=state)
        self.browse_button.configure(state=state)
        self.target_entry.configure(state=state)
        self.mode_combo.configure(state="disabled" if busy else "readonly")
        self.force_check.configure(state=state)
        if busy:
            self.install_button.configure(state="disabled")
            self.confirm_check.configure(state="disabled")
        else:
            if self.current_plan and overwrite_paths(self.current_plan):
                self.confirm_check.configure(state="normal")
            self._refresh_install_button()

    def _install(self) -> None:
        plan = self.current_plan
        if plan is None:
            self.status_var.set("Review the install plan before running the installer.")
            return

        if overwrite_paths(plan) and not self.confirm_overwrite_var.get():
            messagebox.showwarning(
                WINDOW_TITLE,
                "Confirm the overwrite list before running the installer.",
            )
            return

        self._set_busy(True)
        self.progress.configure(value=0, maximum=len(plan.writes) + 1)
        self.status_var.set("Starting install...")
        self.root.update_idletasks()

        def on_progress(current: int, total: int, message: str) -> None:
            self.progress.configure(maximum=total, value=current)
            self.status_var.set(message)
            self.root.update_idletasks()

        try:
            apply_install_plan(plan, progress_callback=on_progress)
        except Exception as error:  # pragma: no cover - GUI recovery path
            self.status_var.set(f"Install failed: {error}")
            messagebox.showerror(WINDOW_TITLE, f"Install failed:\n\n{error}")
            self._set_busy(False)
            return

        self._set_preview_text(build_plan_preview(plan))
        self.progress.configure(value=len(plan.writes) + 1, maximum=len(plan.writes) + 1)
        self.status_var.set("Installation complete.")
        self._set_busy(False)

        messagebox.showinfo(
            WINDOW_TITLE,
            "Codex Enhancer was installed successfully.\n\n"
            "The installer will open the README from this repo next so you land on the usage guidance.",
        )

        try:
            open_product_readme()
        except OSError as error:  # pragma: no cover - platform opener failure
            messagebox.showwarning(
                WINDOW_TITLE,
                "The install finished, but the README could not be opened automatically.\n\n"
                f"{error}",
            )
            return


def main() -> int:
    if TK_IMPORT_ERROR is not None:
        print(
            "Tkinter is required for the GUI installer. Install a Python build that includes Tkinter "
            "or use `python scripts/install_enhancer.py --help` for the CLI installer."
        )
        return 1

    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
