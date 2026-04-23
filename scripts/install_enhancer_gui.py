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
    build_overwrite_confirmation_message,
    build_install_plan,
    format_after_install_preview,
    format_conflict_severity_lines,
    format_output_ownership_lines,
    overwrite_paths,
)
from scripts.stack_packs import PackSelection, selected_pack_names


WINDOW_TITLE = "Codex Enhancer Installer"
PRODUCT_README = SOURCE_ROOT / "README.md"
OPERATION_CHOICES = (
    ("Install or update scaffold", "install"),
    ("Refresh managed outputs", "refresh-generated"),
)
MODE_CHOICES = (
    ("Auto (recommended)", "auto"),
    ("New repo", "new"),
    ("Existing repo", "existing"),
)

INSTALL_PACK_INTRO = (
    "Review the detected stack packs after scanning the target repo. Recommended packs "
    "start selected, and you can toggle them before installation."
)
REFRESH_PACK_INTRO = (
    "Refresh reads selected packs from the target repo's existing enhancer manifest. "
    "Use install mode if you need to change pack selection or update scaffold files."
)


def open_product_readme() -> None:
    """Open the product README after install so the user lands on usage guidance."""

    if os.name == "nt":  # pragma: no branch - Windows is the primary target
        os.startfile(str(PRODUCT_README))  # type: ignore[attr-defined]
        return
    webbrowser.open(PRODUCT_README.resolve().as_uri())


def operation_label(plan: InstallPlan) -> str:
    if plan.operation == "refresh-generated":
        return "Refresh managed outputs"
    return "Install or update scaffold"


def action_verb(plan: InstallPlan) -> str:
    if plan.operation == "refresh-generated":
        return "refresh"
    return "install"


def requires_confirmation(plan: InstallPlan) -> bool:
    return plan.operation != "refresh-generated" and bool(overwrite_paths(plan))


def progress_total(plan: InstallPlan) -> int:
    return len(plan.writes) + (1 if plan.gitignore is not None else 0)


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
        f"Operation: {operation_label(plan)}",
        f"Repo mode: {plan.mode}",
    ]
    if plan.operation == "refresh-generated":
        lines.append("Refresh behavior: overwrite only enhancer-managed generated outputs.")
    else:
        lines.append(
            "Conflict handling: overwrite colliding enhancer files"
            if plan.force
            else "Conflict handling: write proposals for colliding enhancer files"
        )
    conflict_lines = format_conflict_severity_lines(plan)
    if conflict_lines:
        lines.extend(("", *conflict_lines))
    ownership_lines = format_output_ownership_lines(plan)
    if ownership_lines:
        lines.extend(("", *ownership_lines))

    lines.extend(
        [
            "",
            "Stack packs:",
            *format_pack_entries(plan.pack_selections),
            "",
            "Files to create:",
            *format_section_entries(create_paths),
            "",
            "Files to overwrite:",
            *format_section_entries(overwrite_items),
            "",
            "Proposal files:",
            *format_section_entries(proposal_items),
        ]
    )

    if plan.gitignore is not None:
        lines.extend(["", ".gitignore update:"])
        if plan.gitignore.missing_lines:
            lines.extend(f"- add {line}" for line in plan.gitignore.missing_lines)
        else:
            lines.append("- already contains the required enhancer entries")

    lines.extend(("", *format_after_install_preview(plan)))
    return "\n".join(lines)


def format_section_entries(entries: list[str]) -> list[str]:
    if not entries:
        return ["- none"]
    return [f"- {entry}" for entry in entries]


def format_pack_entries(selections: tuple[PackSelection, ...]) -> list[str]:
    if not selections:
        return ["- none"]

    entries: list[str] = []
    selected_names = selected_pack_names(selections)
    for selection in selections:
        state = "selected" if selection.selected else "available"
        recommended = "recommended" if selection.recommended else "optional"
        reason = "; ".join(selection.reasons)
        entries.append(
            f"- {selection.pack.label} (`{selection.pack.name}`): {state}, {recommended} ({reason})"
        )
    if selected_names:
        entries.append("- Manifest selected packs: " + ", ".join(f"`{name}`" for name in selected_names))
    else:
        entries.append("- Manifest selected packs: none")
    return entries


def build_completion_message(plan: InstallPlan) -> str:
    selected_names = selected_pack_names(plan.pack_selections)
    lines = [
        (
            "Codex Enhancer managed outputs were refreshed successfully."
            if plan.operation == "refresh-generated"
            else "Codex Enhancer was installed successfully."
        ),
        "",
        f"Target folder: {plan.target}",
        "",
        (
            "Stack packs from the target manifest:"
            if plan.operation == "refresh-generated"
            else "Installed stack packs:"
        ),
    ]
    if selected_names:
        lines.extend(f"- {name}" for name in selected_names)
    else:
        lines.append("- none selected")
    lines.extend(
        [
            "",
            "The installer will open the README from this repo next so you land on the usage guidance.",
        ]
    )
    return "\n".join(lines)


class InstallerApp:
    """Small Tkinter app for previewing and applying the enhancer install."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.minsize(760, 620)

        self.target_var = tk.StringVar()
        self.operation_var = tk.StringVar(value="install")
        self.force_var = tk.BooleanVar(value=False)
        self.confirm_overwrite_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(
            value="Choose a repository folder, pick install or refresh, review the plan, then run it."
        )

        self.current_plan: InstallPlan | None = None
        self.pack_vars: dict[str, tk.BooleanVar] = {}
        self.pack_summary_labels: list[ttk.Label] = []

        self._build_layout()
        self._wire_events()
        self._sync_operation_controls()
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
                "Preview a full scaffold install or refresh only the managed enhancer outputs "
                "for a repo that is already using Codex Enhancer."
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

        ttk.Label(target_frame, text="Operation").grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 8))
        self.operation_combo = ttk.Combobox(
            target_frame,
            state="readonly",
            textvariable=self.operation_var,
            values=[label for label, _value in OPERATION_CHOICES],
        )
        self.operation_combo.current(0)
        self.operation_combo.grid(row=1, column=1, sticky="w", pady=(10, 0))

        ttk.Label(target_frame, text="Mode").grid(row=2, column=0, sticky="w", pady=(10, 0), padx=(0, 8))
        self.mode_combo = ttk.Combobox(
            target_frame,
            state="readonly",
            values=[label for label, _value in MODE_CHOICES],
        )
        self.mode_combo.current(0)
        self.mode_combo.grid(row=2, column=1, sticky="w", pady=(10, 0))

        self.force_check = ttk.Checkbutton(
            target_frame,
            text="Overwrite colliding enhancer files instead of writing proposals",
            variable=self.force_var,
        )
        self.force_check.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 0))

        pack_frame = ttk.LabelFrame(frame, text="Stack packs", padding=12)
        pack_frame.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        pack_frame.columnconfigure(0, weight=1)
        self.pack_frame = pack_frame
        self.pack_intro = ttk.Label(
            pack_frame,
            text=INSTALL_PACK_INTRO,
            wraplength=700,
        )
        self.pack_intro.grid(row=0, column=0, sticky="w")

        self.pack_container = ttk.Frame(pack_frame)
        self.pack_container.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.pack_container.columnconfigure(0, weight=1)
        self._show_pack_placeholder("No pack scan yet. Click 'Review install plan' to detect stack packs.")

        action_frame = ttk.Frame(frame)
        action_frame.grid(row=4, column=0, sticky="ew", pady=(14, 12))
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

        preview_frame = ttk.LabelFrame(frame, text="Plan preview", padding=12)
        preview_frame.grid(row=5, column=0, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview = scrolledtext.ScrolledText(preview_frame, wrap="word", height=20)
        self.preview.grid(row=0, column=0, sticky="nsew")
        self.preview.insert(
            "1.0",
            "No plan yet.\n\nPick a folder, choose install or refresh, and click the review button to see exactly what will happen.",
        )
        self.preview.configure(state="disabled")

        status_frame = ttk.Frame(frame)
        status_frame.grid(row=6, column=0, sticky="ew", pady=(12, 0))
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
        self.operation_var.trace_add("write", self._on_inputs_changed)
        self.force_var.trace_add("write", self._on_inputs_changed)
        self.confirm_overwrite_var.trace_add("write", self._on_confirm_changed)
        self.operation_combo.bind("<<ComboboxSelected>>", self._on_inputs_changed)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_inputs_changed)

    def _operation_value(self) -> str:
        label = self.operation_combo.get()
        for candidate_label, candidate_value in OPERATION_CHOICES:
            if candidate_label == label:
                return candidate_value
        return "install"

    def _mode_value(self) -> str:
        label = self.mode_combo.get()
        for candidate_label, candidate_value in MODE_CHOICES:
            if candidate_label == label:
                return candidate_value
        return "auto"

    def _is_refresh_operation(self) -> bool:
        return self._operation_value() == "refresh-generated"

    def _sync_operation_controls(self) -> None:
        is_refresh = self._is_refresh_operation()
        if is_refresh:
            self.force_var.set(False)
            self.force_check.configure(state="disabled")
            self.mode_combo.set("Existing repo")
            self.mode_combo.configure(state="disabled")
            self.pack_intro.configure(text=REFRESH_PACK_INTRO)
            self.review_button.configure(text="Review refresh plan")
            self.install_button.configure(text="Refresh generated outputs")
            return

        self.mode_combo.configure(state="readonly")
        self.force_check.configure(state="normal")
        self.pack_intro.configure(text=INSTALL_PACK_INTRO)
        self.review_button.configure(text="Review install plan")
        self.install_button.configure(text="Install enhancer")

    def _set_preview_text(self, text: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def _on_inputs_changed(self, *_args: object) -> None:
        self._sync_operation_controls()
        self.current_plan = None
        self.confirm_overwrite_var.set(False)
        self.confirm_check.configure(state="disabled")
        if self._is_refresh_operation():
            self._show_pack_placeholder(
                "Inputs changed. Review the refresh plan again to read pack selection from the target manifest."
            )
            self.status_var.set("Inputs changed. Review the refresh plan again before running it.")
        else:
            self._show_pack_placeholder("Inputs changed. Review the install plan again to detect stack packs.")
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

        allow_install = (not requires_confirmation(plan)) or self.confirm_overwrite_var.get()
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
            plan = self._build_plan(use_recommended_packs=not self._is_refresh_operation())
        except ValueError as error:
            self.current_plan = None
            self._set_preview_text("No valid plan is available yet.")
            self.status_var.set(str(error))
            self.progress.configure(value=0, maximum=1)
            self._refresh_install_button()
            if self._is_refresh_operation():
                self._show_pack_placeholder("No valid refresh pack view is available yet.")
            else:
                self._show_pack_placeholder("No valid pack scan is available yet.")
            messagebox.showerror(WINDOW_TITLE, str(error))
            return

        self.current_plan = plan
        self._populate_pack_controls(plan, interactive=not self._is_refresh_operation())
        self._set_preview_text(build_plan_preview(plan))
        self.progress.configure(value=0, maximum=progress_total(plan))

        if requires_confirmation(plan):
            self.confirm_check.configure(state="normal")
            self.confirm_overwrite_var.set(False)
            self.status_var.set(
                "Review the overwrite list carefully, tick the confirmation box, then run the installer."
            )
        else:
            self.confirm_check.configure(state="disabled")
            self.confirm_overwrite_var.set(True)
            self.status_var.set(
                "Refresh plan looks ready." if self._is_refresh_operation() else "Install plan looks ready."
            )

        self._refresh_install_button()

    def _build_plan(
        self,
        *,
        use_recommended_packs: bool = False,
        include_packs: tuple[str, ...] = (),
    ) -> InstallPlan:
        raw_target = self.target_var.get().strip()
        is_refresh = self._is_refresh_operation()
        return build_install_plan(
            Path(raw_target),
            mode=self._mode_value(),
            force=self.force_var.get() if not is_refresh else False,
            refresh_generated=is_refresh,
            use_recommended_packs=use_recommended_packs if not is_refresh else False,
            include_packs=include_packs if not is_refresh else (),
        )

    def _clear_pack_controls(self) -> None:
        for child in self.pack_container.winfo_children():
            child.destroy()
        self.pack_vars = {}
        self.pack_summary_labels = []

    def _show_pack_placeholder(self, message: str) -> None:
        self._clear_pack_controls()
        label = ttk.Label(self.pack_container, text=message, wraplength=700)
        label.grid(row=0, column=0, sticky="w")
        self.pack_summary_labels = [label]

    def _populate_pack_controls(self, plan: InstallPlan, *, interactive: bool) -> None:
        self._clear_pack_controls()
        for row_index, selection in enumerate(plan.pack_selections):
            variable = tk.BooleanVar(value=selection.selected)
            if interactive:
                variable.trace_add("write", self._on_pack_toggle)
            self.pack_vars[selection.pack.name] = variable

            if interactive:
                checkbox = ttk.Checkbutton(
                    self.pack_container,
                    text=f"{selection.pack.label} ({selection.pack.name})",
                    variable=variable,
                    state="normal",
                )
                checkbox.grid(row=row_index * 2, column=0, sticky="w")
            else:
                label = ttk.Label(
                    self.pack_container,
                    text=(
                        f"{selection.pack.label} ({selection.pack.name})"
                        f" {'[selected]' if selection.selected else '[not selected]'}"
                    ),
                    wraplength=680,
                )
                label.grid(row=row_index * 2, column=0, sticky="w")

            reason = "; ".join(selection.reasons)
            if interactive:
                summary_text = f"{'Recommended' if selection.recommended else 'Optional'}: {reason}"
            elif selection.selected:
                summary_text = f"Selected from target manifest: {reason}"
            else:
                summary_text = f"Not selected in target manifest: {reason}"
            summary = ttk.Label(
                self.pack_container,
                text=summary_text,
                wraplength=680,
            )
            summary.grid(row=row_index * 2 + 1, column=0, sticky="w", padx=(24, 0), pady=(0, 8))
            self.pack_summary_labels.append(summary)

    def _on_pack_toggle(self, *_args: object) -> None:
        if not self.pack_vars:
            return
        try:
            plan = self._build_plan(include_packs=self._selected_pack_names_from_ui())
        except ValueError as error:
            self.status_var.set(str(error))
            return

        self.current_plan = plan
        self._set_preview_text(build_plan_preview(plan))
        if requires_confirmation(plan) and not self.confirm_overwrite_var.get():
            self.status_var.set(
                "Pack selection updated. Review the overwrite list carefully, then install."
            )
        else:
            self.status_var.set("Pack selection updated.")
        self._refresh_install_button()

    def _selected_pack_names_from_ui(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, variable in self.pack_vars.items()
            if variable.get()
        )

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.review_button.configure(state=state)
        self.browse_button.configure(state=state)
        self.target_entry.configure(state=state)
        if busy:
            self.mode_combo.configure(state="disabled")
        else:
            self.mode_combo.configure(state="disabled" if self._is_refresh_operation() else "readonly")
        if busy:
            self.force_check.configure(state="disabled")
        else:
            self.force_check.configure(state="disabled" if self._is_refresh_operation() else "normal")
        for child in self.pack_container.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                continue
        if busy:
            self.install_button.configure(state="disabled")
            self.confirm_check.configure(state="disabled")
        else:
            if self.current_plan and requires_confirmation(self.current_plan):
                self.confirm_check.configure(state="normal")
            self._refresh_install_button()

    def _install(self) -> None:
        plan = self.current_plan
        if plan is None:
            self.status_var.set("Review the current plan before running it.")
            return

        if requires_confirmation(plan) and not self.confirm_overwrite_var.get():
            messagebox.showwarning(
                WINDOW_TITLE,
                build_overwrite_confirmation_message(plan),
            )
            return

        self._set_busy(True)
        total_steps = progress_total(plan)
        self.progress.configure(value=0, maximum=total_steps)
        self.status_var.set(
            "Starting refresh..." if plan.operation == "refresh-generated" else "Starting install..."
        )
        self.root.update_idletasks()

        def on_progress(current: int, total: int, message: str) -> None:
            self.progress.configure(maximum=total, value=current)
            self.status_var.set(message)
            self.root.update_idletasks()

        try:
            apply_install_plan(plan, progress_callback=on_progress)
        except Exception as error:  # pragma: no cover - GUI recovery path
            action = action_verb(plan).capitalize()
            self.status_var.set(f"{action} failed: {error}")
            messagebox.showerror(WINDOW_TITLE, f"{action} failed:\n\n{error}")
            self._set_busy(False)
            return

        self._set_preview_text(build_plan_preview(plan))
        self.progress.configure(value=total_steps, maximum=total_steps)
        self.status_var.set(
            "Refresh complete." if plan.operation == "refresh-generated" else "Installation complete."
        )
        self._set_busy(False)

        messagebox.showinfo(
            WINDOW_TITLE,
            build_completion_message(plan),
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
