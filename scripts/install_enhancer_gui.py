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

from codex_enhancer.package_assets import asset_path
from scripts.install_enhancer import (
    EXTERNAL_STEP_ORDER_NOTE,
    REGENERABLE_OUTPUT_DESTINATIONS,
    REPOSITORY_IMPROVEMENT_AUDIT_WORKFLOW,
    SOURCE_ALIGNED_UPGRADE_DESTINATIONS,
    InstallPlan,
    apply_install_plan,
    build_overwrite_confirmation_message,
    build_install_plan,
    build_pack_management_plan,
    build_workflow_management_plan,
    build_upgrade_plan,
    format_after_install_preview,
    format_conflict_severity_lines,
    format_external_step_summary_lines,
    format_next_steps,
    format_output_ownership_lines,
    format_pack_decision_hint,
    overwrite_paths,
)
from scripts.spec_kit_bridge import render_spec_kit_detection_lines
from scripts.stack_packs import PackSelection, selected_pack_names


WINDOW_TITLE = "Codex Enhancer Installer"
PRODUCT_README = asset_path("README.md")
OPERATION_CHOICES = (
    ("Install or update scaffold", "install"),
    ("Manage stack packs", "manage-packs"),
    ("Manage workflow packs", "manage-workflows"),
    ("Upgrade or reconcile existing install", "upgrade-enhancer"),
    ("Refresh managed outputs", "refresh-generated"),
)
MODE_CHOICES = (
    ("Auto (recommended)", "auto"),
    ("New repo", "new"),
    ("Existing repo", "existing"),
)
SPEC_KIT_MODE_CHOICES = (
    ("Auto detect (recommended)", "auto"),
    ("Bridge off", "off"),
    ("Attach existing official install", "attach"),
    ("Bootstrap official Spec Kit", "bootstrap"),
)
SPEC_KIT_SCRIPT_CHOICES = (
    ("Auto", "auto"),
    ("PowerShell", "ps"),
    ("Shell", "sh"),
)
SPEC_KIT_COMMAND_SURFACE_CHOICES = (
    ("Auto", "auto"),
    ("$speckit-<command>", "dollar"),
    ("/prompts:speckit.<command>", "slash"),
)
UTILITY_HARNESS_MODE_CHOICES = (
    ("Off (recommended)", "off"),
    ("Install helper tools", "install"),
)

INSTALL_PACK_INTRO = (
    "Stack packs add extra Codex guidance for common repo shapes. After scanning, recommended "
    "packs start selected; read each pack's enable/adds/skip guidance before installing."
)
REFRESH_PACK_INTRO = (
    "Refresh reads selected packs from the target repo's existing enhancer manifest. "
    "The selected packs are read-only here; use manage-packs mode if you need to change them."
)
MANAGE_PACK_INTRO = (
    "Pack management reads the target repo's existing enhancer manifest, lets you change "
    "the selected set, and updates only the managed AGENTS section plus generated pack outputs. "
    "Enable a pack only when its guidance matches real code in the repo."
)
MANAGE_WORKFLOW_INTRO = (
    "Workflow management reads the target repo's existing enhancer manifest, lets you change "
    "selected reusable workflow guidance, and updates only generated workflow outputs. "
    "The repository-improvement audit workflow also maintains a managed section in roadmap.md."
)
UPGRADE_PACK_INTRO = (
    "Upgrade keeps the selected packs from the target repo's existing enhancer manifest. "
    "It reconciles tracked enhancer files against the current source and writes repo-owned drift as proposals."
)
SPEC_KIT_INTRO = (
    "The Spec Kit bridge is optional. Use attach when the repo already has an official Spec Kit install, "
    "bootstrap when you want the installer to run the official Codex setup first, and off when you want the enhancer "
    "to ignore Spec Kit entirely."
)
UTILITY_HARNESS_INTRO = (
    "The Utility Harness is optional Codex/operator tooling. It installs requirements-codex.txt, tools/ai scripts, "
    "and docs/ai/utility-harness.md, but never installs dependencies automatically."
)
WINDOW_MIN_WIDTH = 760
WINDOW_MIN_HEIGHT = 620
WINDOW_MAX_WIDTH = 1120
WINDOW_MAX_HEIGHT = 980
WINDOW_SCREEN_MARGIN = 120
PACK_VIEWPORT_HEIGHT = 240
PACK_TEXT_WRAP = 680


def compute_window_geometry(screen_width: int, screen_height: int) -> tuple[int, int, int, int]:
    """Return a stable starting geometry that stays inside the current screen."""

    width = min(WINDOW_MAX_WIDTH, max(WINDOW_MIN_WIDTH, screen_width - WINDOW_SCREEN_MARGIN))
    height = min(WINDOW_MAX_HEIGHT, max(WINDOW_MIN_HEIGHT, screen_height - WINDOW_SCREEN_MARGIN))
    width = min(width, screen_width)
    height = min(height, screen_height)
    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 2, 0)
    return width, height, x, y


def open_product_readme() -> None:
    """Open the product README after install so the user lands on usage guidance."""

    if os.name == "nt":  # pragma: no branch - Windows is the primary target
        os.startfile(str(PRODUCT_README))  # type: ignore[attr-defined]
        return
    webbrowser.open(PRODUCT_README.resolve().as_uri())


def operation_label(plan: InstallPlan) -> str:
    if plan.operation == "refresh-generated":
        return "Refresh managed outputs"
    if plan.operation == "manage-packs":
        return "Manage stack packs"
    if plan.operation == "manage-workflows":
        return "Manage workflow packs"
    if plan.operation == "manage-spec-kit-bridge":
        return "Manage Spec Kit bridge"
    if plan.operation == "upgrade-enhancer":
        return "Upgrade or reconcile existing install"
    return "Install or update scaffold"


def action_verb(plan: InstallPlan) -> str:
    if plan.operation == "refresh-generated":
        return "refresh"
    if plan.operation == "manage-packs":
        return "manage packs"
    if plan.operation == "manage-workflows":
        return "manage workflows"
    if plan.operation == "manage-spec-kit-bridge":
        return "manage Spec Kit bridge"
    if plan.operation == "upgrade-enhancer":
        return "upgrade"
    return "install"


def requires_confirmation(plan: InstallPlan) -> bool:
    return plan.operation not in {"refresh-generated", "manage-packs", "manage-workflows"} and bool(overwrite_paths(plan))


def progress_total(plan: InstallPlan) -> int:
    return len(plan.external_steps) + len(plan.writes) + (1 if plan.gitignore is not None else 0)


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
    elif plan.operation == "manage-packs":
        lines.append(
            "Pack management behavior: update selected packs, the managed AGENTS section, "
            "and generated pack outputs only."
        )
    elif plan.operation == "manage-workflows":
        lines.append(
            "Workflow management behavior: update selected workflows, generated workflow guidance, "
            "the manifest, and workflow-owned managed outputs only."
        )
    elif plan.operation == "upgrade-enhancer":
        lines.append(
            "Upgrade behavior: overwrite tracked managed outputs and source-aligned copies; "
            "write repo-owned scaffold drift as proposals."
        )
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

    lines.extend(["", "Stack packs:", *format_pack_entries(plan.pack_selections)])
    if plan.workflow_selections or plan.operation == "manage-workflows":
        lines.extend(
            [
                "",
                "Workflow packs:",
                *format_pack_entries(
                    plan.workflow_selections,
                    manifest_label="selected workflows",
                ),
            ]
        )
    bridge_entries = format_spec_kit_entries(plan)
    if bridge_entries:
        lines.extend(["", "Spec Kit bridge:", *bridge_entries])
    utility_entries = format_utility_harness_entries(plan)
    if utility_entries:
        lines.extend(["", "Utility Harness:", *utility_entries])

    if plan.operation == "upgrade-enhancer":
        lines.extend(["", *format_upgrade_sections(plan)])
    else:
        lines.extend(
            [
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

    lines.extend(("", *build_preview_follow_up(plan)))
    return "\n".join(lines)


def format_section_entries(entries: list[str]) -> list[str]:
    if not entries:
        return ["- none"]
    return [f"- {entry}" for entry in entries]


def format_pack_entries(
    selections: tuple[PackSelection, ...],
    *,
    manifest_label: str = "selected packs",
) -> list[str]:
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
        if selection.selected or selection.recommended or selection.detected:
            entries.append(f"  {format_pack_decision_hint(selection.pack)}")
    if selected_names:
        entries.append(
            f"- Manifest {manifest_label}: "
            + ", ".join(f"`{name}`" for name in selected_names)
        )
    else:
        entries.append(f"- Manifest {manifest_label}: none")
    return entries


def format_spec_kit_entries(plan: InstallPlan) -> list[str]:
    entries: list[str] = []
    if plan.spec_kit_bridge is not None:
        entries.append(
            f"- Bridge mode: {plan.spec_kit_bridge.mode} ({plan.spec_kit_bridge.state})"
        )
        if plan.spec_kit_bridge.command_label:
            entries.append(f"- Preferred command surface: {plan.spec_kit_bridge.command_label}")
        if plan.spec_kit_bridge.available_commands:
            commands = ", ".join(f"`{command}`" for command in plan.spec_kit_bridge.available_commands)
            entries.append(f"- Bridge-aware commands: {commands}")
        if plan.external_steps:
            entries.append(f"- Bootstrap order: {EXTERNAL_STEP_ORDER_NOTE}")
            for step in plan.external_steps:
                entries.extend(format_external_step_summary_lines(step))
    detection = plan.spec_kit_detection
    if detection is not None and detection.detected:
        entries.extend(render_spec_kit_detection_lines(detection))
    elif not entries:
        return []
    return entries


def format_utility_harness_entries(plan: InstallPlan) -> list[str]:
    if plan.utility_harness is None or not plan.utility_harness.enabled:
        return []
    entries = [
        f"- Mode: {plan.utility_harness.mode} ({plan.utility_harness.state})",
        "- Dependencies: listed for manual Codex/operator install only",
    ]
    if plan.utility_harness.tool_files:
        tools = ", ".join(f"`{path}`" for path in plan.utility_harness.tool_files)
        entries.append(f"- Tools: {tools}")
    return entries


def format_upgrade_sections(plan: InstallPlan) -> list[str]:
    generated_entries = []
    direct_entries = []
    repo_owned_entries = []

    for item in plan.writes:
        entry = (
            f"proposal: {item.write_path.as_posix()} (for {item.destination.as_posix()})"
            if item.action == "proposal"
            else f"{item.action}: {item.write_path.as_posix()}"
        )
        if item.destination in REGENERABLE_OUTPUT_DESTINATIONS:
            generated_entries.append(entry)
        elif item.destination in SOURCE_ALIGNED_UPGRADE_DESTINATIONS:
            direct_entries.append(entry)
        else:
            repo_owned_entries.append(entry)

    lines = [
        "",
        "Managed generated outputs:",
        *format_section_entries(generated_entries),
        "",
        "Source-aligned direct copies:",
        *format_section_entries(direct_entries),
        "",
        "Repo-owned proposal files:",
        *format_section_entries(repo_owned_entries),
    ]
    if plan.gitignore is not None:
        lines.extend(["", ".gitignore reconcile:"])
        if plan.gitignore.missing_lines:
            lines.extend(f"- add {line}" for line in plan.gitignore.missing_lines)
        else:
            lines.append("- already contains the required enhancer entries")
    return lines


def build_preview_follow_up(plan: InstallPlan) -> list[str]:
    if plan.operation == "upgrade-enhancer":
        return ["After upgrade:", *format_next_steps(plan, write=True)]
    if plan.operation == "manage-packs":
        return ["After pack management:", *format_next_steps(plan, write=True)]
    if plan.operation == "manage-workflows":
        return ["After workflow management:", *format_next_steps(plan, write=True)]
    return format_after_install_preview(plan)


def build_completion_message(plan: InstallPlan) -> str:
    selected_names = selected_pack_names(plan.pack_selections)
    selected_workflows = selected_pack_names(plan.workflow_selections)
    lines = [
        (
            "Codex Enhancer managed outputs were refreshed successfully."
            if plan.operation == "refresh-generated"
            else "Codex Enhancer stack packs were updated successfully."
            if plan.operation == "manage-packs"
            else "Codex Enhancer workflow packs were updated successfully."
            if plan.operation == "manage-workflows"
            else "Codex Enhancer upgrade reconcile completed successfully."
            if plan.operation == "upgrade-enhancer"
            else "Codex Enhancer was installed successfully."
        ),
        "",
        f"Target folder: {plan.target}",
        "",
        (
            "Stack packs from the target manifest:"
            if plan.operation in {"refresh-generated", "upgrade-enhancer"}
            else "Selected stack packs now:"
            if plan.operation == "manage-packs"
            else "Installed stack packs:"
        ),
    ]
    if selected_names:
        lines.extend(f"- {name}" for name in selected_names)
    else:
        lines.append("- none selected")
    if plan.operation == "manage-workflows" or selected_workflows:
        lines.extend(
            [
                "",
                (
                    "Selected workflow packs now:"
                    if plan.operation == "manage-workflows"
                    else "Workflow packs from the target manifest:"
                ),
            ]
        )
        if selected_workflows:
            lines.extend(f"- {name}" for name in selected_workflows)
        else:
            lines.append("- none selected")
        if REPOSITORY_IMPROVEMENT_AUDIT_WORKFLOW in selected_workflows:
            lines.append("- roadmap.md managed audit section is present")
    if plan.utility_harness is not None and plan.utility_harness.enabled:
        lines.extend(
            [
                "",
                "Utility Harness:",
                "- installed",
            ]
        )
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

        self.target_var = tk.StringVar()
        self.operation_var = tk.StringVar(value="install")
        self.force_var = tk.BooleanVar(value=False)
        self.confirm_overwrite_var = tk.BooleanVar(value=False)
        self.spec_kit_mode_var = tk.StringVar(value=SPEC_KIT_MODE_CHOICES[0][0])
        self.spec_kit_script_var = tk.StringVar(value=SPEC_KIT_SCRIPT_CHOICES[0][0])
        self.spec_kit_command_surface_var = tk.StringVar(value=SPEC_KIT_COMMAND_SURFACE_CHOICES[0][0])
        self.spec_kit_version_var = tk.StringVar()
        self.utility_harness_mode_var = tk.StringVar(value=UTILITY_HARNESS_MODE_CHOICES[0][0])
        self.status_var = tk.StringVar(
            value="Choose a repository folder, pick install, upgrade, or refresh, review the plan, then run it."
        )

        self.current_plan: InstallPlan | None = None
        self.pack_vars: dict[str, tk.BooleanVar] = {}
        self.pack_summary_labels: list[ttk.Label] = []

        self._build_layout()
        self._configure_window_geometry()
        self._wire_events()
        self._sync_operation_controls()
        self._refresh_install_button()

    def _configure_window_geometry(self) -> None:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        min_width = min(WINDOW_MIN_WIDTH, screen_width)
        min_height = min(WINDOW_MIN_HEIGHT, screen_height)
        self.root.minsize(min_width, min_height)
        width, height, x, y = compute_window_geometry(screen_width, screen_height)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(7, weight=1)

        style = ttk.Style(self.root)
        style.configure("InstallerTitle.TLabel", font=("Segoe UI", 16, "bold"))
        frame_background = style.lookup("TFrame", "background") or self.root.cget("background")

        ttk.Label(frame, text=WINDOW_TITLE, style="InstallerTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            frame,
            text=(
                "Preview a full scaffold install or refresh only the managed enhancer outputs "
                "or reconcile an existing enhancer install against this source repo."
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

        spec_kit_frame = ttk.LabelFrame(frame, text="Spec Kit bridge", padding=12)
        spec_kit_frame.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        spec_kit_frame.columnconfigure(1, weight=1)
        self.spec_kit_frame = spec_kit_frame

        self.spec_kit_intro = ttk.Label(
            spec_kit_frame,
            text=SPEC_KIT_INTRO,
            wraplength=700,
        )
        self.spec_kit_intro.grid(row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(spec_kit_frame, text="Mode").grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 8))
        self.spec_kit_mode_combo = ttk.Combobox(
            spec_kit_frame,
            state="readonly",
            textvariable=self.spec_kit_mode_var,
            values=[label for label, _value in SPEC_KIT_MODE_CHOICES],
        )
        self.spec_kit_mode_combo.current(0)
        self.spec_kit_mode_combo.grid(row=1, column=1, sticky="w", pady=(10, 0))

        ttk.Label(spec_kit_frame, text="Script").grid(row=1, column=2, sticky="w", pady=(10, 0), padx=(16, 8))
        self.spec_kit_script_combo = ttk.Combobox(
            spec_kit_frame,
            state="readonly",
            textvariable=self.spec_kit_script_var,
            values=[label for label, _value in SPEC_KIT_SCRIPT_CHOICES],
            width=14,
        )
        self.spec_kit_script_combo.current(0)
        self.spec_kit_script_combo.grid(row=1, column=3, sticky="w", pady=(10, 0))

        ttk.Label(spec_kit_frame, text="Command surface").grid(row=2, column=0, sticky="w", pady=(10, 0), padx=(0, 8))
        self.spec_kit_command_surface_combo = ttk.Combobox(
            spec_kit_frame,
            state="readonly",
            textvariable=self.spec_kit_command_surface_var,
            values=[label for label, _value in SPEC_KIT_COMMAND_SURFACE_CHOICES],
            width=28,
        )
        self.spec_kit_command_surface_combo.current(0)
        self.spec_kit_command_surface_combo.grid(row=2, column=1, sticky="w", pady=(10, 0))

        ttk.Label(spec_kit_frame, text="Version").grid(row=2, column=2, sticky="w", pady=(10, 0), padx=(16, 8))
        self.spec_kit_version_entry = ttk.Entry(
            spec_kit_frame,
            textvariable=self.spec_kit_version_var,
            width=18,
        )
        self.spec_kit_version_entry.grid(row=2, column=3, sticky="w", pady=(10, 0))

        utility_frame = ttk.LabelFrame(frame, text="Utility Harness", padding=12)
        utility_frame.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        utility_frame.columnconfigure(1, weight=1)
        self.utility_frame = utility_frame

        ttk.Label(
            utility_frame,
            text=UTILITY_HARNESS_INTRO,
            wraplength=700,
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(utility_frame, text="Mode").grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 8))
        self.utility_harness_mode_combo = ttk.Combobox(
            utility_frame,
            state="readonly",
            textvariable=self.utility_harness_mode_var,
            values=[label for label, _value in UTILITY_HARNESS_MODE_CHOICES],
            width=24,
        )
        self.utility_harness_mode_combo.current(0)
        self.utility_harness_mode_combo.grid(row=1, column=1, sticky="w", pady=(10, 0))

        pack_frame = ttk.LabelFrame(frame, text="Stack packs", padding=12)
        pack_frame.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        pack_frame.columnconfigure(0, weight=1)
        self.pack_frame = pack_frame
        self.pack_intro = ttk.Label(
            pack_frame,
            text=INSTALL_PACK_INTRO,
            wraplength=700,
        )
        self.pack_intro.grid(row=0, column=0, sticky="w")

        self.pack_viewport = ttk.Frame(pack_frame, height=PACK_VIEWPORT_HEIGHT)
        self.pack_viewport.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.pack_viewport.columnconfigure(0, weight=1)
        self.pack_viewport.rowconfigure(0, weight=1)
        self.pack_viewport.grid_propagate(False)

        self.pack_canvas = tk.Canvas(
            self.pack_viewport,
            borderwidth=0,
            highlightthickness=0,
            height=PACK_VIEWPORT_HEIGHT,
            background=frame_background,
        )
        self.pack_canvas.grid(row=0, column=0, sticky="nsew")

        self.pack_scrollbar = ttk.Scrollbar(
            self.pack_viewport,
            orient="vertical",
            command=self.pack_canvas.yview,
        )
        self.pack_scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.pack_canvas.configure(yscrollcommand=self.pack_scrollbar.set)

        self.pack_container = ttk.Frame(self.pack_canvas)
        self.pack_container.columnconfigure(0, weight=1)
        self.pack_canvas_window = self.pack_canvas.create_window(
            (0, 0),
            window=self.pack_container,
            anchor="nw",
        )
        self.pack_canvas.bind("<Configure>", self._on_pack_canvas_configure)
        self.pack_container.bind("<Configure>", self._on_pack_container_configure)
        self._show_pack_placeholder("No pack scan yet. Click 'Review install plan' to detect stack packs.")

        action_frame = ttk.Frame(frame)
        action_frame.grid(row=6, column=0, sticky="ew", pady=(14, 12))
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
        preview_frame.grid(row=7, column=0, sticky="nsew")
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
        status_frame.grid(row=8, column=0, sticky="ew", pady=(12, 0))
        status_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, wraplength=700)
        self.status_label.grid(row=0, column=0, sticky="w")

        self.progress = ttk.Progressbar(status_frame, mode="determinate", maximum=1, value=0)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        self.target_entry.focus_set()

    def _on_pack_canvas_configure(self, event: tk.Event) -> None:
        self.pack_canvas.itemconfigure(self.pack_canvas_window, width=event.width)
        self._refresh_pack_scroll_region()

    def _on_pack_container_configure(self, _event: tk.Event | None = None) -> None:
        self._refresh_pack_scroll_region()

    def _refresh_pack_scroll_region(self) -> None:
        scroll_region = self.pack_canvas.bbox("all")
        if scroll_region is None:
            self.pack_canvas.configure(scrollregion=(0, 0, 0, 0))
            return
        self.pack_canvas.configure(scrollregion=scroll_region)

    def _reset_pack_scroll(self) -> None:
        self.pack_canvas.update_idletasks()
        self._refresh_pack_scroll_region()
        self.pack_canvas.yview_moveto(0)

    def _bind_pack_scroll_widget(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_pack_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_pack_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_pack_mousewheel, add="+")

    def _on_pack_mousewheel(self, event: tk.Event) -> str:
        if getattr(event, "delta", 0):
            direction = -1 if event.delta > 0 else 1
        else:
            direction = -1 if getattr(event, "num", 0) == 4 else 1
        self.pack_canvas.yview_scroll(direction, "units")
        return "break"

    def _wire_events(self) -> None:
        self.target_var.trace_add("write", self._on_inputs_changed)
        self.operation_var.trace_add("write", self._on_inputs_changed)
        self.force_var.trace_add("write", self._on_inputs_changed)
        self.spec_kit_mode_var.trace_add("write", self._on_inputs_changed)
        self.spec_kit_script_var.trace_add("write", self._on_inputs_changed)
        self.spec_kit_command_surface_var.trace_add("write", self._on_inputs_changed)
        self.spec_kit_version_var.trace_add("write", self._on_inputs_changed)
        self.utility_harness_mode_var.trace_add("write", self._on_inputs_changed)
        self.confirm_overwrite_var.trace_add("write", self._on_confirm_changed)
        self.operation_combo.bind("<<ComboboxSelected>>", self._on_inputs_changed)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_inputs_changed)
        self.spec_kit_mode_combo.bind("<<ComboboxSelected>>", self._on_inputs_changed)
        self.spec_kit_script_combo.bind("<<ComboboxSelected>>", self._on_inputs_changed)
        self.spec_kit_command_surface_combo.bind("<<ComboboxSelected>>", self._on_inputs_changed)
        self.utility_harness_mode_combo.bind("<<ComboboxSelected>>", self._on_inputs_changed)

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

    def _spec_kit_mode_value(self) -> str:
        label = self.spec_kit_mode_combo.get()
        for candidate_label, candidate_value in SPEC_KIT_MODE_CHOICES:
            if candidate_label == label:
                return candidate_value
        return "auto"

    def _spec_kit_script_value(self) -> str:
        label = self.spec_kit_script_combo.get()
        for candidate_label, candidate_value in SPEC_KIT_SCRIPT_CHOICES:
            if candidate_label == label:
                return candidate_value
        return "auto"

    def _spec_kit_command_surface_value(self) -> str:
        label = self.spec_kit_command_surface_combo.get()
        for candidate_label, candidate_value in SPEC_KIT_COMMAND_SURFACE_CHOICES:
            if candidate_label == label:
                return candidate_value
        return "auto"

    def _utility_harness_mode_value(self) -> str:
        label = self.utility_harness_mode_combo.get()
        for candidate_label, candidate_value in UTILITY_HARNESS_MODE_CHOICES:
            if candidate_label == label:
                return candidate_value
        return "off"

    def _is_refresh_operation(self) -> bool:
        return self._operation_value() == "refresh-generated"

    def _is_manage_operation(self) -> bool:
        return self._operation_value() in {"manage-packs", "manage-workflows"}

    def _is_manage_workflow_operation(self) -> bool:
        return self._operation_value() == "manage-workflows"

    def _is_upgrade_operation(self) -> bool:
        return self._operation_value() == "upgrade-enhancer"

    def _sync_operation_controls(self) -> None:
        is_refresh = self._is_refresh_operation()
        is_manage = self._is_manage_operation()
        is_upgrade = self._is_upgrade_operation()

        def set_spec_kit_state(state: str) -> None:
            self.spec_kit_mode_combo.configure(state=state)
            self.spec_kit_script_combo.configure(state=state)
            self.spec_kit_command_surface_combo.configure(state=state)
            self.spec_kit_version_entry.configure(state="normal" if state != "disabled" else "disabled")

        def set_utility_state(state: str) -> None:
            self.utility_harness_mode_combo.configure(state=state)

        if is_refresh:
            self.force_var.set(False)
            self.force_check.configure(state="disabled")
            self.mode_combo.set("Existing repo")
            self.mode_combo.configure(state="disabled")
            set_spec_kit_state("disabled")
            set_utility_state("disabled")
            self.pack_intro.configure(text=REFRESH_PACK_INTRO)
            self.review_button.configure(text="Review refresh plan")
            self.install_button.configure(text="Refresh generated outputs")
            return

        if is_manage:
            self.force_var.set(False)
            self.force_check.configure(state="disabled")
            self.mode_combo.set("Existing repo")
            self.mode_combo.configure(state="disabled")
            set_spec_kit_state("disabled")
            set_utility_state("disabled")
            if self._is_manage_workflow_operation():
                self.pack_frame.configure(text="Workflow packs")
                self.pack_intro.configure(text=MANAGE_WORKFLOW_INTRO)
                self.review_button.configure(text="Review workflow changes")
                self.install_button.configure(text="Apply workflow changes")
            else:
                self.pack_frame.configure(text="Stack packs")
                self.pack_intro.configure(text=MANAGE_PACK_INTRO)
                self.review_button.configure(text="Review pack changes")
                self.install_button.configure(text="Apply pack changes")
            return

        if is_upgrade:
            self.force_var.set(False)
            self.force_check.configure(state="disabled")
            self.mode_combo.set("Existing repo")
            self.mode_combo.configure(state="disabled")
            set_spec_kit_state("readonly")
            set_utility_state("readonly")
            self.pack_frame.configure(text="Stack packs")
            self.pack_intro.configure(text=UPGRADE_PACK_INTRO)
            self.review_button.configure(text="Review upgrade plan")
            self.install_button.configure(text="Apply upgrade reconcile")
            return

        self.mode_combo.configure(state="readonly")
        self.force_check.configure(state="normal")
        set_spec_kit_state("readonly")
        set_utility_state("readonly")
        self.pack_frame.configure(text="Stack packs")
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
        elif self._is_manage_operation():
            if self._is_manage_workflow_operation():
                self._show_pack_placeholder(
                    "Inputs changed. Review workflow changes again to read workflow selection from the target manifest."
                )
                self.status_var.set("Inputs changed. Review workflow changes again before applying them.")
            else:
                self._show_pack_placeholder(
                    "Inputs changed. Review pack changes again to read pack selection from the target manifest."
                )
                self.status_var.set("Inputs changed. Review pack changes again before applying them.")
        elif self._is_upgrade_operation():
            self._show_pack_placeholder(
                "Inputs changed. Review the upgrade plan again to read pack selection from the target manifest."
            )
            self.status_var.set("Inputs changed. Review the upgrade plan again before running it.")
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
            plan = self._build_plan(
                use_recommended_packs=not (
                    self._is_refresh_operation()
                    or self._is_manage_operation()
                    or self._is_upgrade_operation()
                )
            )
        except ValueError as error:
            self.current_plan = None
            self._set_preview_text("No valid plan is available yet.")
            self.status_var.set(str(error))
            self.progress.configure(value=0, maximum=1)
            self._refresh_install_button()
            if self._is_refresh_operation():
                self._show_pack_placeholder("No valid refresh pack view is available yet.")
            elif self._is_manage_operation():
                self._show_pack_placeholder(
                    "No valid workflow-management view is available yet."
                    if self._is_manage_workflow_operation()
                    else "No valid pack-management view is available yet."
                )
            elif self._is_upgrade_operation():
                self._show_pack_placeholder("No valid upgrade pack view is available yet.")
            else:
                self._show_pack_placeholder("No valid pack scan is available yet.")
            messagebox.showerror(WINDOW_TITLE, str(error))
            return

        self.current_plan = plan
        self._populate_pack_controls(
            plan,
            interactive=not (self._is_refresh_operation() or self._is_upgrade_operation()),
        )
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
            if self._is_refresh_operation():
                self.status_var.set("Refresh plan looks ready.")
            elif self._is_manage_operation():
                self.status_var.set(
                    "Workflow changes look ready."
                    if self._is_manage_workflow_operation()
                    else "Pack changes look ready."
                )
            elif self._is_upgrade_operation():
                self.status_var.set("Upgrade plan looks ready.")
            else:
                self.status_var.set("Install plan looks ready.")

        self._refresh_install_button()

    def _build_plan(
        self,
        *,
        use_recommended_packs: bool = False,
        include_packs: tuple[str, ...] = (),
        set_packs: tuple[str, ...] | None = None,
    ) -> InstallPlan:
        raw_target = self.target_var.get().strip()
        spec_kit_version = self.spec_kit_version_var.get().strip() or None
        is_refresh = self._is_refresh_operation()
        is_manage = self._is_manage_operation()
        is_upgrade = self._is_upgrade_operation()
        if is_upgrade:
            return build_upgrade_plan(
                Path(raw_target),
                spec_kit_mode=self._spec_kit_mode_value(),
                spec_kit_script=self._spec_kit_script_value(),
                spec_kit_command_surface=self._spec_kit_command_surface_value(),
                spec_kit_version=spec_kit_version,
                utility_harness_mode=self._utility_harness_mode_value(),
            )
        if is_manage:
            if self._is_manage_workflow_operation():
                return build_workflow_management_plan(
                    Path(raw_target),
                    set_workflows=set_packs,
                    require_changes=False,
                )
            return build_pack_management_plan(
                Path(raw_target),
                set_packs=set_packs,
                require_changes=False,
            )
        return build_install_plan(
            Path(raw_target),
            mode=self._mode_value(),
            force=self.force_var.get() if not is_refresh else False,
            refresh_generated=is_refresh,
            use_recommended_packs=use_recommended_packs if not is_refresh else False,
            include_packs=include_packs if not is_refresh else (),
            spec_kit_mode=self._spec_kit_mode_value() if not is_refresh else None,
            spec_kit_script=self._spec_kit_script_value(),
            spec_kit_command_surface=self._spec_kit_command_surface_value(),
            spec_kit_version=spec_kit_version,
            utility_harness_mode=self._utility_harness_mode_value() if not is_refresh else None,
        )

    def _clear_pack_controls(self) -> None:
        for child in self.pack_container.winfo_children():
            child.destroy()
        self.pack_vars = {}
        self.pack_summary_labels = []

    def _show_pack_placeholder(self, message: str) -> None:
        self._clear_pack_controls()
        label = ttk.Label(self.pack_container, text=message, wraplength=PACK_TEXT_WRAP)
        label.grid(row=0, column=0, sticky="w")
        self._bind_pack_scroll_widget(label)
        self.pack_summary_labels = [label]
        self._reset_pack_scroll()

    def _populate_pack_controls(self, plan: InstallPlan, *, interactive: bool) -> None:
        self._clear_pack_controls()
        selections = (
            plan.workflow_selections
            if plan.operation == "manage-workflows"
            else plan.pack_selections
        )
        for row_index, selection in enumerate(selections):
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
                self._bind_pack_scroll_widget(checkbox)
            else:
                label = ttk.Label(
                    self.pack_container,
                    text=(
                        f"{selection.pack.label} ({selection.pack.name})"
                        f" {'[selected]' if selection.selected else '[not selected]'}"
                    ),
                    wraplength=PACK_TEXT_WRAP,
                )
                label.grid(row=row_index * 2, column=0, sticky="w")
                self._bind_pack_scroll_widget(label)

            reason = "; ".join(selection.reasons)
            if interactive:
                summary_text = (
                    f"{'Recommended' if selection.recommended else 'Optional'}: {reason}\n"
                    f"What it does: {selection.pack.description}\n"
                    f"Enable when: {'; '.join(selection.pack.guidance.use_when)}\n"
                    f"Adds: {'; '.join(selection.pack.guidance.adds)}\n"
                    f"Skip when: {'; '.join(selection.pack.guidance.skip_when)}"
                )
            elif selection.selected:
                summary_text = (
                    f"Selected from target manifest: {reason}\n"
                    f"What it does: {selection.pack.description}\n"
                    f"Adds: {'; '.join(selection.pack.guidance.adds)}"
                )
            else:
                summary_text = (
                    f"Not selected in target manifest: {reason}\n"
                    f"Skip when: {'; '.join(selection.pack.guidance.skip_when)}"
                )
            summary = ttk.Label(
                self.pack_container,
                text=summary_text,
                wraplength=PACK_TEXT_WRAP,
            )
            summary.grid(row=row_index * 2 + 1, column=0, sticky="w", padx=(24, 0), pady=(0, 8))
            self._bind_pack_scroll_widget(summary)
            self.pack_summary_labels.append(summary)
        self._reset_pack_scroll()

    def _on_pack_toggle(self, *_args: object) -> None:
        if not self.pack_vars:
            return
        try:
            selected_names = self._selected_pack_names_from_ui()
            if self._is_manage_operation():
                plan = self._build_plan(set_packs=selected_names)
            else:
                plan = self._build_plan(include_packs=selected_names)
        except ValueError as error:
            self.status_var.set(str(error))
            return

        self.current_plan = plan
        self._set_preview_text(build_plan_preview(plan))
        noun = "Workflow selection" if self._is_manage_workflow_operation() else "Pack selection"
        if requires_confirmation(plan) and not self.confirm_overwrite_var.get():
            self.status_var.set(
                f"{noun} updated. Review the overwrite list carefully, then install."
            )
        else:
            self.status_var.set(f"{noun} updated.")
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
            self.mode_combo.configure(
                state="disabled"
                if (
                    self._is_refresh_operation()
                    or self._is_manage_operation()
                    or self._is_upgrade_operation()
                )
                else "readonly"
            )
        if busy:
            self.force_check.configure(state="disabled")
        else:
            self.force_check.configure(
                state="disabled"
                if (
                    self._is_refresh_operation()
                    or self._is_manage_operation()
                    or self._is_upgrade_operation()
                )
                else "normal"
            )
        if busy:
            self.spec_kit_mode_combo.configure(state="disabled")
            self.spec_kit_script_combo.configure(state="disabled")
            self.spec_kit_command_surface_combo.configure(state="disabled")
            self.spec_kit_version_entry.configure(state="disabled")
            self.utility_harness_mode_combo.configure(state="disabled")
        else:
            spec_state = (
                "disabled"
                if self._is_refresh_operation() or self._is_manage_operation()
                else "readonly"
            )
            self.spec_kit_mode_combo.configure(state=spec_state)
            self.spec_kit_script_combo.configure(state=spec_state)
            self.spec_kit_command_surface_combo.configure(state=spec_state)
            self.spec_kit_version_entry.configure(
                state="disabled" if spec_state == "disabled" else "normal"
            )
            self.utility_harness_mode_combo.configure(state=spec_state)
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
        if plan.operation == "refresh-generated":
            self.status_var.set("Starting refresh...")
        elif plan.operation == "manage-packs":
            self.status_var.set("Starting pack management...")
        elif plan.operation == "manage-workflows":
            self.status_var.set("Starting workflow management...")
        elif plan.operation == "upgrade-enhancer":
            self.status_var.set("Starting upgrade...")
        else:
            self.status_var.set("Starting install...")
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
        if plan.operation == "refresh-generated":
            self.status_var.set("Refresh complete.")
        elif plan.operation == "manage-packs":
            self.status_var.set("Pack management complete.")
        elif plan.operation == "manage-workflows":
            self.status_var.set("Workflow management complete.")
        elif plan.operation == "upgrade-enhancer":
            self.status_var.set("Upgrade complete.")
        else:
            self.status_var.set("Installation complete.")
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
