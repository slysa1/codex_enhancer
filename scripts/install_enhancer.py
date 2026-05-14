#!/usr/bin/env python3
"""Install or refresh the Codex Enhancer scaffold in a target repository."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codex_enhancer.package_assets import asset_path, read_asset_text
from scripts.enhancer_spec import (
    CHECK_COMMAND,
    ENHANCER_MANIFEST_SCHEMA_VERSION,
    ENHANCER_VERSION,
    GITIGNORE_LINES,
    INSTALL_COPY_ASSETS,
    INSTALL_TEMPLATE_ASSETS,
    MANAGED_SECTIONS,
    OPTIONAL_SPEC_KIT_TEMPLATE_ASSETS,
    OPTIONAL_UTILITY_HARNESS_COPY_ASSETS,
    SPEC_KIT_BRIDGE_TEMPLATE_PATH,
    TEST_COMMAND,
)
from scripts.spec_kit_bridge import (
    SPEC_KIT_BRIDGE_SKILLS,
    SpecKitBridgeConfig,
    SpecKitDetection,
    SpecKitPaths,
    detect_spec_kit,
    render_spec_kit_bridge_doc_command_surface,
    render_spec_kit_bridge_doc_skills,
    render_spec_kit_bridge_doc_status,
    render_spec_kit_bridge_doc_workflow,
    render_spec_kit_bridge_summary,
    render_spec_kit_detection_lines,
    render_spec_kit_feature_report,
    render_spec_kit_sync_report,
    resolve_spec_kit_bridge,
)
from scripts.stack_packs import (
    EnhancerInstallState,
    PackDetection,
    PackSelection,
    StackPack,
    detect_package_manager,
    detect_stack_packs,
    format_detection_reason,
    load_enhancer_install_state,
    load_selected_packs_from_manifest,
    load_stack_packs,
    render_agents_summary,
    render_install_follow_up_lines,
    render_refresh_follow_up_lines,
    render_stack_guidance,
    render_stack_pack_manifest,
    render_workflow_guidance,
    resolve_manifest_pack_selection,
    resolve_managed_pack_selection,
    resolve_stack_pack_selection,
    selected_pack_names,
)
from scripts.utility_harness import (
    UtilityHarnessConfig,
    render_utility_harness_summary,
    resolve_utility_harness,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ROOT = Path(".codex/enhancer-proposals")
PLAN_JSON_SCHEMA_VERSION = 1
DEFAULT_DIFF_FILE_LINE_LIMIT = 240
EXTERNAL_STEP_TIMEOUT_SECONDS = 600
GIT_STATUS_TIMEOUT_SECONDS = 10
EXTERNAL_STEP_ORDER = "before-enhancer-writes"
EXTERNAL_STEP_ORDER_NOTE = "external tools run before enhancer-owned writes"

COMMON_GUIDANCE_PATHS = (
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
    Path(".cursorrules"),
    Path(".cursor/rules"),
    Path(".github/copilot-instructions.md"),
)

ADAPTATION_AUDIT_PATHS = (
    Path("AGENTS.md"),
    Path("docs/ai/architecture.md"),
    Path("docs/ai/code-review.md"),
    Path("docs/ai/spec-kit-bridge.md"),
    Path("docs/ai/utility-harness.md"),
)

INHERITED_GUIDANCE_PATTERNS = (
    ("inherited generic guidance", "Replace inherited generic guidance with target-specific rules or explicitly document why it still applies."),
    ("bootstrapped by Codex Enhancer", "Rewrite bootstrap status into this repo's real current state."),
    ("starting point, not final truth", "Finish adaptation so the target repo guidance reads as maintained project guidance."),
    ("Replace guessed commands", "Verify commands from manifests, scripts, or CI and record only confirmed commands."),
    ("No install/build/lint/test/check/dev commands were auto-confirmed yet", "Inspect the repo and replace the empty discovered-command section with confirmed commands or an explicit no-command note."),
    ("Remove skills, docs, or checks that do not solve a real problem here", "Delete or adapt unused inherited workflow assets."),
    ("Inspect the repo's real build, lint, test, and dev commands", "Complete the immediate follow-up checklist after install."),
)

PLACEHOLDER_PATTERNS = ("{{", "}}", "TODO", "TBD", "FIXME")


@dataclass(frozen=True)
class PlannedWrite:
    destination: Path
    write_path: Path
    content: str
    source_label: str
    action: str


@dataclass(frozen=True)
class GitignorePlan:
    destination: Path
    missing_lines: tuple[str, ...]


@dataclass(frozen=True)
class ExternalStep:
    argv: tuple[str, ...]
    cwd: Path
    label: str
    source_label: str


@dataclass(frozen=True)
class ExternalStepAudit:
    label: str
    source_label: str
    argv: tuple[str, ...]
    command: str
    cwd: Path
    executable: str | None
    executable_path: str | None
    executable_found: bool
    executable_status: str
    requires_network: bool
    pinned_ref: str | None
    warnings: tuple[str, ...]
    recovery_hint: str


@dataclass(frozen=True)
class AdaptationFinding:
    severity: str
    path: Path
    message: str
    recommendation: str


@dataclass(frozen=True)
class InstallPlan:
    target: Path
    operation: str
    mode: str
    force: bool
    writes: tuple[PlannedWrite, ...]
    gitignore: GitignorePlan | None
    pack_detections: tuple[PackDetection, ...]
    pack_selections: tuple[PackSelection, ...]
    manifest_preview: str
    workflow_detections: tuple[PackDetection, ...] = ()
    workflow_selections: tuple[PackSelection, ...] = ()
    spec_kit_bridge: SpecKitBridgeConfig | None = None
    spec_kit_detection: SpecKitDetection | None = None
    utility_harness: UtilityHarnessConfig | None = None
    external_steps: tuple[ExternalStep, ...] = ()


@dataclass(frozen=True)
class InstallInspection:
    target: Path
    manifest_path: Path
    source_version: str
    target_version: str | None
    status: str
    install_state: EnhancerInstallState | None
    spec_kit_bridge: SpecKitBridgeConfig | None = None
    spec_kit_detection: SpecKitDetection | None = None
    utility_harness: UtilityHarnessConfig | None = None


@dataclass(frozen=True)
class DoctorReport:
    target: Path
    repo_kind: str
    source_checkout: bool
    python_version: str
    inspection: InstallInspection
    next_steps: tuple[str, ...]


@dataclass(frozen=True)
class ConflictSummary:
    critical_proposals: tuple[Path, ...]
    standard_proposals: tuple[Path, ...]
    critical_overwrites: tuple[Path, ...]
    standard_overwrites: tuple[Path, ...]


@dataclass(frozen=True)
class WriteSafetyDiagnostic:
    severity: str
    code: str
    message: str
    details: tuple[str, ...]


@dataclass(frozen=True)
class OutputOwnershipSummary:
    safe_to_regenerate: tuple[Path, ...]
    adapt_manually: tuple[Path, ...]


ProgressCallback = Callable[[int, int, str], None]


CRITICAL_CONFLICT_PATHS = frozenset(
    {
        Path("AGENTS.md"),
        Path("docs/ai/architecture.md"),
        Path("docs/ai/code-review.md"),
        Path("scripts/check.py"),
        Path("scripts/enhancer_spec.py"),
        Path("scripts/enhancer_validator.py"),
        Path(".github/workflows/validate.yml"),
    }
)

GENERATED_OUTPUT_DESTINATIONS = (
    Path("docs/ai/stack-guidance.md"),
    Path("docs/ai/spec-kit-bridge.md"),
    Path(".codex/enhancer/manifest.toml"),
)
WORKFLOW_PACK_ROOT = asset_path("scaffold/workflow-packs")
WORKFLOW_GUIDANCE_DESTINATION = Path("docs/ai/workflow-guidance.md")
WORKFLOW_GENERATED_OUTPUT_DESTINATIONS = (WORKFLOW_GUIDANCE_DESTINATION,)
REGENERABLE_OUTPUT_DESTINATIONS = (
    GENERATED_OUTPUT_DESTINATIONS + WORKFLOW_GENERATED_OUTPUT_DESTINATIONS
)
ROADMAP_DESTINATION = Path("roadmap.md")
ROADMAP_AUDIT_SECTION_START = (
    "<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit start -->"
)
ROADMAP_AUDIT_SECTION_END = (
    "<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit end -->"
)
REPOSITORY_IMPROVEMENT_AUDIT_WORKFLOW = "repository-improvement-audit"
SELECTED_STACK_PACKS_SECTION_ID = "AGENTS.md:selected-stack-packs"
SPEC_KIT_BRIDGE_SECTION_ID = "AGENTS.md:spec-kit-bridge"

BASE_INSTALL_MANAGED_DESTINATIONS = (
    tuple(asset.destination for asset in INSTALL_TEMPLATE_ASSETS)
    + tuple(asset.destination for asset in INSTALL_COPY_ASSETS)
    + GENERATED_OUTPUT_DESTINATIONS
)

SOURCE_ALIGNED_UPGRADE_DESTINATIONS = frozenset(
    {
        Path(".codex/skills/AGENTS.md"),
        Path(".codex/skills/plan-change/SKILL.md"),
        Path(".codex/skills/review-prep/SKILL.md"),
    }
)


def install_managed_destinations(
    spec_kit_bridge: SpecKitBridgeConfig | None,
    utility_harness: UtilityHarnessConfig | None = None,
) -> tuple[Path, ...]:
    destinations = BASE_INSTALL_MANAGED_DESTINATIONS
    if spec_kit_bridge is not None and spec_kit_bridge.enabled:
        destinations += tuple(asset.destination for asset in OPTIONAL_SPEC_KIT_TEMPLATE_ASSETS)
    if utility_harness is not None and utility_harness.enabled:
        destinations += tuple(asset.destination for asset in OPTIONAL_UTILITY_HARNESS_COPY_ASSETS)
    return destinations


def load_workflow_packs() -> tuple[StackPack, ...]:
    return load_stack_packs(WORKFLOW_PACK_ROOT)


def detect_workflow_packs(target: Path) -> tuple[PackDetection, ...]:
    return detect_stack_packs(target, packs=load_workflow_packs())


def resolve_manifest_workflow_selection(
    workflow_detections: tuple[PackDetection, ...],
    selected_workflows: tuple[str, ...],
) -> tuple[PackSelection, ...]:
    return resolve_manifest_pack_selection(
        workflow_detections,
        selected_packs=selected_workflows,
        pack_label="workflow pack",
    )


def selected_workflow_names(plan: InstallPlan) -> tuple[str, ...]:
    return selected_pack_names(plan.workflow_selections)


def infer_mode(target: Path) -> str:
    if not target.exists():
        return "new"
    if not target.is_dir():
        raise ValueError(f"Target {target} exists but is not a directory.")

    visible_entries = [entry for entry in target.iterdir() if entry.name != ".git"]
    if not visible_entries:
        return "new"

    return "existing"


def validate_mode(target: Path, mode: str) -> None:
    inferred = infer_mode(target)
    if mode == "auto":
        return
    if mode == "new" and inferred != "new":
        raise ValueError(
            f"Target {target} is not empty enough for --mode new; use --mode existing or --mode auto."
        )
    if mode == "existing" and inferred != "existing":
        raise ValueError(
            f"Target {target} does not look like an existing repo; use --mode new or --mode auto."
        )


def _version_key(version: str) -> tuple[tuple[int, int | str], ...]:
    key: list[tuple[int, int | str]] = []
    for part in version.split("."):
        key.append((0, int(part)) if part.isdigit() else (1, part))
    while len(key) > 1 and key[-1] == (0, 0):
        key.pop()
    return tuple(key)


def inspect_install(target: Path) -> InstallInspection:
    resolved_target = target.resolve()
    if not resolved_target.exists():
        raise ValueError(f"Target {resolved_target} does not exist yet.")
    if not resolved_target.is_dir():
        raise ValueError(f"Target {resolved_target} exists but is not a directory.")

    spec_kit_detection = detect_spec_kit(resolved_target)
    manifest_path = resolved_target / ".codex/enhancer/manifest.toml"
    if not manifest_path.exists():
        return InstallInspection(
            target=resolved_target,
            manifest_path=manifest_path,
            source_version=ENHANCER_VERSION,
            target_version=None,
            status="not-installed",
            install_state=None,
            spec_kit_bridge=None,
            spec_kit_detection=spec_kit_detection,
            utility_harness=None,
        )

    install_state = load_enhancer_install_state(resolved_target)
    target_version = install_state.enhancer_version
    if target_version is None:
        status = "legacy"
    elif install_state.schema_version != ENHANCER_MANIFEST_SCHEMA_VERSION:
        status = "upgrade-recommended"
    elif _version_key(target_version) == _version_key(ENHANCER_VERSION):
        status = "current"
    elif _version_key(target_version) < _version_key(ENHANCER_VERSION):
        status = "upgrade-recommended"
    else:
        status = "source-behind-target"

    return InstallInspection(
        target=resolved_target,
        manifest_path=manifest_path,
        source_version=ENHANCER_VERSION,
        target_version=target_version,
        status=status,
        install_state=install_state,
        spec_kit_bridge=install_state.spec_kit_bridge,
        spec_kit_detection=spec_kit_detection,
        utility_harness=install_state.utility_harness,
    )


def build_doctor_report(target: Path) -> DoctorReport:
    resolved_target = target.resolve()
    inspection = inspect_install(resolved_target)
    source_checkout = looks_like_source_repo(resolved_target)
    installed = inspection.status != "not-installed"
    if source_checkout:
        repo_kind = "source-checkout"
    elif installed:
        repo_kind = "installed-target"
    else:
        repo_kind = "plain-repo"
    return DoctorReport(
        target=resolved_target,
        repo_kind=repo_kind,
        source_checkout=source_checkout,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        inspection=inspection,
        next_steps=tuple(doctor_next_steps(resolved_target, repo_kind, inspection)),
    )


def _command_path(path: Path) -> str:
    text = str(path)
    return f'"{text}"' if any(character.isspace() for character in text) else text


def doctor_next_steps(
    target: Path,
    repo_kind: str,
    inspection: InstallInspection,
) -> list[str]:
    if repo_kind == "source-checkout":
        return [
            f"Run `{CHECK_COMMAND}` to validate the enhancer source checkout.",
            f"Run `{TEST_COMMAND}` to exercise the full test suite.",
            "Preview a target install with `python scripts/codex_enhancer_cli.py init ../target-repo --existing --summary`.",
        ]

    if repo_kind == "installed-target":
        if inspection.status == "current":
            status_step = "Run `codex-enhancer audit <target>` to check whether inherited guidance still needs adaptation."
        else:
            status_step = "Run `codex-enhancer upgrade <target> --summary` to preview reconcile work before applying it."
        return [
            status_step,
            f"Run `{CHECK_COMMAND}` in the target repo.",
            f"Run `{TEST_COMMAND}` in the target repo.",
        ]

    mode_flag = "--new" if infer_mode(target) == "new" else "--existing"
    return [
        f"Preview an install with `codex-enhancer init {_command_path(target)} {mode_flag} --summary`.",
        "Add `--diff` if you want planned file content changes before applying.",
        "Re-run with `--write` only after the preview looks right.",
    ]


def _format_string_list(values: tuple[str, ...]) -> str:
    if not values:
        return "none"
    return ", ".join(f"`{value}`" for value in values)


def _format_spec_kit_lines(
    bridge: SpecKitBridgeConfig | None,
    detection: SpecKitDetection | None,
    *,
    always_include: bool,
) -> list[str]:
    if bridge is None and detection is None:
        return []
    detection_lines = (
        render_spec_kit_detection_lines(detection)
        if detection is not None
        else ["- Official Spec Kit not detected."]
    )
    bridge_lines = (
        render_spec_kit_bridge_summary(bridge, detection).splitlines()
        if bridge is not None
        else []
    )
    if (
        not always_include
        and not bridge_lines
        and detection_lines == ["- Official Spec Kit not detected."]
    ):
        return []
    lines = ["", "Spec Kit bridge:"]
    if bridge_lines:
        lines.extend(bridge_lines)
    lines.extend(detection_lines)
    lines.append("")
    return lines


def _format_utility_harness_lines(
    utility_harness: UtilityHarnessConfig | None,
    *,
    always_include: bool,
) -> list[str]:
    if utility_harness is None:
        if not always_include:
            return []
        utility_harness = resolve_utility_harness(mode="off")
    if not always_include and not utility_harness.enabled:
        return []
    lines = ["", "Utility Harness:"]
    lines.extend(render_utility_harness_summary(utility_harness).splitlines())
    lines.append("")
    return lines


def format_install_inspection(inspection: InstallInspection) -> str:
    lines = [
        f"Codex Enhancer install inspection for {inspection.target}",
        f"- Source enhancer version: `{inspection.source_version}`",
        f"- Target manifest: `{inspection.manifest_path.relative_to(inspection.target).as_posix()}`",
    ]
    lines.extend(
        _format_spec_kit_lines(
            inspection.spec_kit_bridge,
            inspection.spec_kit_detection,
            always_include=True,
        )
    )
    lines.extend(
        _format_utility_harness_lines(
            inspection.utility_harness,
            always_include=True,
        )
    )

    if inspection.status == "not-installed":
        lines.extend(
            [
                "- Target enhancer version: not installed",
                "- Status: no enhancer install was found in the target repo.",
                "",
                "Next step:",
                "- Run a full install preview to bootstrap this repo with Codex Enhancer.",
            ]
        )
        return "\n".join(lines)

    target_version = inspection.target_version or "unknown"
    lines.append(f"- Target enhancer version: `{target_version}`")
    state = inspection.install_state or EnhancerInstallState(None, (), (), ())
    schema_version = "unknown" if state.schema_version is None else str(state.schema_version)
    lines.append(f"- Target manifest schema: `{schema_version}`")
    lines.append(f"- Selected packs: {_format_string_list(state.selected_packs)}")
    lines.append(f"- Selected workflows: {_format_string_list(state.selected_workflows)}")
    lines.append(f"- Safe to regenerate: {_format_string_list(state.safe_to_regenerate)}")
    lines.append(f"- Adapt manually: {_format_string_list(state.adapt_manually)}")
    if inspection.spec_kit_bridge is not None:
        lines.append(f"- Spec Kit bridge mode: `{inspection.spec_kit_bridge.mode}`")
        lines.append(f"- Spec Kit bridge state: `{inspection.spec_kit_bridge.state}`")
    if inspection.utility_harness is not None:
        lines.append(f"- Utility Harness mode: `{inspection.utility_harness.mode}`")
        lines.append(f"- Utility Harness state: `{inspection.utility_harness.state}`")
    if state.lifecycle_state or state.pack_selection_mode or state.managed_sections:
        lines.append(f"- Lifecycle state: `{state.lifecycle_state or 'unknown'}`")
        lines.append(f"- Pack selection mode: `{state.pack_selection_mode or 'unknown'}`")
        lines.append(f"- Managed sections: {_format_string_list(state.managed_sections)}")

    if inspection.status == "current":
        status_line = "target install matches the current source version."
        next_step = "- No upgrade drift is reported. Use `--refresh-generated` only if you need to re-render managed outputs."
    elif inspection.status == "legacy":
        status_line = "target install is missing a precise enhancer version and should be treated as a legacy install."
        next_step = (
            "- Use `--upgrade-enhancer` to preview reconcile drift, then re-run with `--write` when the plan looks correct."
        )
    elif inspection.status == "upgrade-recommended":
        if state.schema_version != ENHANCER_MANIFEST_SCHEMA_VERSION and inspection.target_version == ENHANCER_VERSION:
            status_line = "target install uses an older manifest schema than the current source version."
        else:
            status_line = "target install is older than the current source version."
        next_step = (
            "- Use `--upgrade-enhancer` to preview scaffold reconcile drift, then re-run with `--write` to apply it. "
            "Use `--refresh-generated` only if you just need managed outputs."
        )
    else:
        status_line = "target install reports a newer enhancer version than this source repo."
        next_step = "- Treat this repo as ahead of the current source and inspect the upgrade preview carefully before reconciling anything."

    lines.extend(
        [
            f"- Status: {status_line}",
            "",
            "Next step:",
            next_step,
        ]
    )
    return "\n".join(lines)


def format_doctor_report(report: DoctorReport) -> str:
    inspection = report.inspection
    lines = [
        f"Codex Enhancer doctor for {report.target}",
        "- Safety: read-only check; no files were changed.",
        f"- Repo kind: `{report.repo_kind}`",
        f"- Python: `{report.python_version}`",
        f"- Source checkout: {'yes' if report.source_checkout else 'no'}",
        f"- Install status: `{inspection.status}`",
    ]
    if inspection.target_version is not None:
        lines.append(f"- Target enhancer version: `{inspection.target_version}`")
    state = inspection.install_state
    if state is not None:
        lines.append(f"- Manifest schema: `{state.schema_version}`")
        lines.append(f"- Selected packs: {_format_string_list(state.selected_packs)}")
    lines.extend(
        _format_spec_kit_lines(
            inspection.spec_kit_bridge,
            inspection.spec_kit_detection,
            always_include=True,
        )
    )
    lines.extend(
        _format_utility_harness_lines(
            inspection.utility_harness,
            always_include=True,
        )
    )
    lines.append("Next steps:")
    lines.extend(f"- {step}" for step in report.next_steps)
    return "\n".join(lines)


def looks_like_source_repo(target: Path) -> bool:
    return all(
        (target / path).exists()
        for path in (
            Path("scripts/install_enhancer.py"),
            Path("docs/ai/roadmap.md"),
            Path("scaffold/target-repo/AGENTS.md"),
        )
    )


def _relative_display(target: Path, path: Path) -> Path:
    try:
        return path.relative_to(target)
    except ValueError:
        return path


def audit_adaptation(target: Path) -> tuple[AdaptationFinding, ...]:
    resolved_target = target.resolve()
    if not resolved_target.exists():
        raise ValueError(f"Target {resolved_target} does not exist yet.")
    if not resolved_target.is_dir():
        raise ValueError(f"Target {resolved_target} exists but is not a directory.")

    findings: list[AdaptationFinding] = []
    manifest = resolved_target / ".codex/enhancer/manifest.toml"
    if not manifest.exists():
        severity = "info" if looks_like_source_repo(resolved_target) else "high"
        recommendation = (
            "This appears to be the Codex Enhancer source repo, not an installed target; use source validation here."
            if severity == "info"
            else "Run an install preview before using target adaptation checks."
        )
        findings.append(
            AdaptationFinding(
                severity=severity,
                path=Path(".codex/enhancer/manifest.toml"),
                message="No installed enhancer manifest was found.",
                recommendation=recommendation,
            )
        )

    proposals_root = resolved_target / PROPOSAL_ROOT
    if proposals_root.exists():
        proposal_files = sorted(path for path in proposals_root.rglob("*") if path.is_file())
        if proposal_files:
            findings.append(
                AdaptationFinding(
                    severity="medium",
                    path=PROPOSAL_ROOT,
                    message=f"{len(proposal_files)} proposal file(s) still need review.",
                    recommendation="Merge or discard proposal files before treating the enhancer install as fully adapted.",
                )
            )

    for relative_path in ADAPTATION_AUDIT_PATHS:
        path = resolved_target / relative_path
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern in text:
                findings.append(
                    AdaptationFinding(
                        severity="high",
                        path=relative_path,
                        message=f"Placeholder marker `{pattern}` is still present.",
                        recommendation="Replace template placeholders with repo-specific guidance before handoff.",
                    )
                )
                break
        lowered = text.lower()
        for pattern, recommendation in INHERITED_GUIDANCE_PATTERNS:
            if pattern.lower() in lowered:
                findings.append(
                    AdaptationFinding(
                        severity="medium",
                        path=relative_path,
                        message=f"Inherited guidance remains: {pattern}.",
                        recommendation=recommendation,
                    )
                )

    return tuple(findings)


ADAPTATION_SEVERITIES = ("high", "medium", "low", "info")


def adaptation_severity_counts(findings: tuple[AdaptationFinding, ...]) -> dict[str, int]:
    counts = {severity: 0 for severity in ADAPTATION_SEVERITIES}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def adaptation_audit_status(findings: tuple[AdaptationFinding, ...]) -> str:
    counts = adaptation_severity_counts(findings)
    if not findings:
        return "ready"
    if counts["high"] or counts["medium"]:
        return "needs-adaptation"
    return "review-info"


def format_severity_summary(counts: dict[str, int]) -> str:
    parts = [f"{count} {severity}" for severity, count in counts.items() if count]
    return ", ".join(parts) if parts else "none"


def format_adaptation_audit(target: Path) -> str:
    resolved_target = target.resolve()
    findings = audit_adaptation(resolved_target)
    lines = [f"Codex Enhancer adaptation audit for {resolved_target}"]
    counts = adaptation_severity_counts(findings)
    status = adaptation_audit_status(findings)
    if not findings:
        lines.extend(
            [
                "- Status: ready; no obvious inherited placeholders, proposal files, or generic install guidance were found.",
                "- Severity summary: none",
                "- Next step: run the target repo validation commands and review the workflow docs normally.",
            ]
        )
        return "\n".join(lines)

    severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    sorted_findings = sorted(
        findings,
        key=lambda finding: (severity_order.get(finding.severity, 99), finding.path.as_posix(), finding.message),
    )
    lines.append(f"- Status: {status}")
    lines.append(f"- Severity summary: {format_severity_summary(counts)}")
    lines.append(f"- Findings: {len(sorted_findings)}")
    for finding in sorted_findings:
        lines.append(
            f"- [{finding.severity}] `{finding.path.as_posix()}`: {finding.message} "
            f"Recommendation: {finding.recommendation}"
        )
    lines.extend(
        [
            "",
            "Next step:",
            "- Resolve high and medium findings, then rerun this audit before treating the install as adapted.",
        ]
    )
    return "\n".join(lines)


def parse_make_like_targets(path: Path) -> set[str]:
    if not path.exists():
        return set()

    target_re = re.compile(r"^([A-Za-z0-9_.-]+):")
    targets: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = target_re.match(line)
        if not match:
            continue
        target = match.group(1)
        if target.startswith("."):
            continue
        targets.add(target)
    return targets


def maybe_set_command(commands: dict[str, str], key: str, command: str) -> None:
    commands.setdefault(key, command)


def package_manager_install_command(package_manager: str) -> str:
    return f"{package_manager} install"


def package_manager_script_command(package_manager: str, script_name: str) -> str:
    if package_manager == "bun":
        return f"bun run {script_name}"
    if script_name == "test":
        return f"{package_manager} test"
    return f"{package_manager} run {script_name}"


def discover_commands(target: Path) -> dict[str, str]:
    commands: dict[str, str] = {}

    make_targets = parse_make_like_targets(target / "Makefile")
    if make_targets:
        for name in ("install", "build", "lint", "test", "check", "dev"):
            if name in make_targets:
                maybe_set_command(commands, name, f"make {name}")

    just_targets = parse_make_like_targets(target / "justfile")
    if just_targets:
        for name in ("install", "build", "lint", "test", "check", "dev"):
            if name in just_targets:
                maybe_set_command(commands, name, f"just {name}")

    cargo_toml = target / "Cargo.toml"
    if cargo_toml.exists():
        maybe_set_command(commands, "build", "cargo build")
        maybe_set_command(commands, "lint", "cargo clippy -- -D warnings")
        maybe_set_command(commands, "test", "cargo test")
        maybe_set_command(commands, "check", "cargo fmt --check && cargo clippy -- -D warnings && cargo test")

    package_json = target / "package.json"
    if package_json.exists():
        try:
            package_data = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            package_data = {}
        if not isinstance(package_data, dict):
            package_data = {}
        scripts = package_data.get("scripts", {})
        if not isinstance(scripts, dict):
            scripts = {}
        if package_data:
            package_manager = detect_package_manager(target).name
            maybe_set_command(
                commands,
                "install",
                package_manager_install_command(package_manager),
            )
        for name in ("build", "lint", "dev", "check"):
            if name in scripts:
                maybe_set_command(
                    commands,
                    name,
                    package_manager_script_command(package_manager, name),
                )
        if "test" in scripts:
            maybe_set_command(
                commands,
                "test",
                package_manager_script_command(package_manager, "test"),
            )

    pyproject = target / "pyproject.toml"
    if pyproject.exists():
        try:
            pyproject_data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            pyproject_data = {}

        if "project" in pyproject_data or "build-system" in pyproject_data:
            maybe_set_command(commands, "install", "pip install -e .")

        tool = pyproject_data.get("tool", {})
        if "pytest" in tool or "pytest.ini_options" in tool.get("pytest", {}):
            maybe_set_command(commands, "test", "python -m pytest")
        if "ruff" in tool:
            maybe_set_command(commands, "lint", "ruff check .")

    requirements = target / "requirements.txt"
    if requirements.exists():
        maybe_set_command(commands, "install", "pip install -r requirements.txt")

    return commands


def discover_existing_guidance(
    target: Path,
    *,
    ignore_paths: tuple[Path, ...] = (),
) -> list[str]:
    ignored = set(ignore_paths)
    found: list[str] = []
    for relative_path in COMMON_GUIDANCE_PATHS:
        if relative_path in ignored:
            continue
        full_path = target / relative_path
        if full_path.exists():
            found.append(relative_path.as_posix())
    return found


def render_discovered_commands(commands: dict[str, str]) -> str:
    ordered_keys = ("install", "build", "lint", "test", "check", "dev")
    lines = [f"- `{key}`: `{commands[key]}`" for key in ordered_keys if key in commands]
    if lines:
        return "\n".join(lines)
    return (
        "- No install/build/lint/test/check/dev commands were auto-confirmed yet.\n"
        "- Inspect the repo and replace this section with commands verified from manifests, scripts, or CI."
    )


def render_existing_guidance(found: list[str]) -> str:
    if found:
        return "\n".join(f"- Review existing guidance in `{path}` before leaving inherited enhancer text in place." for path in found)
    return "- No existing AGENTS/Claude/Cursor/Copilot guidance was auto-detected."


def render_template(template_text: str, replacements: dict[str, str]) -> str:
    rendered = template_text
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("Template rendering left unresolved placeholders behind.")
    return rendered


def proposal_destination(destination: Path) -> Path:
    return PROPOSAL_ROOT / destination


def unique_proposal_destination(target: Path, destination: Path) -> Path:
    proposal_path = proposal_destination(destination)
    if not (target / proposal_path).exists():
        return proposal_path

    parent = proposal_path.parent
    stem = proposal_path.stem
    suffix = proposal_path.suffix
    for index in range(1, 1000):
        candidate = parent / f"{stem}.{index}{suffix}"
        if not (target / candidate).exists():
            return candidate

    raise ValueError(
        f"Too many existing proposal files for {destination.as_posix()}; "
        "review .codex/enhancer-proposals before retrying."
    )


def _plan_changed_write(
    target: Path,
    destination: Path,
    content: str,
    source_label: str,
    *,
    existing_action: str,
) -> PlannedWrite | None:
    destination_path = target / destination
    if destination_path.exists():
        existing_content = destination_path.read_text(encoding="utf-8")
        if existing_content == content:
            return None
        if existing_action == "proposal":
            return PlannedWrite(
                destination=destination,
                write_path=unique_proposal_destination(target, destination),
                content=content,
                source_label=source_label,
                action="proposal",
            )
        return PlannedWrite(
            destination=destination,
            write_path=destination,
            content=content,
            source_label=source_label,
            action=existing_action,
        )

    return PlannedWrite(
        destination=destination,
        write_path=destination,
        content=content,
        source_label=source_label,
        action="create",
    )


def build_replacements(
    target: Path,
    pack_selections: tuple[PackSelection, ...],
    spec_kit_bridge: SpecKitBridgeConfig,
    spec_kit_detection: SpecKitDetection,
    utility_harness: UtilityHarnessConfig,
    *,
    ignore_existing_guidance: tuple[Path, ...] = (),
) -> dict[str, str]:
    commands = discover_commands(target)
    repo_name = target.name or "Repository"
    return {
        "REPO_NAME": repo_name,
        "DISCOVERED_COMMANDS": render_discovered_commands(commands),
        "EXISTING_GUIDANCE": render_existing_guidance(
            discover_existing_guidance(target, ignore_paths=ignore_existing_guidance)
        ),
        "PACK_AGENTS_SUMMARY": render_agents_summary(pack_selections),
        "SPEC_KIT_BRIDGE_SUMMARY": render_spec_kit_bridge_summary(
            spec_kit_bridge,
            spec_kit_detection,
        ),
        "SPEC_KIT_BRIDGE_STATUS": render_spec_kit_bridge_doc_status(
            spec_kit_bridge,
            spec_kit_detection,
        ),
        "SPEC_KIT_COMMAND_SURFACE_GUIDE": render_spec_kit_bridge_doc_command_surface(
            spec_kit_bridge
        ),
        "SPEC_KIT_WORKFLOW_GUIDE": render_spec_kit_bridge_doc_workflow(spec_kit_bridge),
        "SPEC_KIT_SKILL_GUIDE": render_spec_kit_bridge_doc_skills(spec_kit_bridge),
        "UTILITY_HARNESS_SUMMARY": render_utility_harness_summary(utility_harness),
    }


def resolve_target_spec_kit_bridge(
    target: Path,
    *,
    detection: SpecKitDetection,
    install_state: EnhancerInstallState | None = None,
    mode: str | None = None,
    script_type: str = "auto",
    command_surface: str = "auto",
    version: str | None = None,
    executable: str | None = None,
) -> SpecKitBridgeConfig:
    existing_bridge = install_state.spec_kit_bridge if install_state is not None else None
    resolved_mode = mode or (existing_bridge.mode if existing_bridge is not None else "auto")
    resolved_script = (
        script_type
        if script_type != "auto"
        else existing_bridge.script_type
        if existing_bridge is not None and existing_bridge.script_type is not None
        else "auto"
    )
    resolved_surface = (
        command_surface
        if command_surface != "auto"
        else existing_bridge.command_surface
        if existing_bridge is not None and existing_bridge.command_surface is not None
        else "auto"
    )
    resolved_version = version or (
        existing_bridge.cli_version if existing_bridge is not None else None
    )
    return resolve_spec_kit_bridge(
        target,
        mode=resolved_mode,
        script_type=resolved_script,
        command_surface=resolved_surface,
        version=resolved_version,
        executable=executable,
        detection=detection,
        existing_bridge=existing_bridge,
    )


def plan_template_writes(
    target: Path,
    force: bool,
    replacements: dict[str, str],
    spec_kit_bridge: SpecKitBridgeConfig,
) -> list[PlannedWrite]:
    writes: list[PlannedWrite] = []
    template_assets = INSTALL_TEMPLATE_ASSETS + (
        OPTIONAL_SPEC_KIT_TEMPLATE_ASSETS if spec_kit_bridge.enabled else ()
    )

    for asset in template_assets:
        content = render_template(read_asset_text(asset.template_path), replacements)
        destination = target / asset.destination
        action = "create"
        write_path = asset.destination
        if destination.exists():
            if force:
                action = "overwrite"
            else:
                action = "proposal"
                write_path = unique_proposal_destination(target, asset.destination)
        writes.append(
            PlannedWrite(
                destination=asset.destination,
                write_path=write_path,
                content=content,
                source_label=asset.template_path.as_posix(),
                action=action,
            )
        )

    return writes


def render_generated_spec_kit_bridge_doc(replacements: dict[str, str]) -> str:
    return render_template(read_asset_text(SPEC_KIT_BRIDGE_TEMPLATE_PATH), replacements)


def plan_copy_writes(target: Path, force: bool) -> list[PlannedWrite]:
    writes: list[PlannedWrite] = []

    for asset in INSTALL_COPY_ASSETS:
        content = read_asset_text(asset.source_path)
        destination = target / asset.destination
        action = "create"
        write_path = asset.destination
        if destination.exists():
            if force:
                action = "overwrite"
            else:
                action = "proposal"
                write_path = unique_proposal_destination(target, asset.destination)
        writes.append(
            PlannedWrite(
                destination=asset.destination,
                write_path=write_path,
                content=content,
                source_label=asset.source_path.as_posix(),
                action=action,
            )
        )

    return writes


def plan_utility_harness_writes(
    target: Path,
    force: bool,
    utility_harness: UtilityHarnessConfig,
) -> list[PlannedWrite]:
    if not utility_harness.enabled:
        return []

    writes: list[PlannedWrite] = []
    for asset in OPTIONAL_UTILITY_HARNESS_COPY_ASSETS:
        content = read_asset_text(asset.source_path)
        destination = target / asset.destination
        action = "create"
        write_path = asset.destination
        if destination.exists():
            if force:
                action = "overwrite"
            else:
                action = "proposal"
                write_path = unique_proposal_destination(target, asset.destination)
        writes.append(
            PlannedWrite(
                destination=asset.destination,
                write_path=write_path,
                content=content,
                source_label=asset.source_path.as_posix(),
                action=action,
            )
        )
    return writes


def plan_generated_writes(
    target: Path,
    force: bool,
    replacements: dict[str, str],
    pack_selections: tuple[PackSelection, ...],
    manifest_preview: str,
    workflow_selections: tuple[PackSelection, ...] | None = None,
) -> list[PlannedWrite]:
    generated_assets: tuple[tuple[Path, str, str], ...] = (
        (
            GENERATED_OUTPUT_DESTINATIONS[0],
            render_stack_guidance(pack_selections),
            "generated stack guidance",
        ),
        (
            GENERATED_OUTPUT_DESTINATIONS[1],
            render_generated_spec_kit_bridge_doc(replacements),
            "generated Spec Kit bridge guide",
        ),
        (
            GENERATED_OUTPUT_DESTINATIONS[2],
            manifest_preview,
            "generated stack-pack manifest",
        ),
    )
    if workflow_selections is not None and (
        selected_pack_names(workflow_selections)
        or (target / WORKFLOW_GUIDANCE_DESTINATION).exists()
    ):
        generated_assets += (
            (
                WORKFLOW_GUIDANCE_DESTINATION,
                render_workflow_guidance(workflow_selections),
                "generated workflow guidance",
            ),
        )

    writes: list[PlannedWrite] = []
    for destination, content, source_label in generated_assets:
        action = "create"
        write_path = destination
        if (target / destination).exists():
            if force:
                action = "overwrite"
            else:
                action = "proposal"
                write_path = unique_proposal_destination(target, destination)
        writes.append(
            PlannedWrite(
                destination=destination,
                write_path=write_path,
                content=content,
                source_label=source_label,
                action=action,
            )
        )
    return writes


def workflow_managed_destinations(
    target: Path,
    workflow_selections: tuple[PackSelection, ...],
) -> tuple[Path, ...]:
    selected_names = selected_pack_names(workflow_selections)
    destinations: list[Path] = []
    if selected_names or (target / WORKFLOW_GUIDANCE_DESTINATION).exists():
        destinations.append(WORKFLOW_GUIDANCE_DESTINATION)
    if REPOSITORY_IMPROVEMENT_AUDIT_WORKFLOW in selected_names:
        destinations.append(ROADMAP_DESTINATION)
    return tuple(destinations)


def render_audit_roadmap_section() -> str:
    return "\n".join(
        [
            ROADMAP_AUDIT_SECTION_START,
            "## Repository Improvement Audit",
            "",
            "No audit findings recorded yet.",
            "",
            "When Codex completes a full repository improvement audit, update this section with evidence-backed suggested changes, risks, and staged roadmap items. Preserve roadmap content outside this managed section.",
            ROADMAP_AUDIT_SECTION_END,
        ]
    )


def ensure_audit_roadmap_section(existing_text: str | None) -> str:
    section = render_audit_roadmap_section()
    if existing_text is None or not existing_text.strip():
        return f"# Roadmap\n\n{section}\n"

    start_count = existing_text.count(ROADMAP_AUDIT_SECTION_START)
    end_count = existing_text.count(ROADMAP_AUDIT_SECTION_END)
    if start_count == 0 and end_count == 0:
        prefix = "" if existing_text.endswith("\n") else "\n"
        return f"{existing_text}{prefix}\n{section}\n"
    if start_count != 1 or end_count != 1:
        raise ValueError(
            "roadmap.md has malformed repository-improvement audit managed markers; "
            "keep exactly one start marker and one end marker before managing workflow packs."
        )
    if existing_text.index(ROADMAP_AUDIT_SECTION_START) > existing_text.index(ROADMAP_AUDIT_SECTION_END):
        raise ValueError(
            "roadmap.md has reversed repository-improvement audit managed markers."
        )
    start_index = existing_text.index(ROADMAP_AUDIT_SECTION_START)
    end_index = existing_text.index(ROADMAP_AUDIT_SECTION_END) + len(ROADMAP_AUDIT_SECTION_END)
    return f"{existing_text[:start_index]}{section}{existing_text[end_index:]}"


def plan_audit_roadmap_write(
    target: Path,
    workflow_selections: tuple[PackSelection, ...],
) -> PlannedWrite | None:
    if REPOSITORY_IMPROVEMENT_AUDIT_WORKFLOW not in selected_pack_names(workflow_selections):
        return None
    roadmap_path = target / ROADMAP_DESTINATION
    existing_text = roadmap_path.read_text(encoding="utf-8") if roadmap_path.exists() else None
    content = ensure_audit_roadmap_section(existing_text)
    return _plan_changed_write(
        target,
        ROADMAP_DESTINATION,
        content,
        "repository improvement audit roadmap section",
        existing_action="overwrite",
    )


def _managed_section(identifier: str):
    for section in MANAGED_SECTIONS:
        if section.identifier == identifier:
            return section
    raise ValueError(f"Missing managed section spec: {identifier}")


def replace_managed_section_content(
    text: str,
    *,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> str:
    start_count = text.count(start_marker)
    end_count = text.count(end_marker)
    if start_count != 1 or end_count != 1:
        raise ValueError(
            "AGENTS.md must contain exactly one enhancer-managed section marker pair."
        )

    start_index = text.index(start_marker)
    end_index = text.index(end_marker)
    if start_index > end_index:
        raise ValueError("AGENTS.md has reversed enhancer-managed section markers.")

    before = text[: start_index + len(start_marker)]
    after = text[end_index:]
    return f"{before}\n{replacement.strip()}\n{after}"


def normalize_managed_sections(
    text: str,
    section_ids: tuple[str, ...] = (
        SELECTED_STACK_PACKS_SECTION_ID,
        SPEC_KIT_BRIDGE_SECTION_ID,
    ),
) -> str:
    normalized = text
    for section_id in section_ids:
        section = _managed_section(section_id)
        normalized = replace_managed_section_content(
            normalized,
            start_marker=section.start_marker,
            end_marker=section.end_marker,
            replacement="__CODEX_ENHANCER_MANAGED_SECTION__",
        )
    return normalized


def render_managed_agents_update(
    target: Path,
    *,
    section_replacements: dict[str, str],
) -> str:
    if not section_replacements:
        raise ValueError("At least one AGENTS.md managed section replacement is required.")

    first_section = _managed_section(next(iter(section_replacements)))
    agents_path = target / first_section.path
    if not agents_path.exists():
        raise ValueError(
            "Target AGENTS.md is missing; run --upgrade-enhancer before managing packs."
        )

    rendered = agents_path.read_text(encoding="utf-8")
    for section_id, replacement in section_replacements.items():
        section = _managed_section(section_id)
        rendered = replace_managed_section_content(
            rendered,
            start_marker=section.start_marker,
            end_marker=section.end_marker,
            replacement=replacement,
        )
    return rendered


def plan_agents_upgrade_writes(
    target: Path,
    content: str,
    source_label: str,
    pack_selections: tuple[PackSelection, ...],
    spec_kit_bridge: SpecKitBridgeConfig,
    spec_kit_detection: SpecKitDetection,
) -> list[PlannedWrite]:
    section = _managed_section(SELECTED_STACK_PACKS_SECTION_ID)
    destination = section.path
    destination_path = target / destination
    if not destination_path.exists():
        planned = _plan_changed_write(
            target,
            destination,
            content,
            source_label,
            existing_action="proposal",
        )
        return [] if planned is None else [planned]

    writes: list[PlannedWrite] = []
    try:
        managed_content = render_managed_agents_update(
            target,
            section_replacements={
                SELECTED_STACK_PACKS_SECTION_ID: render_agents_summary(pack_selections),
                SPEC_KIT_BRIDGE_SECTION_ID: render_spec_kit_bridge_summary(
                    spec_kit_bridge,
                    spec_kit_detection,
                ),
            },
        )
    except ValueError:
        planned = _plan_changed_write(
            target,
            destination,
            content,
            source_label,
            existing_action="proposal",
        )
        return [] if planned is None else [planned]

    managed_update = _plan_changed_write(
        target,
        destination,
        managed_content,
        "managed AGENTS.md selected stack-pack section",
        existing_action="overwrite",
    )
    if managed_update is not None:
        writes.append(managed_update)

    existing_content = destination_path.read_text(encoding="utf-8")
    existing_shape = normalize_managed_sections(existing_content)
    source_shape = normalize_managed_sections(content)
    if existing_shape != source_shape:
        proposal = _plan_changed_write(
            target,
            destination,
            content,
            source_label,
            existing_action="proposal",
        )
        if proposal is not None:
            writes.append(proposal)

    return writes


def build_upgrade_plan(
    target: Path,
    *,
    spec_kit_mode: str | None = None,
    spec_kit_script: str = "auto",
    spec_kit_command_surface: str = "auto",
    spec_kit_version: str | None = None,
    spec_kit_executable: str | None = None,
    utility_harness_mode: str | None = None,
) -> InstallPlan:
    inspection = inspect_install(target)
    if inspection.status == "not-installed":
        raise ValueError(
            "Target repo does not contain an enhancer install yet; run a full install preview instead."
        )

    resolved_target = inspection.target
    spec_kit_detection = inspection.spec_kit_detection or detect_spec_kit(resolved_target)
    pack_detections = detect_stack_packs(resolved_target)
    workflow_detections = detect_workflow_packs(resolved_target)
    install_state = inspection.install_state or EnhancerInstallState(None, (), (), ())
    spec_kit_bridge = resolve_target_spec_kit_bridge(
        resolved_target,
        detection=spec_kit_detection,
        install_state=install_state,
        mode=spec_kit_mode,
        script_type=spec_kit_script,
        command_surface=spec_kit_command_surface,
        version=spec_kit_version,
        executable=spec_kit_executable,
    )
    utility_harness = resolve_utility_harness(
        mode=utility_harness_mode,
        existing=install_state.utility_harness,
    )
    pack_selections = resolve_manifest_pack_selection(
        pack_detections,
        selected_packs=install_state.selected_packs,
    )
    workflow_selections = resolve_manifest_workflow_selection(
        workflow_detections,
        install_state.selected_workflows,
    )
    ownership = summarize_output_ownership(
        install_managed_destinations(spec_kit_bridge, utility_harness)
        + workflow_managed_destinations(resolved_target, workflow_selections)
    )
    manifest_preview = render_stack_pack_manifest(
        pack_detections,
        selected_packs=selected_pack_names(pack_selections),
        workflow_detections=workflow_detections,
        selected_workflows=selected_pack_names(workflow_selections),
        safe_to_regenerate=ownership.safe_to_regenerate,
        adapt_manually=ownership.adapt_manually,
        spec_kit_bridge=spec_kit_bridge,
        utility_harness=utility_harness,
    )

    writes: list[PlannedWrite] = []
    replacements = build_replacements(
        resolved_target,
        pack_selections,
        spec_kit_bridge,
        spec_kit_detection,
        utility_harness,
        ignore_existing_guidance=(Path("AGENTS.md"),),
    )

    template_assets = INSTALL_TEMPLATE_ASSETS + (
        OPTIONAL_SPEC_KIT_TEMPLATE_ASSETS if spec_kit_bridge.enabled else ()
    )
    for asset in template_assets:
        content = render_template(read_asset_text(asset.template_path), replacements)
        if asset.destination == Path("AGENTS.md"):
            writes.extend(
                plan_agents_upgrade_writes(
                    resolved_target,
                    content,
                    asset.template_path.as_posix(),
                    pack_selections,
                    spec_kit_bridge,
                    spec_kit_detection,
                )
            )
            continue
        planned = _plan_changed_write(
            resolved_target,
            asset.destination,
            content,
            asset.template_path.as_posix(),
            existing_action="proposal",
        )
        if planned is not None:
            writes.append(planned)

    for asset in INSTALL_COPY_ASSETS:
        content = read_asset_text(asset.source_path)
        planned = _plan_changed_write(
            resolved_target,
            asset.destination,
            content,
            asset.source_path.as_posix(),
            existing_action=(
                "overwrite"
                if asset.destination in SOURCE_ALIGNED_UPGRADE_DESTINATIONS
                else "proposal"
            ),
        )
        if planned is not None:
            writes.append(planned)

    if utility_harness.enabled:
        for asset in OPTIONAL_UTILITY_HARNESS_COPY_ASSETS:
            content = read_asset_text(asset.source_path)
            planned = _plan_changed_write(
                resolved_target,
                asset.destination,
                content,
                asset.source_path.as_posix(),
                existing_action="proposal",
            )
            if planned is not None:
                writes.append(planned)

    for planned in plan_generated_writes(
        resolved_target,
        force=True,
        replacements=replacements,
        pack_selections=pack_selections,
        manifest_preview=manifest_preview,
        workflow_selections=workflow_selections,
    ):
        changed = _plan_changed_write(
            resolved_target,
            planned.destination,
            planned.content,
            planned.source_label,
            existing_action="overwrite",
        )
        if changed is not None:
            writes.append(changed)
    roadmap_update = plan_audit_roadmap_write(resolved_target, workflow_selections)
    if roadmap_update is not None:
        writes.append(roadmap_update)

    gitignore = compute_gitignore_update(resolved_target)
    gitignore_plan = gitignore if gitignore.missing_lines else None
    external_steps = (
        tuple(
            [
                ExternalStep(
                    argv=spec_kit_bridge.bootstrap_command,
                    cwd=resolved_target,
                    label="Bootstrap official Spec Kit",
                    source_label="official Spec Kit bootstrap",
                )
            ]
        )
        if spec_kit_bridge.bootstrap_command
        else ()
    )

    return InstallPlan(
        target=resolved_target,
        operation="upgrade-enhancer",
        mode="existing",
        force=False,
        writes=tuple(writes),
        gitignore=gitignore_plan,
        pack_detections=pack_detections,
        pack_selections=pack_selections,
        manifest_preview=manifest_preview,
        workflow_detections=workflow_detections,
        workflow_selections=workflow_selections,
        spec_kit_bridge=spec_kit_bridge,
        spec_kit_detection=spec_kit_detection,
        utility_harness=utility_harness,
        external_steps=external_steps,
    )


def build_pack_management_plan(
    target: Path,
    *,
    add_packs: tuple[str, ...] = (),
    remove_packs: tuple[str, ...] = (),
    set_packs: tuple[str, ...] | None = None,
    require_changes: bool = False,
) -> InstallPlan:
    inspection = inspect_install(target)
    if inspection.status == "not-installed":
        raise ValueError(
            "Target repo does not contain an enhancer install yet; run a full install preview first."
        )
    if inspection.status != "current":
        raise ValueError(
            "Target enhancer install is not current; run --upgrade-enhancer before managing packs."
        )
    if require_changes and not add_packs and not remove_packs and set_packs is None:
        raise ValueError("--manage-packs requires --add-pack, --remove-pack, or --set-pack.")

    resolved_target = inspection.target
    spec_kit_detection = inspection.spec_kit_detection or detect_spec_kit(resolved_target)
    pack_detections = detect_stack_packs(resolved_target)
    workflow_detections = detect_workflow_packs(resolved_target)
    install_state = inspection.install_state or EnhancerInstallState(None, (), (), ())
    spec_kit_bridge = resolve_target_spec_kit_bridge(
        resolved_target,
        detection=spec_kit_detection,
        install_state=install_state,
    )
    utility_harness = resolve_utility_harness(
        mode=None,
        existing=install_state.utility_harness,
    )
    pack_selections = resolve_managed_pack_selection(
        pack_detections,
        current_selected_packs=install_state.selected_packs,
        add_packs=add_packs,
        remove_packs=remove_packs,
        set_packs=set_packs,
    )
    workflow_selections = resolve_manifest_workflow_selection(
        workflow_detections,
        install_state.selected_workflows,
    )
    ownership = summarize_output_ownership(
        install_managed_destinations(spec_kit_bridge, utility_harness)
        + workflow_managed_destinations(resolved_target, workflow_selections)
    )
    manifest_preview = render_stack_pack_manifest(
        pack_detections,
        selected_packs=selected_pack_names(pack_selections),
        workflow_detections=workflow_detections,
        selected_workflows=selected_pack_names(workflow_selections),
        safe_to_regenerate=ownership.safe_to_regenerate,
        adapt_manually=ownership.adapt_manually,
        spec_kit_bridge=spec_kit_bridge,
        utility_harness=utility_harness,
    )
    replacements = build_replacements(
        resolved_target,
        pack_selections,
        spec_kit_bridge,
        spec_kit_detection,
        utility_harness,
        ignore_existing_guidance=(Path("AGENTS.md"),),
    )

    writes: list[PlannedWrite] = []
    agents_update = _plan_changed_write(
        resolved_target,
        Path("AGENTS.md"),
        render_managed_agents_update(
            resolved_target,
            section_replacements={
                SELECTED_STACK_PACKS_SECTION_ID: render_agents_summary(pack_selections),
            },
        ),
        "managed AGENTS.md selected stack-pack section",
        existing_action="overwrite",
    )
    if agents_update is not None:
        writes.append(agents_update)

    for planned in plan_generated_writes(
        resolved_target,
        force=True,
        replacements=replacements,
        pack_selections=pack_selections,
        manifest_preview=manifest_preview,
        workflow_selections=workflow_selections,
    ):
        changed = _plan_changed_write(
            resolved_target,
            planned.destination,
            planned.content,
            planned.source_label,
            existing_action="overwrite",
        )
        if changed is not None:
            writes.append(changed)
    roadmap_update = plan_audit_roadmap_write(resolved_target, workflow_selections)
    if roadmap_update is not None:
        writes.append(roadmap_update)

    return InstallPlan(
        target=resolved_target,
        operation="manage-packs",
        mode="existing",
        force=False,
        writes=tuple(writes),
        gitignore=None,
        pack_detections=pack_detections,
        pack_selections=pack_selections,
        manifest_preview=manifest_preview,
        workflow_detections=workflow_detections,
        workflow_selections=workflow_selections,
        spec_kit_bridge=spec_kit_bridge,
        spec_kit_detection=spec_kit_detection,
        utility_harness=utility_harness,
    )


def build_workflow_management_plan(
    target: Path,
    *,
    add_workflows: tuple[str, ...] = (),
    remove_workflows: tuple[str, ...] = (),
    set_workflows: tuple[str, ...] | None = None,
    require_changes: bool = False,
) -> InstallPlan:
    inspection = inspect_install(target)
    if inspection.status == "not-installed":
        raise ValueError(
            "Target repo does not contain an enhancer install yet; run a full install preview first."
        )
    if inspection.status != "current":
        raise ValueError(
            "Target enhancer install is not current; run --upgrade-enhancer before managing workflow packs."
        )
    if require_changes and not add_workflows and not remove_workflows and set_workflows is None:
        raise ValueError(
            "--manage-workflows requires --add-workflow, --remove-workflow, or --set-workflow."
        )

    resolved_target = inspection.target
    spec_kit_detection = inspection.spec_kit_detection or detect_spec_kit(resolved_target)
    pack_detections = detect_stack_packs(resolved_target)
    workflow_detections = detect_workflow_packs(resolved_target)
    install_state = inspection.install_state or EnhancerInstallState(None, (), (), ())
    spec_kit_bridge = resolve_target_spec_kit_bridge(
        resolved_target,
        detection=spec_kit_detection,
        install_state=install_state,
    )
    utility_harness = resolve_utility_harness(
        mode=None,
        existing=install_state.utility_harness,
    )
    pack_selections = resolve_manifest_pack_selection(
        pack_detections,
        selected_packs=install_state.selected_packs,
    )
    workflow_selections = resolve_managed_pack_selection(
        workflow_detections,
        current_selected_packs=install_state.selected_workflows,
        add_packs=add_workflows,
        remove_packs=remove_workflows,
        set_packs=set_workflows,
        pack_label="workflow pack",
        option_suffix="workflow",
    )
    ownership = summarize_output_ownership(
        install_managed_destinations(spec_kit_bridge, utility_harness)
        + workflow_managed_destinations(resolved_target, workflow_selections)
    )
    manifest_preview = render_stack_pack_manifest(
        pack_detections,
        selected_packs=selected_pack_names(pack_selections),
        workflow_detections=workflow_detections,
        selected_workflows=selected_pack_names(workflow_selections),
        safe_to_regenerate=ownership.safe_to_regenerate,
        adapt_manually=ownership.adapt_manually,
        spec_kit_bridge=spec_kit_bridge,
        utility_harness=utility_harness,
    )
    replacements = build_replacements(
        resolved_target,
        pack_selections,
        spec_kit_bridge,
        spec_kit_detection,
        utility_harness,
        ignore_existing_guidance=(Path("AGENTS.md"),),
    )

    writes: list[PlannedWrite] = []
    for planned in plan_generated_writes(
        resolved_target,
        force=True,
        replacements=replacements,
        pack_selections=pack_selections,
        manifest_preview=manifest_preview,
        workflow_selections=workflow_selections,
    ):
        changed = _plan_changed_write(
            resolved_target,
            planned.destination,
            planned.content,
            planned.source_label,
            existing_action="overwrite",
        )
        if changed is not None:
            writes.append(changed)
    roadmap_update = plan_audit_roadmap_write(resolved_target, workflow_selections)
    if roadmap_update is not None:
        writes.append(roadmap_update)

    return InstallPlan(
        target=resolved_target,
        operation="manage-workflows",
        mode="existing",
        force=False,
        writes=tuple(writes),
        gitignore=None,
        pack_detections=pack_detections,
        pack_selections=pack_selections,
        manifest_preview=manifest_preview,
        workflow_detections=workflow_detections,
        workflow_selections=workflow_selections,
        spec_kit_bridge=spec_kit_bridge,
        spec_kit_detection=spec_kit_detection,
        utility_harness=utility_harness,
    )


def build_spec_kit_bridge_management_plan(
    target: Path,
    *,
    spec_kit_mode: str | None = None,
    spec_kit_script: str = "auto",
    spec_kit_command_surface: str = "auto",
    spec_kit_version: str | None = None,
    spec_kit_executable: str | None = None,
    require_changes: bool = False,
) -> InstallPlan:
    if require_changes and not (
        spec_kit_mode
        or spec_kit_script != "auto"
        or spec_kit_command_surface != "auto"
        or spec_kit_version
        or spec_kit_executable
    ):
        raise ValueError(
            "--manage-spec-kit-bridge requires a Spec Kit bridge option such as --spec-kit-mode."
        )

    inspection = inspect_install(target)
    if inspection.status == "not-installed":
        raise ValueError(
            "Target repo does not contain an enhancer install yet; run a full install preview first."
        )
    if inspection.status != "current":
        raise ValueError(
            "Target enhancer install is not current; run --upgrade-enhancer before managing the Spec Kit bridge."
        )

    resolved_target = inspection.target
    spec_kit_detection = inspection.spec_kit_detection or detect_spec_kit(resolved_target)
    pack_detections = detect_stack_packs(resolved_target)
    workflow_detections = detect_workflow_packs(resolved_target)
    install_state = inspection.install_state or EnhancerInstallState(None, (), (), ())
    spec_kit_bridge = resolve_target_spec_kit_bridge(
        resolved_target,
        detection=spec_kit_detection,
        install_state=install_state,
        mode=spec_kit_mode,
        script_type=spec_kit_script,
        command_surface=spec_kit_command_surface,
        version=spec_kit_version,
        executable=spec_kit_executable,
    )
    utility_harness = resolve_utility_harness(
        mode=None,
        existing=install_state.utility_harness,
    )
    pack_selections = resolve_manifest_pack_selection(
        pack_detections,
        selected_packs=install_state.selected_packs,
    )
    workflow_selections = resolve_manifest_workflow_selection(
        workflow_detections,
        install_state.selected_workflows,
    )
    ownership = summarize_output_ownership(
        install_managed_destinations(spec_kit_bridge, utility_harness)
        + workflow_managed_destinations(resolved_target, workflow_selections)
    )
    manifest_preview = render_stack_pack_manifest(
        pack_detections,
        selected_packs=selected_pack_names(pack_selections),
        workflow_detections=workflow_detections,
        selected_workflows=selected_pack_names(workflow_selections),
        safe_to_regenerate=ownership.safe_to_regenerate,
        adapt_manually=ownership.adapt_manually,
        spec_kit_bridge=spec_kit_bridge,
        utility_harness=utility_harness,
    )
    replacements = build_replacements(
        resolved_target,
        pack_selections,
        spec_kit_bridge,
        spec_kit_detection,
        utility_harness,
        ignore_existing_guidance=(Path("AGENTS.md"),),
    )

    writes: list[PlannedWrite] = []
    agents_update = _plan_changed_write(
        resolved_target,
        Path("AGENTS.md"),
        render_managed_agents_update(
            resolved_target,
            section_replacements={
                SPEC_KIT_BRIDGE_SECTION_ID: render_spec_kit_bridge_summary(
                    spec_kit_bridge,
                    spec_kit_detection,
                ),
            },
        ),
        "managed AGENTS.md Spec Kit bridge section",
        existing_action="overwrite",
    )
    if agents_update is not None:
        writes.append(agents_update)

    if spec_kit_bridge.enabled:
        for asset in OPTIONAL_SPEC_KIT_TEMPLATE_ASSETS:
            content = render_template(read_asset_text(asset.template_path), replacements)
            planned = _plan_changed_write(
                resolved_target,
                asset.destination,
                content,
                asset.template_path.as_posix(),
                existing_action="proposal",
            )
            if planned is not None:
                writes.append(planned)

    for planned in plan_generated_writes(
        resolved_target,
        force=True,
        replacements=replacements,
        pack_selections=pack_selections,
        manifest_preview=manifest_preview,
        workflow_selections=workflow_selections,
    ):
        changed = _plan_changed_write(
            resolved_target,
            planned.destination,
            planned.content,
            planned.source_label,
            existing_action="overwrite",
        )
        if changed is not None:
            writes.append(changed)
    roadmap_update = plan_audit_roadmap_write(resolved_target, workflow_selections)
    if roadmap_update is not None:
        writes.append(roadmap_update)

    external_steps = (
        tuple(
            [
                ExternalStep(
                    argv=spec_kit_bridge.bootstrap_command,
                    cwd=resolved_target,
                    label="Bootstrap official Spec Kit",
                    source_label="official Spec Kit bootstrap",
                )
            ]
        )
        if spec_kit_bridge.bootstrap_command
        else ()
    )

    return InstallPlan(
        target=resolved_target,
        operation="manage-spec-kit-bridge",
        mode="existing",
        force=False,
        writes=tuple(writes),
        gitignore=None,
        pack_detections=pack_detections,
        pack_selections=pack_selections,
        manifest_preview=manifest_preview,
        workflow_detections=workflow_detections,
        workflow_selections=workflow_selections,
        spec_kit_bridge=spec_kit_bridge,
        spec_kit_detection=spec_kit_detection,
        utility_harness=utility_harness,
        external_steps=external_steps,
    )


def compute_gitignore_update(target: Path) -> GitignorePlan:
    gitignore = target / ".gitignore"
    if gitignore.exists():
        existing_lines = set(gitignore.read_text(encoding="utf-8").splitlines())
    else:
        existing_lines = set()
    missing_lines = [line for line in GITIGNORE_LINES if line not in existing_lines]
    return GitignorePlan(destination=Path(".gitignore"), missing_lines=tuple(missing_lines))


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def apply_gitignore_update(path: Path, missing_lines: tuple[str, ...]) -> None:
    if not missing_lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        prefix = "" if existing.endswith("\n") or not existing else "\n"
        missing_text = "\n".join(missing_lines)
        write_text_file(path, f"{existing}{prefix}{missing_text}\n")
        return
    write_text_file(path, "\n".join(missing_lines) + "\n")


def build_install_plan(
    target: Path,
    mode: str = "auto",
    force: bool = False,
    *,
    refresh_generated: bool = False,
    use_recommended_packs: bool = False,
    include_packs: tuple[str, ...] = (),
    exclude_packs: tuple[str, ...] = (),
    spec_kit_mode: str | None = None,
    spec_kit_script: str = "auto",
    spec_kit_command_surface: str = "auto",
    spec_kit_version: str | None = None,
    spec_kit_executable: str | None = None,
    utility_harness_mode: str | None = None,
) -> InstallPlan:
    resolved_target = target.resolve()
    validate_mode(resolved_target, mode)
    effective_mode = infer_mode(resolved_target) if mode == "auto" else mode
    spec_kit_detection = detect_spec_kit(resolved_target)
    pack_detections = detect_stack_packs(resolved_target)
    workflow_detections = detect_workflow_packs(resolved_target)

    if refresh_generated:
        if effective_mode != "existing":
            raise ValueError(
                "--refresh-generated only works on an existing repo with an installed enhancer manifest."
            )

        install_state = load_enhancer_install_state(resolved_target)
        spec_kit_bridge = resolve_target_spec_kit_bridge(
            resolved_target,
            detection=spec_kit_detection,
            install_state=install_state,
        )
        utility_harness = resolve_utility_harness(
            mode=None,
            existing=install_state.utility_harness,
        )
        selected_names = load_selected_packs_from_manifest(resolved_target)
        pack_selections = resolve_manifest_pack_selection(
            pack_detections,
            selected_packs=selected_names,
        )
        workflow_selections = resolve_manifest_workflow_selection(
            workflow_detections,
            install_state.selected_workflows,
        )
        ownership = summarize_output_ownership(
            install_managed_destinations(spec_kit_bridge, utility_harness)
            + workflow_managed_destinations(resolved_target, workflow_selections)
        )
        replacements = build_replacements(
            resolved_target,
            pack_selections,
            spec_kit_bridge,
            spec_kit_detection,
            utility_harness,
            ignore_existing_guidance=(Path("AGENTS.md"),),
        )
        manifest_preview = render_stack_pack_manifest(
            pack_detections,
            selected_packs=selected_pack_names(pack_selections),
            workflow_detections=workflow_detections,
            selected_workflows=selected_pack_names(workflow_selections),
            safe_to_regenerate=ownership.safe_to_regenerate,
            adapt_manually=ownership.adapt_manually,
            spec_kit_bridge=spec_kit_bridge,
            utility_harness=utility_harness,
        )
        writes_list = plan_generated_writes(
            resolved_target,
            force=True,
            replacements=replacements,
            pack_selections=pack_selections,
            manifest_preview=manifest_preview,
            workflow_selections=workflow_selections,
        )
        roadmap_update = plan_audit_roadmap_write(resolved_target, workflow_selections)
        if roadmap_update is not None:
            writes_list.append(roadmap_update)
        writes = tuple(
            writes_list
        )
        return InstallPlan(
            target=resolved_target,
            operation="refresh-generated",
            mode=effective_mode,
            force=False,
            writes=writes,
            gitignore=None,
            pack_detections=pack_detections,
            pack_selections=pack_selections,
            manifest_preview=manifest_preview,
            workflow_detections=workflow_detections,
            workflow_selections=workflow_selections,
            spec_kit_bridge=spec_kit_bridge,
            spec_kit_detection=spec_kit_detection,
            utility_harness=utility_harness,
        )

    gitignore = compute_gitignore_update(resolved_target)
    spec_kit_bridge = resolve_target_spec_kit_bridge(
        resolved_target,
        detection=spec_kit_detection,
        mode=spec_kit_mode,
        script_type=spec_kit_script,
        command_surface=spec_kit_command_surface,
        version=spec_kit_version,
        executable=spec_kit_executable,
    )
    utility_harness = resolve_utility_harness(mode=utility_harness_mode or "off")
    ownership = summarize_output_ownership(
        install_managed_destinations(spec_kit_bridge, utility_harness)
    )
    pack_selections = resolve_stack_pack_selection(
        pack_detections,
        use_recommended_packs=use_recommended_packs,
        include_packs=include_packs,
        exclude_packs=exclude_packs,
    )
    replacements = build_replacements(
        resolved_target,
        pack_selections,
        spec_kit_bridge,
        spec_kit_detection,
        utility_harness,
    )
    manifest_preview = render_stack_pack_manifest(
        pack_detections,
        selected_packs=selected_pack_names(pack_selections),
        safe_to_regenerate=ownership.safe_to_regenerate,
        adapt_manually=ownership.adapt_manually,
        spec_kit_bridge=spec_kit_bridge,
        utility_harness=utility_harness,
    )
    writes = tuple(
        plan_template_writes(
            resolved_target,
            force=force,
            replacements=replacements,
            spec_kit_bridge=spec_kit_bridge,
        )
        + plan_copy_writes(resolved_target, force=force)
        + plan_utility_harness_writes(
            resolved_target,
            force=force,
            utility_harness=utility_harness,
        )
        + plan_generated_writes(
            resolved_target,
            force=force,
            replacements=replacements,
            pack_selections=pack_selections,
            manifest_preview=manifest_preview,
        )
    )
    external_steps = (
        tuple(
            [
                ExternalStep(
                    argv=spec_kit_bridge.bootstrap_command,
                    cwd=resolved_target,
                    label="Bootstrap official Spec Kit",
                    source_label="official Spec Kit bootstrap",
                )
            ]
        )
        if spec_kit_bridge.bootstrap_command
        else ()
    )
    return InstallPlan(
        target=resolved_target,
        operation="install",
        mode=effective_mode,
        force=force,
        writes=writes,
        gitignore=gitignore,
        pack_detections=pack_detections,
        pack_selections=pack_selections,
        manifest_preview=manifest_preview,
        spec_kit_bridge=spec_kit_bridge,
        spec_kit_detection=spec_kit_detection,
        utility_harness=utility_harness,
        external_steps=external_steps,
    )


def format_plan_header(plan: InstallPlan, write: bool) -> str:
    noun = (
        "Codex Enhancer upgrade reconcile plan"
        if plan.operation == "upgrade-enhancer"
        else
        "Codex Enhancer stack-pack management plan"
        if plan.operation == "manage-packs"
        else
        "Codex Enhancer workflow-pack management plan"
        if plan.operation == "manage-workflows"
        else
        "Codex Enhancer Spec Kit bridge management plan"
        if plan.operation == "manage-spec-kit-bridge"
        else
        "Codex Enhancer generated-output refresh"
        if plan.operation == "refresh-generated"
        else "Codex Enhancer install"
    )
    return (
        f"{'Applying' if write else 'Planned'} {noun} into {plan.target} "
        f"(mode={plan.mode}, force={plan.force})"
    )


def format_external_command(argv: tuple[str, ...]) -> str:
    if sys.platform == "win32":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


def _resolve_external_executable(executable: str | None) -> str | None:
    if not executable:
        return None
    candidate = Path(executable)
    if candidate.exists():
        return str(candidate.resolve())
    return shutil.which(executable)


def _external_step_requires_network(step: ExternalStep) -> bool:
    return any(
        argument.startswith(("git+https://", "https://", "http://"))
        for argument in step.argv
    )


def _external_step_pinned_ref(step: ExternalStep) -> str | None:
    for argument in step.argv:
        match = re.search(
            r"git\+https://github\.com/github/spec-kit\.git@(?P<ref>[^#\s]+)",
            argument,
        )
        if match:
            return match.group("ref")
    return None


def _external_step_recovery_hint(
    step: ExternalStep,
    *,
    executable_found: bool,
    requires_network: bool,
) -> str:
    executable = step.argv[0] if step.argv else ""
    if not executable_found:
        if executable == "uvx":
            return "Install uv/uvx or rerun with --spec-kit-exe <path>."
        return "Fix the executable path or rerun with --spec-kit-exe <path>."
    if requires_network:
        return "Ensure network access can fetch the pinned official Spec Kit ref before rerunning with --write."
    return "If this fails, inspect any official files it created, fix the executable or arguments, then rerun the same enhancer command."


def audit_external_step(step: ExternalStep) -> ExternalStepAudit:
    executable = step.argv[0] if step.argv else None
    executable_path = _resolve_external_executable(executable)
    executable_found = executable_path is not None
    executable_status = (
        "missing command"
        if executable is None
        else f"found at {executable_path}"
        if executable_found
        else "not found on PATH"
    )
    requires_network = _external_step_requires_network(step)
    pinned_ref = _external_step_pinned_ref(step)
    warnings: list[str] = []
    if not executable_found:
        warnings.append(f"executable `{executable}` is not available on this machine")
    if requires_network:
        warnings.append("command may need network access to fetch official Spec Kit")
    return ExternalStepAudit(
        label=step.label,
        source_label=step.source_label,
        argv=step.argv,
        command=format_external_command(step.argv),
        cwd=step.cwd,
        executable=executable,
        executable_path=executable_path,
        executable_found=executable_found,
        executable_status=executable_status,
        requires_network=requires_network,
        pinned_ref=pinned_ref,
        warnings=tuple(warnings),
        recovery_hint=_external_step_recovery_hint(
            step,
            executable_found=executable_found,
            requires_network=requires_network,
        ),
    )


def external_step_to_dict(step: ExternalStep) -> dict[str, object]:
    audit = audit_external_step(step)
    return {
        "label": audit.label,
        "source_label": audit.source_label,
        "argv": list(audit.argv),
        "command": audit.command,
        "cwd": str(audit.cwd),
        "executable": audit.executable,
        "executable_path": audit.executable_path,
        "executable_found": audit.executable_found,
        "executable_status": audit.executable_status,
        "requires_network": audit.requires_network,
        "pinned_ref": audit.pinned_ref,
        "order": EXTERNAL_STEP_ORDER,
        "order_note": EXTERNAL_STEP_ORDER_NOTE,
        "warnings": list(audit.warnings),
        "recovery_hint": audit.recovery_hint,
    }


def format_external_step_preview_lines(step: ExternalStep) -> list[str]:
    audit = audit_external_step(step)
    lines = [
        f"- {audit.label}: `{audit.command}`",
        f"  cwd: `{audit.cwd}`",
        f"  executable: `{audit.executable}` {audit.executable_status}",
    ]
    if audit.pinned_ref:
        lines.append(f"  pinned ref: `{audit.pinned_ref}`")
    lines.append(
        "  network: required for official bootstrap source"
        if audit.requires_network
        else "  network: no network URL detected"
    )
    for warning in audit.warnings:
        lines.append(f"  warning: {warning}")
    lines.append(f"  recovery: {audit.recovery_hint}")
    return lines


def format_external_step_summary_lines(step: ExternalStep) -> list[str]:
    audit = audit_external_step(step)
    lines = [
        f"  - {audit.label}: `{audit.command}`",
        f"    executable: `{audit.executable}` {audit.executable_status}",
    ]
    if audit.pinned_ref:
        lines.append(f"    pinned ref: `{audit.pinned_ref}`")
    if audit.requires_network:
        lines.append("    warning: may need network access")
    if not audit.executable_found:
        lines.append(f"    fallback: {audit.recovery_hint}")
    else:
        lines.append(f"    recovery: {audit.recovery_hint}")
    return lines


def format_plan_lines(plan: InstallPlan) -> list[str]:
    lines: list[str] = []
    lines.extend(format_pack_lines(plan))
    workflow_lines = format_workflow_lines(plan)
    if workflow_lines:
        lines.extend(workflow_lines)
    spec_kit_lines = _format_spec_kit_lines(
        plan.spec_kit_bridge,
        plan.spec_kit_detection,
        always_include=False,
    )
    if spec_kit_lines:
        lines.extend(spec_kit_lines)
    utility_lines = _format_utility_harness_lines(
        plan.utility_harness,
        always_include=False,
    )
    if utility_lines:
        lines.extend(utility_lines)
    if plan.external_steps:
        lines.append("External steps:")
        lines.append(f"- Order: {EXTERNAL_STEP_ORDER_NOTE}.")
        for step in plan.external_steps:
            lines.extend(format_external_step_preview_lines(step))
        lines.append("")
    ownership_lines = format_output_ownership_lines(plan)
    if ownership_lines:
        lines.extend(ownership_lines)
        lines.append("")
    if plan.operation == "upgrade-enhancer":
        lines.extend(format_upgrade_write_groups(plan))
        if plan.gitignore is not None:
            lines.extend(
                [
                    "",
                    ".gitignore reconcile:",
                    f"- merge: {plan.gitignore.destination.as_posix()} add {', '.join(plan.gitignore.missing_lines)}",
                ]
            )
        elif not plan.writes:
            lines.append("Upgrade drift: none. The tracked enhancer files already match this source version.")
        return lines

    conflict_lines = format_conflict_severity_lines(plan)
    if conflict_lines:
        lines.extend(conflict_lines)
        lines.append("")
    for planned_write in plan.writes:
        if planned_write.action == "proposal":
            lines.append(
                f"- proposal: {planned_write.write_path.as_posix()} "
                f"(for {planned_write.destination.as_posix()}, from {planned_write.source_label})"
            )
            continue
        lines.append(
            f"- {planned_write.action}: {planned_write.write_path.as_posix()} "
            f"(from {planned_write.source_label})"
        )
    if plan.gitignore is not None:
        if plan.gitignore.missing_lines:
            lines.append(
                f"- merge: {plan.gitignore.destination.as_posix()} add {', '.join(plan.gitignore.missing_lines)}"
            )
        else:
            lines.append(
                f"- merge: {plan.gitignore.destination.as_posix()} already contains required entries"
            )
    return lines


def format_pack_lines(plan: InstallPlan) -> list[str]:
    lines = ["Stack pack selection:"]
    if not plan.pack_selections:
        lines.append("- none")
        lines.append("")
        return lines

    for selection in plan.pack_selections:
        lines.append(f"- {selection.pack.name}: {describe_pack_selection(selection)}")
        if selection.selected or selection.recommended or selection.detected:
            lines.append(f"  {format_pack_decision_hint(selection.pack)}")
    selected_names = selected_pack_names(plan.pack_selections)
    if selected_names:
        rendered_names = ", ".join(f'"{name}"' for name in selected_names)
        lines.append(f"- Manifest preview selected_packs = [{rendered_names}]")
    else:
        lines.append("- Manifest preview selected_packs = []")
    if plan.operation == "upgrade-enhancer":
        lines.append("- Upgrade reconcile keeps the installed pack selection and compares tracked enhancer files against the current source.")
    elif plan.operation == "manage-packs":
        lines.append("- Pack management updates the selected target manifest packs, managed AGENTS section, and generated bridge or pack guidance.")
    elif plan.operation == "manage-spec-kit-bridge":
        lines.append("- Spec Kit bridge management keeps the installed pack selection and updates only enhancer-owned bridge guidance and generated outputs.")
    elif plan.operation == "manage-workflows":
        lines.append("- Workflow management keeps the installed stack-pack selection and updates only workflow guidance plus generated outputs.")
    elif plan.operation == "refresh-generated":
        lines.append("- Stack guidance, the Spec Kit bridge guide, and the pack manifest will be regenerated from the existing target manifest.")
    else:
        lines.append("- Stack guidance, the Spec Kit bridge guide, and the pack manifest will be generated during install.")
    lines.append("")
    return lines


def format_workflow_lines(plan: InstallPlan) -> list[str]:
    if not plan.workflow_selections and plan.operation != "manage-workflows":
        return []

    lines = ["Workflow pack selection:"]
    if not plan.workflow_selections:
        lines.append("- none")
        lines.append("")
        return lines

    for selection in plan.workflow_selections:
        lines.append(
            f"- {selection.pack.name}: "
            f"{describe_pack_selection(selection, option_suffix='workflow')}"
        )
        if selection.selected or selection.recommended or selection.detected:
            lines.append(f"  {format_pack_decision_hint(selection.pack)}")
    selected_names = selected_pack_names(plan.workflow_selections)
    if selected_names:
        rendered_names = ", ".join(f'"{name}"' for name in selected_names)
        lines.append(f"- Manifest preview selected_workflows = [{rendered_names}]")
    else:
        lines.append("- Manifest preview selected_workflows = []")
    if REPOSITORY_IMPROVEMENT_AUDIT_WORKFLOW in selected_names:
        lines.append(
            "- Repository improvement audits will maintain a managed section in root `roadmap.md`."
        )
    if plan.operation == "manage-workflows":
        lines.append(
            "- Workflow management updates workflow guidance, the manifest, and selected workflow-owned outputs."
        )
    elif plan.workflow_selections:
        lines.append(
            "- Existing workflow-pack selection is preserved while this operation updates other enhancer outputs."
        )
    lines.append("")
    return lines


def summarize_conflicts(plan: InstallPlan) -> ConflictSummary:
    if plan.operation in {
        "refresh-generated",
        "upgrade-enhancer",
        "manage-packs",
        "manage-workflows",
        "manage-spec-kit-bridge",
    }:
        return ConflictSummary(
            critical_proposals=(),
            standard_proposals=(),
            critical_overwrites=(),
            standard_overwrites=(),
        )

    critical_proposals: list[Path] = []
    standard_proposals: list[Path] = []
    critical_overwrites: list[Path] = []
    standard_overwrites: list[Path] = []

    for planned_write in plan.writes:
        if planned_write.action not in {"proposal", "overwrite"}:
            continue
        is_critical = planned_write.destination in CRITICAL_CONFLICT_PATHS
        if planned_write.action == "proposal":
            if is_critical:
                critical_proposals.append(planned_write.destination)
            else:
                standard_proposals.append(planned_write.destination)
            continue
        if is_critical:
            critical_overwrites.append(planned_write.destination)
        else:
            standard_overwrites.append(planned_write.destination)

    return ConflictSummary(
        critical_proposals=tuple(critical_proposals),
        standard_proposals=tuple(standard_proposals),
        critical_overwrites=tuple(critical_overwrites),
        standard_overwrites=tuple(standard_overwrites),
    )


def _dedupe_paths(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return tuple(ordered)


def summarize_output_ownership(destinations: tuple[Path, ...]) -> OutputOwnershipSummary:
    ordered_destinations = _dedupe_paths(destinations)
    safe_to_regenerate = tuple(
        path for path in ordered_destinations if path in REGENERABLE_OUTPUT_DESTINATIONS
    )
    adapt_manually = tuple(
        path for path in ordered_destinations if path not in REGENERABLE_OUTPUT_DESTINATIONS
    )
    return OutputOwnershipSummary(
        safe_to_regenerate=safe_to_regenerate,
        adapt_manually=adapt_manually,
    )


def format_output_ownership_lines(plan: InstallPlan) -> list[str]:
    summary = summarize_output_ownership(tuple(item.destination for item in plan.writes))
    if not summary.safe_to_regenerate and not summary.adapt_manually:
        return []

    if plan.operation in {"manage-packs", "manage-workflows", "manage-spec-kit-bridge"}:
        lines = ["Output ownership:"]
        if summary.safe_to_regenerate:
            lines.append("- Regenerated managed outputs: " + _format_conflict_paths(summary.safe_to_regenerate))
        if summary.adapt_manually:
            lines.append("- Managed sections updated in place: " + _format_conflict_paths(summary.adapt_manually))
        if plan.operation == "manage-spec-kit-bridge":
            lines.append("- Official Spec Kit files stay untouched.")
        elif plan.operation == "manage-workflows":
            lines.append("- Repo-owned roadmap content outside managed markers stays untouched.")
        else:
            lines.append("- Repo-owned content outside managed markers stays untouched.")
        return lines

    lines = ["Output ownership:"]
    if summary.safe_to_regenerate:
        lines.append("- Safe to regenerate later: " + _format_conflict_paths(summary.safe_to_regenerate))
    if summary.adapt_manually:
        lines.append("- Adapt manually after install: " + _format_conflict_paths(summary.adapt_manually))
    if plan.operation == "refresh-generated":
        lines.append("- Manual scaffold files stay untouched during refresh.")
    elif plan.operation == "upgrade-enhancer":
        lines.append("- Generated outputs and source-aligned copies are previewed separately from repo-owned proposal files.")
    else:
        lines.append("- Review merged `.gitignore` changes manually if the target repo uses different ignore conventions.")
    return lines


def _format_conflict_paths(paths: tuple[Path, ...]) -> str:
    return ", ".join(f"`{path.as_posix()}`" for path in paths)


def format_upgrade_write_groups(plan: InstallPlan) -> list[str]:
    generated = [
        item for item in plan.writes if item.destination in REGENERABLE_OUTPUT_DESTINATIONS
    ]
    direct_copies = [
        item for item in plan.writes if item.destination in SOURCE_ALIGNED_UPGRADE_DESTINATIONS
    ]
    repo_owned = [
        item
        for item in plan.writes
        if item.destination not in REGENERABLE_OUTPUT_DESTINATIONS
        and item.destination not in SOURCE_ALIGNED_UPGRADE_DESTINATIONS
    ]

    lines: list[str] = []
    if generated:
        lines.extend(["Managed generated outputs:"])
        lines.extend(_format_write_lines(generated))
        lines.append("")
    if direct_copies:
        lines.extend(["Source-aligned direct copies:"])
        lines.extend(_format_write_lines(direct_copies))
        lines.append("")
    if repo_owned:
        lines.extend(["Repo-owned proposal files:"])
        lines.extend(_format_write_lines(repo_owned))
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _format_write_lines(planned_writes: list[PlannedWrite]) -> list[str]:
    lines: list[str] = []
    for planned_write in planned_writes:
        if planned_write.action == "proposal":
            lines.append(
                f"- proposal: {planned_write.write_path.as_posix()} "
                f"(for {planned_write.destination.as_posix()}, from {planned_write.source_label})"
            )
            continue
        lines.append(
            f"- {planned_write.action}: {planned_write.write_path.as_posix()} "
            f"(from {planned_write.source_label})"
        )
    return lines


def format_conflict_severity_lines(plan: InstallPlan) -> list[str]:
    summary = summarize_conflicts(plan)
    if not any(
        (
            summary.critical_proposals,
            summary.standard_proposals,
            summary.critical_overwrites,
            summary.standard_overwrites,
        )
    ):
        return []

    lines = ["Conflict severity:"]
    if summary.critical_proposals:
        lines.append("- Critical proposal files: " + _format_conflict_paths(summary.critical_proposals))
    if summary.standard_proposals:
        lines.append("- Standard proposal files: " + _format_conflict_paths(summary.standard_proposals))
    if summary.critical_overwrites:
        lines.append("- Critical overwrite files: " + _format_conflict_paths(summary.critical_overwrites))
    if summary.standard_overwrites:
        lines.append("- Standard overwrite files: " + _format_conflict_paths(summary.standard_overwrites))
    if summary.critical_proposals and not plan.force:
        lines.append(
            "- Proposal mode keeps the listed critical files in place and writes reviewable copies under "
            "`.codex/enhancer-proposals/`."
        )
    if summary.critical_overwrites:
        lines.append("- Force mode will replace the listed critical enhancer-owned files.")
    return lines


def build_overwrite_confirmation_message(plan: InstallPlan) -> str:
    summary = summarize_conflicts(plan)
    lines = ["Confirm the overwrite list before running the installer."]
    if summary.critical_overwrites:
        lines.extend(
            [
                "",
                "Critical enhancer-owned files will be replaced:",
                *[f"- {path.as_posix()}" for path in summary.critical_overwrites],
            ]
        )
    elif plan.operation == "upgrade-enhancer":
        overwrite_targets = overwrite_paths(plan)
        if overwrite_targets:
            lines.extend(
                [
                    "",
                    "Tracked enhancer files will be updated in place:",
                    *[f"- {path.as_posix()}" for path in overwrite_targets],
                ]
            )
    return "\n".join(lines)


def describe_pack_selection(selection: PackSelection, *, option_suffix: str = "pack") -> str:
    reason = format_detection_reason(
        PackDetection(
            pack=selection.pack,
            detected=selection.detected,
            recommended=selection.recommended,
            reasons=selection.reasons,
        )
    )
    if selection.selection_source == "recommended":
        return f"selected from recommended detection ({reason})"
    if selection.selection_source == "explicit-include":
        return f"selected explicitly via --{option_suffix} ({reason})"
    if selection.selection_source == "explicit-exclude":
        return f"skipped explicitly via --no-{option_suffix} ({reason})"
    if selection.selection_source == "manifest":
        return f"selected from existing target manifest ({reason})"
    if selection.selection_source == "manage-add":
        return f"added by --add-{option_suffix} ({reason})"
    if selection.selection_source == "manage-remove":
        return f"removed by --remove-{option_suffix} ({reason})"
    if selection.selection_source == "manage-set":
        return f"selected by --set-{option_suffix} ({reason})"
    if selection.selection_source == "manage-set-remove":
        return f"removed by --set-{option_suffix} replacement ({reason})"
    if selection.selection_source == "default":
        return f"selected by pack default ({reason})"
    if selection.detected and selection.recommended:
        return f"available as recommended but not selected ({reason})"
    if selection.detected:
        return f"detected but not selected ({reason})"
    return f"not detected ({reason})"


def _first_guidance_item(items: tuple[str, ...]) -> str:
    if not items:
        return "No guidance recorded."
    return items[0]


def format_pack_decision_hint(pack: StackPack) -> str:
    return (
        f"enable when: {_first_guidance_item(pack.guidance.use_when)}; "
        f"adds: {_first_guidance_item(pack.guidance.adds)}; "
        f"skip when: {_first_guidance_item(pack.guidance.skip_when)}"
    )


def format_pack_guidance_block(pack: StackPack, *, indent: str = "  ") -> list[str]:
    lines = [
        f"{indent}What it does: {pack.description}",
        f"{indent}Enable when:",
    ]
    lines.extend(f"{indent}- {item}" for item in pack.guidance.use_when)
    lines.append(f"{indent}Adds:")
    lines.extend(f"{indent}- {item}" for item in pack.guidance.adds)
    lines.append(f"{indent}Skip when:")
    lines.extend(f"{indent}- {item}" for item in pack.guidance.skip_when)
    return lines


def pack_detection_status(detection: PackDetection) -> str:
    if detection.recommended:
        return "recommended"
    if detection.detected:
        return "detected"
    return "not detected"


def _format_pack_signal_items(items: tuple[Path, ...] | tuple[str, ...]) -> str:
    if not items:
        return "none"
    return ", ".join(item.as_posix() if isinstance(item, Path) else item for item in items)


def format_pack_signal_lines(pack: StackPack, *, indent: str = "  ") -> list[str]:
    optional_signals: list[str] = []
    if pack.discovery.any_files:
        optional_signals.append(f"files {_format_pack_signal_items(pack.discovery.any_files)}")
    if pack.discovery.any_globs:
        optional_signals.append(f"globs {_format_pack_signal_items(pack.discovery.any_globs)}")

    lines = [
        f"{indent}Signals checked:",
        f"{indent}- required files: {_format_pack_signal_items(pack.discovery.all_files)}",
        f"{indent}- required directories: {_format_pack_signal_items(pack.discovery.all_dirs)}",
        f"{indent}- optional detection signals: {' or '.join(optional_signals) if optional_signals else 'none'}",
        f"{indent}- exclusion files: {_format_pack_signal_items(pack.discovery.exclude_files)}",
        f"{indent}False-positive boundary: {_first_guidance_item(pack.guidance.skip_when)}",
    ]
    return lines


def pack_catalog_to_dict(target: Path | None = None) -> dict[str, object]:
    packs = load_stack_packs()
    detections_by_name: dict[str, PackDetection] = {}
    if target is not None:
        detections_by_name = {
            detection.pack.name: detection
            for detection in detect_stack_packs(target, packs=packs)
        }

    pack_entries: list[dict[str, object]] = []
    for pack in packs:
        detection = detections_by_name.get(pack.name)
        pack_entries.append(
            {
                "name": pack.name,
                "label": pack.label,
                "description": pack.description,
                "version": pack.version,
                "guidance": {
                    "use_when": list(pack.guidance.use_when),
                    "adds": list(pack.guidance.adds),
                    "skip_when": list(pack.guidance.skip_when),
                },
                "detection_signals": {
                    "all_files": [path.as_posix() for path in pack.discovery.all_files],
                    "any_files": [path.as_posix() for path in pack.discovery.any_files],
                    "any_globs": list(pack.discovery.any_globs),
                    "all_dirs": [path.as_posix() for path in pack.discovery.all_dirs],
                    "exclude_files": [path.as_posix() for path in pack.discovery.exclude_files],
                },
                "status": None if detection is None else pack_detection_status(detection),
                "detected": None if detection is None else detection.detected,
                "recommended": None if detection is None else detection.recommended,
                "evidence": [] if detection is None else list(detection.reasons),
            }
        )

    notes = [
        "Detection uses only local, visible repo evidence such as paths and narrow package metadata.",
        "This report is read-only and does not select packs; use --use-recommended-packs or --pack in an install preview.",
    ]
    return {
        "schema_version": PLAN_JSON_SCHEMA_VERSION,
        "kind": "pack-catalog",
        "target": None if target is None else str(target),
        "notes": notes,
        "packs": pack_entries,
    }


def workflow_catalog_to_dict(target: Path | None = None) -> dict[str, object]:
    workflows = load_workflow_packs()
    detections_by_name: dict[str, PackDetection] = {}
    if target is not None:
        detections_by_name = {
            detection.pack.name: detection
            for detection in detect_workflow_packs(target)
        }

    workflow_entries: list[dict[str, object]] = []
    for workflow in workflows:
        detection = detections_by_name.get(workflow.name)
        workflow_entries.append(
            {
                "name": workflow.name,
                "label": workflow.label,
                "description": workflow.description,
                "version": workflow.version,
                "guidance": {
                    "use_when": list(workflow.guidance.use_when),
                    "adds": list(workflow.guidance.adds),
                    "skip_when": list(workflow.guidance.skip_when),
                },
                "detection_signals": {
                    "all_files": [path.as_posix() for path in workflow.discovery.all_files],
                    "any_files": [path.as_posix() for path in workflow.discovery.any_files],
                    "any_globs": list(workflow.discovery.any_globs),
                    "all_dirs": [path.as_posix() for path in workflow.discovery.all_dirs],
                    "exclude_files": [path.as_posix() for path in workflow.discovery.exclude_files],
                },
                "status": None if detection is None else pack_detection_status(detection),
                "detected": None if detection is None else detection.detected,
                "recommended": None if detection is None else detection.recommended,
                "evidence": [] if detection is None else list(detection.reasons),
            }
        )

    notes = [
        "Workflow packs use the existing stack-pack loader format but live under scaffold/workflow-packs/.",
        "This report is read-only and does not select workflows; use --manage-workflows on an installed target to opt in.",
    ]
    return {
        "schema_version": PLAN_JSON_SCHEMA_VERSION,
        "kind": "workflow-catalog",
        "target": None if target is None else str(target),
        "notes": notes,
        "workflows": workflow_entries,
    }


def format_pack_catalog(target: Path | None = None) -> str:
    packs = load_stack_packs()
    detections_by_name: dict[str, PackDetection] = {}
    if target is not None:
        detections_by_name = {
            detection.pack.name: detection
            for detection in detect_stack_packs(target, packs=packs)
        }

    lines = ["Available stack packs:"]
    if target is not None:
        lines.extend(
            [
                "",
                "Detection audit:",
                f"- Target: `{target.resolve()}`",
                "- Evidence is local only: visible paths plus narrow `package.json` and `pyproject.toml` metadata.",
                "- This report does not select packs. Use `--use-recommended-packs` or `--pack <name>` in an install preview to opt in.",
                "- Not detected means a required signal was missing, an optional signal did not match, or an exclusion/false-positive boundary applied.",
                "",
            ]
        )
    for pack in packs:
        lines.append(f"- {pack.name}: {pack.label}")
        lines.extend(format_pack_guidance_block(pack, indent="  "))
        lines.extend(format_pack_signal_lines(pack, indent="  "))
        if target is not None:
            detection = detections_by_name[pack.name]
            lines.append(f"  status: {pack_detection_status(detection)}")
            lines.append(f"  evidence: {format_detection_reason(detection)}")
    return "\n".join(lines)


def format_workflow_catalog(target: Path | None = None) -> str:
    workflows = load_workflow_packs()
    detections_by_name: dict[str, PackDetection] = {}
    if target is not None:
        detections_by_name = {
            detection.pack.name: detection
            for detection in detect_workflow_packs(target)
        }

    lines = ["Available workflow packs:"]
    if target is not None:
        lines.extend(
            [
                "",
                "Detection audit:",
                f"- Target: `{target.resolve()}`",
                "- Evidence is local only: visible paths and explicit workflow marker files.",
                "- This report does not select workflows. Use `--manage-workflows --add-workflow <name>` on an installed target to opt in.",
                "- Not detected means the optional workflow marker is absent; workflow packs are still manually selectable.",
                "",
            ]
        )
    for workflow in workflows:
        lines.append(f"- {workflow.name}: {workflow.label}")
        lines.extend(format_pack_guidance_block(workflow, indent="  "))
        lines.extend(format_pack_signal_lines(workflow, indent="  "))
        if target is not None:
            detection = detections_by_name[workflow.name]
            lines.append(f"  status: {pack_detection_status(detection)}")
            lines.append(f"  evidence: {format_detection_reason(detection)}")
    return "\n".join(lines)


def _path_text(path: Path) -> str:
    return path.as_posix()


def _write_safety_to_dict(diagnostic: WriteSafetyDiagnostic) -> dict[str, object]:
    return {
        "severity": diagnostic.severity,
        "code": diagnostic.code,
        "message": diagnostic.message,
        "details": list(diagnostic.details),
    }


def _bridge_to_dict(bridge: SpecKitBridgeConfig | None) -> dict[str, object] | None:
    if bridge is None:
        return None
    return {
        "mode": bridge.mode,
        "state": bridge.state,
        "origin": bridge.origin,
        "integration_key": bridge.integration_key,
        "managed_by": bridge.managed_by,
        "script_type": bridge.script_type,
        "command_surface": bridge.command_surface,
        "command_label": bridge.command_label,
        "cli_version": bridge.cli_version,
        "available_commands": list(bridge.available_commands),
        "evidence": list(bridge.evidence),
        "bootstrap_command": list(bridge.bootstrap_command),
    }


def _spec_kit_paths_to_dict(paths: SpecKitPaths) -> dict[str, object]:
    return {
        "specify_root": paths.specify_root,
        "specs_root": paths.specs_root,
        "prompts_root": paths.prompts_root,
        "agents_root": paths.agents_root,
        "codex_skills_root": paths.codex_skills_root,
        "context_file": paths.context_file,
        "constitution": paths.constitution,
    }


def _detection_to_dict(detection: SpecKitDetection | None) -> dict[str, object] | None:
    if detection is None:
        return None
    return {
        "detected": detection.detected,
        "integration": detection.integration,
        "command_surface": detection.command_surface,
        "command_label": detection.command_label,
        "script_type": detection.script_type,
        "version": detection.version,
        "commands": list(detection.commands),
        "evidence": list(detection.evidence),
        "paths": _spec_kit_paths_to_dict(detection.paths),
        "has_git_extension": detection.has_git_extension,
    }


def _utility_to_dict(utility_harness: UtilityHarnessConfig | None) -> dict[str, object] | None:
    if utility_harness is None:
        return None
    return {
        "mode": utility_harness.mode,
        "state": utility_harness.state,
        "enabled": utility_harness.enabled,
        "requirements_file": utility_harness.requirements_file,
        "dependency_files": list(utility_harness.dependency_files),
        "tool_files": list(utility_harness.tool_files),
    }


def _pack_selection_to_dict(selection: PackSelection) -> dict[str, object]:
    return {
        "name": selection.pack.name,
        "label": selection.pack.label,
        "selected": selection.selected,
        "detected": selection.detected,
        "recommended": selection.recommended,
        "selection_source": selection.selection_source,
        "reasons": list(selection.reasons),
    }


def _planned_write_to_dict(write: PlannedWrite) -> dict[str, object]:
    return {
        "destination": _path_text(write.destination),
        "write_path": _path_text(write.write_path),
        "source_label": write.source_label,
        "action": write.action,
    }


def _gitignore_to_dict(gitignore: GitignorePlan | None) -> dict[str, object] | None:
    if gitignore is None:
        return None
    return {
        "destination": _path_text(gitignore.destination),
        "missing_lines": list(gitignore.missing_lines),
    }


def plan_to_dict(
    plan: InstallPlan,
    *,
    write: bool,
    diagnostics: tuple[WriteSafetyDiagnostic, ...] = (),
) -> dict[str, object]:
    selected_names = selected_pack_names(plan.pack_selections)
    selected_workflows = selected_pack_names(plan.workflow_selections)
    summary = summarize_conflicts(plan)
    return {
        "schema_version": PLAN_JSON_SCHEMA_VERSION,
        "kind": "install-plan",
        "operation": plan.operation,
        "target": str(plan.target),
        "mode": plan.mode,
        "write": write,
        "force": plan.force,
        "selected_packs": list(selected_names),
        "pack_selections": [_pack_selection_to_dict(selection) for selection in plan.pack_selections],
        "selected_workflows": list(selected_workflows),
        "workflow_selections": [
            _pack_selection_to_dict(selection) for selection in plan.workflow_selections
        ],
        "spec_kit_bridge": _bridge_to_dict(plan.spec_kit_bridge),
        "spec_kit_detection": _detection_to_dict(plan.spec_kit_detection),
        "utility_harness": _utility_to_dict(plan.utility_harness),
        "writes": [_planned_write_to_dict(write_item) for write_item in plan.writes],
        "write_counts": {
            "create": sum(1 for item in plan.writes if item.action == "create"),
            "overwrite": sum(1 for item in plan.writes if item.action == "overwrite"),
            "proposal": sum(1 for item in plan.writes if item.action == "proposal"),
        },
        "conflicts": {
            "critical_proposals": [_path_text(path) for path in summary.critical_proposals],
            "standard_proposals": [_path_text(path) for path in summary.standard_proposals],
            "critical_overwrites": [_path_text(path) for path in summary.critical_overwrites],
            "standard_overwrites": [_path_text(path) for path in summary.standard_overwrites],
        },
        "gitignore": _gitignore_to_dict(plan.gitignore),
        "diagnostics": [_write_safety_to_dict(diagnostic) for diagnostic in diagnostics],
        "external_steps": [external_step_to_dict(step) for step in plan.external_steps],
        "next_steps": format_next_steps(plan, write=write),
    }


def inspection_to_dict(inspection: InstallInspection) -> dict[str, object]:
    state = inspection.install_state
    return {
        "schema_version": PLAN_JSON_SCHEMA_VERSION,
        "kind": "install-inspection",
        "target": str(inspection.target),
        "manifest_path": _path_text(inspection.manifest_path.relative_to(inspection.target)),
        "source_version": inspection.source_version,
        "target_version": inspection.target_version,
        "status": inspection.status,
        "manifest_schema": None if state is None else state.schema_version,
        "selected_packs": [] if state is None else list(state.selected_packs),
        "selected_workflows": [] if state is None else list(state.selected_workflows),
        "safe_to_regenerate": [] if state is None else list(state.safe_to_regenerate),
        "adapt_manually": [] if state is None else list(state.adapt_manually),
        "spec_kit_bridge": _bridge_to_dict(inspection.spec_kit_bridge),
        "spec_kit_detection": _detection_to_dict(inspection.spec_kit_detection),
        "utility_harness": _utility_to_dict(inspection.utility_harness),
    }


def doctor_to_dict(report: DoctorReport) -> dict[str, object]:
    return {
        "schema_version": PLAN_JSON_SCHEMA_VERSION,
        "kind": "doctor-report",
        "target": str(report.target),
        "repo_kind": report.repo_kind,
        "source_checkout": report.source_checkout,
        "python_version": report.python_version,
        "install_status": report.inspection.status,
        "install": inspection_to_dict(report.inspection),
        "next_steps": list(report.next_steps),
    }


def adaptation_audit_to_dict(target: Path) -> dict[str, object]:
    findings = audit_adaptation(target)
    counts = adaptation_severity_counts(findings)
    return {
        "schema_version": PLAN_JSON_SCHEMA_VERSION,
        "kind": "adaptation-audit",
        "target": str(target.resolve()),
        "status": adaptation_audit_status(findings),
        "finding_count": len(findings),
        "severity_counts": counts,
        "findings": [
            {
                "severity": finding.severity,
                "path": _path_text(finding.path),
                "message": finding.message,
                "recommendation": finding.recommendation,
            }
            for finding in findings
        ],
    }


def format_json(data: dict[str, object]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def format_plan_summary_lines(plan: InstallPlan) -> list[str]:
    selected_names = selected_pack_names(plan.pack_selections)
    selected_workflows = selected_pack_names(plan.workflow_selections)
    summary = summarize_conflicts(plan)
    lines = [
        "Plan summary:",
        f"- Operation: `{plan.operation}`",
        f"- Target: `{plan.target}`",
        f"- Mode: `{plan.mode}`",
        f"- Force: `{plan.force}`",
        "- Selected packs: "
        + (", ".join(f"`{name}`" for name in selected_names) if selected_names else "none"),
        "- Selected workflows: "
        + (", ".join(f"`{name}`" for name in selected_workflows) if selected_workflows else "none"),
        f"- Writes: {len(plan.writes)} total; "
        f"{sum(1 for item in plan.writes if item.action == 'create')} create, "
        f"{sum(1 for item in plan.writes if item.action == 'overwrite')} overwrite, "
        f"{sum(1 for item in plan.writes if item.action == 'proposal')} proposal",
    ]
    if plan.gitignore is not None:
        gitignore_note = (
            ", ".join(plan.gitignore.missing_lines)
            if plan.gitignore.missing_lines
            else "already aligned"
        )
        lines.append(f"- .gitignore: {gitignore_note}")
    if plan.spec_kit_bridge is not None:
        lines.append(f"- Spec Kit bridge: `{plan.spec_kit_bridge.mode}` / `{plan.spec_kit_bridge.state}`")
    if plan.utility_harness is not None:
        lines.append(f"- Utility Harness: `{plan.utility_harness.mode}` / `{plan.utility_harness.state}`")
    if plan.external_steps:
        lines.append(f"- External steps: {len(plan.external_steps)} ({EXTERNAL_STEP_ORDER_NOTE})")
        for step in plan.external_steps:
            lines.extend(format_external_step_summary_lines(step))
    if summary.critical_proposals or summary.critical_overwrites:
        critical = len(summary.critical_proposals) + len(summary.critical_overwrites)
        lines.append(f"- Critical conflicts: {critical}")
    return lines


def _existing_file_lines(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _truncate_diff_lines(
    rendered: list[str],
    *,
    limit: int,
    full: bool,
) -> list[str]:
    if full or limit <= 0 or len(rendered) <= limit:
        return rendered
    hidden = len(rendered) - limit
    return [
        *rendered[:limit],
        f"... diff truncated after {limit} lines; {hidden} more lines hidden. Re-run with --diff-full to show everything.",
    ]


def format_plan_diff_lines(
    plan: InstallPlan,
    *,
    full: bool = False,
    file_line_limit: int = DEFAULT_DIFF_FILE_LINE_LIMIT,
) -> list[str]:
    lines: list[str] = []
    for write_item in plan.writes:
        existing = _existing_file_lines(plan.target / write_item.destination)
        planned = write_item.content.splitlines()
        if existing == planned:
            continue
        fromfile = write_item.destination.as_posix()
        tofile = write_item.write_path.as_posix()
        diff = difflib.unified_diff(existing, planned, fromfile=fromfile, tofile=tofile, lineterm="")
        rendered = _truncate_diff_lines(list(diff), limit=file_line_limit, full=full)
        if rendered:
            lines.extend(rendered)
            if lines[-1] != "":
                lines.append("")
    if plan.gitignore is not None and plan.gitignore.missing_lines:
        lines.append(f"# .gitignore merge adds: {', '.join(plan.gitignore.missing_lines)}")
    if not lines:
        return ["- No planned text diffs."]
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _truncated_status_details(status_lines: tuple[str, ...], *, limit: int = 8) -> tuple[str, ...]:
    if len(status_lines) <= limit:
        return status_lines
    hidden = len(status_lines) - limit
    return (*status_lines[:limit], f"... {hidden} more local change(s) not shown.")


def _blocking_or_warning(blocked: bool) -> str:
    return "error" if blocked else "warning"


def collect_write_safety_diagnostics(
    target: Path,
    *,
    allow_dirty: bool = False,
    allow_source_target: bool = False,
) -> tuple[WriteSafetyDiagnostic, ...]:
    diagnostics: list[WriteSafetyDiagnostic] = []
    if target.exists() and target.is_dir() and looks_like_source_repo(target):
        diagnostics.append(
            WriteSafetyDiagnostic(
                severity=_blocking_or_warning(not allow_source_target),
                code="source-checkout-target",
                message=(
                    "Target looks like the Codex Enhancer source checkout, not an install target. "
                    "Installing into it can create proposal files and confusing scaffold drift."
                ),
                details=(
                    "Use a separate target repo path, or rerun with --allow-source-target if this is deliberate.",
                ),
            )
        )

    if not target.exists() or not target.is_dir() or not (target / ".git").exists():
        return tuple(diagnostics)

    git = shutil.which("git")
    if git is None:
        diagnostics.append(
            WriteSafetyDiagnostic(
                severity=_blocking_or_warning(not allow_dirty),
                code="git-status-unavailable",
                message="Target has .git metadata, but `git` was not found; clean state cannot be verified.",
                details=("Install Git, inspect the target manually, or rerun with --allow-dirty if this is deliberate.",),
            )
        )
        return tuple(diagnostics)

    try:
        completed = subprocess.run(
            [git, "-C", str(target), "status", "--short", "--untracked-files=normal"],
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_STATUS_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        diagnostics.append(
            WriteSafetyDiagnostic(
                severity=_blocking_or_warning(not allow_dirty),
                code="git-status-unavailable",
                message="Target has .git metadata, but `git status --short` could not run.",
                details=(str(error), "Rerun with --allow-dirty only if applying over this state is deliberate."),
            )
        )
        return tuple(diagnostics)
    except subprocess.TimeoutExpired:
        diagnostics.append(
            WriteSafetyDiagnostic(
                severity=_blocking_or_warning(not allow_dirty),
                code="git-status-timeout",
                message=(
                    f"`git status --short` timed out after {GIT_STATUS_TIMEOUT_SECONDS} seconds; "
                    "clean state cannot be verified."
                ),
                details=("Run `git status --short` in the target repo, or rerun with --allow-dirty if this is deliberate.",),
            )
        )
        return tuple(diagnostics)

    if completed.returncode != 0:
        details = tuple(
            line.strip()
            for line in (completed.stderr or completed.stdout).splitlines()
            if line.strip()
        )
        diagnostics.append(
            WriteSafetyDiagnostic(
                severity=_blocking_or_warning(not allow_dirty),
                code="git-status-failed",
                message="Target has .git metadata, but `git status --short` failed; clean state cannot be verified.",
                details=(details or (f"git exited with code {completed.returncode}",))
                + ("Rerun with --allow-dirty only if applying over this state is deliberate.",),
            )
        )
        return tuple(diagnostics)

    status_lines = tuple(line for line in completed.stdout.splitlines() if line.strip())
    if not status_lines:
        return tuple(diagnostics)

    diagnostics.append(
        WriteSafetyDiagnostic(
            severity=_blocking_or_warning(not allow_dirty),
            code="dirty-git-worktree",
            message=(
                f"Target git worktree already has {len(status_lines)} local change(s) before enhancer apply. "
                "Review `git status --short` or commit/stash unrelated work first."
            ),
            details=_truncated_status_details(status_lines)
            + ("Rerun with --allow-dirty only if applying over this state is deliberate.",),
        )
    )
    return tuple(diagnostics)


def format_write_safety_lines(diagnostics: tuple[WriteSafetyDiagnostic, ...]) -> list[str]:
    if not diagnostics:
        return []

    lines = ["Write safety:"]
    for diagnostic in diagnostics:
        lines.append(f"- {diagnostic.severity}: {diagnostic.message}")
        for detail in diagnostic.details:
            lines.append(f"  {detail}")
    return lines


def has_blocking_write_safety_diagnostics(
    diagnostics: tuple[WriteSafetyDiagnostic, ...],
) -> bool:
    return any(diagnostic.severity == "error" for diagnostic in diagnostics)


def format_write_safety_block_message(
    diagnostics: tuple[WriteSafetyDiagnostic, ...],
) -> str:
    lines = ["Write safety blocked apply:"]
    for diagnostic in diagnostics:
        lines.append(f"- {diagnostic.severity}: {diagnostic.message}")
        for detail in diagnostic.details:
            lines.append(f"  {detail}")
    return "\n".join(lines)


def format_plan_report(
    plan: InstallPlan,
    write: bool,
    *,
    summary: bool = False,
    include_diff: bool = False,
    diff_full: bool = False,
    diagnostics: tuple[WriteSafetyDiagnostic, ...] = (),
) -> str:
    lines = [
        format_plan_header(plan, write),
        *(format_plan_summary_lines(plan) if summary else format_plan_lines(plan)),
    ]
    write_safety_lines = format_write_safety_lines(diagnostics)
    if write_safety_lines:
        lines.extend(["", *write_safety_lines])
    if include_diff:
        lines.extend(["", "Diff preview:", *format_plan_diff_lines(plan, full=diff_full)])
    if plan.operation == "upgrade-enhancer":
        lines.extend(["", *format_next_steps(plan, write=write)])
        return "\n".join(lines)

    if write:
        lines.extend(["", *format_next_steps(plan, write=True)])
        return "\n".join(lines)

    lines.extend(
        [
            "",
            *format_after_install_preview(plan),
            "",
            *format_next_steps(plan, write=False),
        ]
    )
    return "\n".join(lines)


def format_next_steps(plan: InstallPlan, write: bool) -> list[str]:
    proposals = [item for item in plan.writes if item.action == "proposal"]
    bridge_enabled = plan.spec_kit_bridge is not None and plan.spec_kit_bridge.enabled
    utility_enabled = plan.utility_harness is not None and plan.utility_harness.enabled
    if plan.operation == "upgrade-enhancer":
        if not write:
            lines = [
                "Next step:",
                "- Re-run this command with `--upgrade-enhancer --write` when the grouped reconcile plan looks correct.",
                "- If you only need managed outputs today, use `--refresh-generated --write` instead of a full reconcile.",
            ]
            if plan.external_steps:
                lines.append("- Official Spec Kit bootstrap will run before enhancer writes during apply.")
            return lines

        lines = ["Next steps:"]
        if not plan.writes and plan.gitignore is None:
            lines.append("- No reconcile changes were needed; the tracked enhancer files already matched this source version.")
        elif proposals:
            lines.append(
                "- Review the proposal files under `.codex/enhancer-proposals/` and merge the repo-owned scaffold changes you want to keep."
            )
            lines.append(
                "- Use the `adapt-enhancer` skill after merging if repo-specific guidance needs another cleanup pass."
            )
        else:
            lines.append("- Repo-owned scaffold files were already aligned, so only tracked managed outputs and source-aligned copies were updated in place.")
        if plan.gitignore is not None and plan.gitignore.missing_lines:
            lines.append("- Review merged `.gitignore` entries if the target repo uses different ignore conventions.")
        if bridge_enabled:
            lines.append("- Review `docs/ai/spec-kit-bridge.md` and any installed bridge skills before feature work.")
        if utility_enabled:
            lines.append("- Review `docs/ai/utility-harness.md` before installing or running Codex helper dependencies.")
        lines.append("- Run `codex-enhancer audit <target>` from an installed CLI, or `python scripts/codex_enhancer_cli.py audit <target>` from the enhancer source checkout.")
        lines.append(f"- Run `{CHECK_COMMAND}` in the target repo.")
        lines.append(f"- Run `{TEST_COMMAND}` in the target repo.")
        return lines

    if not write:
        action = (
            "refresh preview"
            if plan.operation == "refresh-generated"
            else "Spec Kit bridge-management preview"
            if plan.operation == "manage-spec-kit-bridge"
            else "pack-management preview"
            if plan.operation == "manage-packs"
            else "workflow-management preview"
            if plan.operation == "manage-workflows"
            else "preview"
        )
        lines = [
            "Next step:",
            f"- Re-run this command with --write when the {action} looks correct.",
        ]
        if plan.external_steps:
            lines.append("- Official Spec Kit bootstrap will run before enhancer files are written.")
        return lines

    lines = ["Next steps:"]
    if plan.operation == "manage-packs":
        selected_names = selected_pack_names(plan.pack_selections)
        if selected_names:
            lines.append(
                "- Review the updated managed stack-pack section in `AGENTS.md` for: "
                + ", ".join(f"`{name}`" for name in selected_names)
                + "."
            )
        else:
            lines.append("- Review the updated managed stack-pack section in `AGENTS.md`; no packs are selected now.")
        lines.append("- Review the regenerated `docs/ai/stack-guidance.md`, `docs/ai/spec-kit-bridge.md`, and `.codex/enhancer/manifest.toml`.")
        lines.append(f"- Run `{CHECK_COMMAND}` in the target repo.")
        lines.append(f"- Run `{TEST_COMMAND}` in the target repo.")
        return lines

    if plan.operation == "manage-workflows":
        selected_names = selected_pack_names(plan.workflow_selections)
        if selected_names:
            lines.append(
                "- Review the regenerated `docs/ai/workflow-guidance.md` for: "
                + ", ".join(f"`{name}`" for name in selected_names)
                + "."
            )
        else:
            lines.append("- Review `docs/ai/workflow-guidance.md`; no workflow packs are selected now.")
        if REPOSITORY_IMPROVEMENT_AUDIT_WORKFLOW in selected_names:
            lines.append("- Review the managed repository-improvement audit section in root `roadmap.md`.")
        lines.append("- Review `.codex/enhancer/manifest.toml` for the selected_workflows state.")
        lines.append(f"- Run `{CHECK_COMMAND}` in the target repo.")
        lines.append(f"- Run `{TEST_COMMAND}` in the target repo.")
        return lines

    if plan.operation == "manage-spec-kit-bridge":
        if bridge_enabled:
            lines.append("- Review the updated managed Spec Kit bridge section in `AGENTS.md` and the regenerated `docs/ai/spec-kit-bridge.md`.")
            lines.append("- Review any bridge skill proposals under `.codex/enhancer-proposals/` before merging them.")
        else:
            lines.append("- Review the updated managed Spec Kit bridge section in `AGENTS.md`; the bridge is now off.")
        lines.append("- Confirm official Spec Kit-owned files under `.specify/`, `specs/`, `.github/`, or `.agents/` were not edited by the enhancer.")
        lines.append(f"- Run `{CHECK_COMMAND}` in the target repo.")
        lines.append(f"- Run `{TEST_COMMAND}` in the target repo.")
        return lines

    if plan.operation == "refresh-generated":
        lines.extend(render_refresh_follow_up_lines(plan.pack_selections))
        workflow_names = selected_pack_names(plan.workflow_selections)
        if workflow_names:
            lines.append("- Review the refreshed `docs/ai/workflow-guidance.md` for selected workflow packs.")
        if REPOSITORY_IMPROVEMENT_AUDIT_WORKFLOW in workflow_names:
            lines.append("- Confirm root `roadmap.md` still preserves any existing audit roadmap notes.")
        lines.append("- Review the refreshed `docs/ai/spec-kit-bridge.md` if this repo uses the Spec Kit bridge.")
        lines.append(f"- Run `{CHECK_COMMAND}` in the target repo.")
        lines.append(f"- Run `{TEST_COMMAND}` in the target repo.")
        return lines

    if proposals:
        lines.append(
            "- Review the proposal files under `.codex/enhancer-proposals/` and merge them into the live repo files."
        )
        lines.append(
            "- Use the `adapt-enhancer` skill after copying or merging to remove inherited generic guidance."
        )
    else:
        lines.append(
            "- Use the `adapt-enhancer` skill to replace any inherited generic sections with repo-specific guidance."
        )
    lines.extend(render_install_follow_up_lines(plan.pack_selections))
    if bridge_enabled:
        lines.append("- Review `docs/ai/spec-kit-bridge.md` and the bridge skills before using Spec Kit-driven feature branches.")
    if utility_enabled:
        lines.append("- Review `docs/ai/utility-harness.md` and keep `requirements-codex.txt` out of production dependency flows.")
    lines.append("- Run `codex-enhancer audit <target>` from an installed CLI, or `python scripts/codex_enhancer_cli.py audit <target>` from the enhancer source checkout.")
    lines.append(f"- Run `{CHECK_COMMAND}` in the target repo.")
    lines.append(f"- Run `{TEST_COMMAND}` in the target repo.")
    return lines


def format_after_install_preview(plan: InstallPlan) -> list[str]:
    heading = (
        "After refresh:"
        if plan.operation == "refresh-generated"
        else "After Spec Kit bridge management:"
        if plan.operation == "manage-spec-kit-bridge"
        else "After workflow management:"
        if plan.operation == "manage-workflows"
        else "After pack management:"
        if plan.operation == "manage-packs"
        else "After install:"
    )
    return [heading, *format_next_steps(plan, write=True)]


def overwrite_paths(plan: InstallPlan) -> tuple[Path, ...]:
    return tuple(item.destination for item in plan.writes if item.action == "overwrite")


def proposal_paths(plan: InstallPlan) -> tuple[Path, ...]:
    return tuple(item.write_path for item in plan.writes if item.action == "proposal")


def run_external_step(step: ExternalStep) -> None:
    if not step.argv:
        raise RuntimeError(f"{step.label} failed because no command was configured.")
    executable = step.argv[0]
    if not Path(executable).exists() and shutil.which(executable) is None:
        audit = audit_external_step(step)
        raise RuntimeError(
            f"{step.label} failed before enhancer-owned files were written because `{executable}` was not found.\n"
            f"Command: `{audit.command}`\n"
            f"Working directory: `{audit.cwd}`\n"
            f"Recovery: {audit.recovery_hint}"
        )
    try:
        completed = subprocess.run(
            step.argv,
            cwd=step.cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=EXTERNAL_STEP_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        audit = audit_external_step(step)
        raise RuntimeError(
            f"{step.label} failed before enhancer-owned files were written because `{executable}` was not found.\n"
            f"Command: `{audit.command}`\n"
            f"Working directory: `{audit.cwd}`\n"
            f"Recovery: {audit.recovery_hint}"
        ) from error
    except subprocess.TimeoutExpired as error:
        audit = audit_external_step(step)
        raise RuntimeError(
            f"{step.label} timed out after {EXTERNAL_STEP_TIMEOUT_SECONDS} seconds.\n"
            f"Command: `{audit.command}`\n"
            f"Working directory: `{audit.cwd}`\n"
            "Recovery: inspect the target for any files written by the external tool, fix the executable, "
            "version, or network problem, then rerun the same enhancer command."
        ) from error
    if completed.returncode == 0:
        return

    output_parts = [part.strip() for part in (completed.stdout, completed.stderr) if part.strip()]
    details = "\n".join(output_parts)
    recovery = (
        "Recovery: inspect the target for any files written by the external tool, fix the bootstrap problem, "
        "then rerun the same enhancer command. Enhancer-owned files are written only after external steps succeed."
    )
    audit = audit_external_step(step)
    if details:
        raise RuntimeError(
            f"{step.label} failed.\n"
            f"Command: `{audit.command}`\n"
            f"Working directory: `{audit.cwd}`\n"
            f"{details}\n"
            f"{recovery}"
        )
    raise RuntimeError(
        f"{step.label} failed with exit code {completed.returncode}.\n"
        f"Command: `{audit.command}`\n"
        f"Working directory: `{audit.cwd}`\n"
        f"{recovery}"
    )


def _format_limited_paths(paths: tuple[Path, ...], *, limit: int = 8) -> list[str]:
    rendered = [f"  - {path.as_posix()}" for path in paths[:limit]]
    hidden = len(paths) - limit
    if hidden > 0:
        rendered.append(f"  - ... {hidden} more path(s) not shown.")
    return rendered


def build_apply_failure_message(
    plan: InstallPlan,
    *,
    action: str,
    failed_path: Path,
    error: OSError,
    completed_paths: tuple[Path, ...],
) -> str:
    relative_failed = failed_path.relative_to(plan.target) if failed_path.is_relative_to(plan.target) else failed_path
    lines = [
        f"Failed while {action} `{relative_failed.as_posix()}`: {error}",
        "Recovery:",
        "- Inspect the target repo before rerunning; Codex Enhancer does not roll back partial writes automatically.",
        f"- Failed write target: `{relative_failed.as_posix()}`.",
    ]
    if completed_paths:
        lines.append("- Likely enhancer-owned files already touched in this run:")
        lines.extend(_format_limited_paths(completed_paths))
    else:
        lines.append("- No enhancer-owned file writes completed before this failure.")
    lines.append("- Fix the permission, lock, or path conflict, then rerun the same enhancer command.")
    return "\n".join(lines)


def apply_install_plan(
    plan: InstallPlan,
    progress_callback: ProgressCallback | None = None,
    *,
    allow_dirty: bool = False,
    allow_source_target: bool = False,
) -> None:
    diagnostics = collect_write_safety_diagnostics(
        plan.target,
        allow_dirty=allow_dirty,
        allow_source_target=allow_source_target,
    )
    if has_blocking_write_safety_diagnostics(diagnostics):
        raise RuntimeError(format_write_safety_block_message(diagnostics))

    total_steps = len(plan.external_steps) + len(plan.writes) + (1 if plan.gitignore is not None else 0)
    current_step = 0
    completed_paths: list[Path] = []

    if progress_callback:
        if plan.operation == "upgrade-enhancer":
            message = "Preparing upgrade..."
        elif plan.operation == "manage-spec-kit-bridge":
            message = "Preparing Spec Kit bridge management..."
        elif plan.operation == "manage-workflows":
            message = "Preparing workflow management..."
        elif plan.operation == "manage-packs":
            message = "Preparing pack management..."
        elif plan.operation == "refresh-generated":
            message = "Preparing refresh..."
        else:
            message = "Preparing install..."
        progress_callback(
            current_step,
            total_steps,
            message,
        )

    plan.target.mkdir(parents=True, exist_ok=True)
    for external_step in plan.external_steps:
        run_external_step(external_step)
        current_step += 1
        if progress_callback:
            progress_callback(current_step, total_steps, external_step.label)

    for planned_write in plan.writes:
        absolute_write_path = plan.target / planned_write.write_path
        try:
            write_text_file(absolute_write_path, planned_write.content)
        except OSError as error:
            raise RuntimeError(
                build_apply_failure_message(
                    plan,
                    action="writing",
                    failed_path=absolute_write_path,
                    error=error,
                    completed_paths=tuple(completed_paths),
                )
            ) from error
        completed_paths.append(planned_write.write_path)
        current_step += 1
        if progress_callback:
            progress_callback(
                current_step,
                total_steps,
                f"{planned_write.action.title()} {planned_write.write_path.as_posix()}",
            )

    if plan.gitignore is not None:
        absolute_gitignore_path = plan.target / plan.gitignore.destination
        try:
            apply_gitignore_update(absolute_gitignore_path, plan.gitignore.missing_lines)
        except OSError as error:
            raise RuntimeError(
                build_apply_failure_message(
                    plan,
                    action="updating",
                    failed_path=absolute_gitignore_path,
                    error=error,
                    completed_paths=tuple(completed_paths),
                )
            ) from error
        completed_paths.append(plan.gitignore.destination)
        current_step += 1
        if progress_callback:
            message = (
                f"Merged {plan.gitignore.destination.as_posix()}"
                if plan.gitignore.missing_lines
                else f"Checked {plan.gitignore.destination.as_posix()}"
            )
            progress_callback(current_step, total_steps, message)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Common previews:\n"
            "  python scripts/install_enhancer.py --doctor --target ../repo\n"
            "  python scripts/install_enhancer.py --target ../repo --mode existing --summary\n"
            "  python scripts/install_enhancer.py --target ../repo --mode existing --summary --diff\n"
            "  python scripts/install_enhancer.py --target ../repo --inspect-install --json\n\n"
            "Preview is the default. Use --write only after reviewing the plan."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        help="path to the new or existing repository that should receive the enhancer scaffold",
    )
    parser.add_argument(
        "--list-packs",
        action="store_true",
        help="print the available stack packs and exit",
    )
    parser.add_argument(
        "--list-workflows",
        action="store_true",
        help="print the available workflow packs and exit",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="run a read-only first-run diagnostic for a source checkout, installed target, or plain repo",
    )
    parser.add_argument(
        "--inspect-install",
        action="store_true",
        help="inspect source-vs-target enhancer install state without planning writes",
    )
    parser.add_argument(
        "--audit-adaptation",
        action="store_true",
        help="audit an installed target for inherited generic guidance, placeholders, and proposal files",
    )
    parser.add_argument(
        "--spec-kit-report",
        action="store_true",
        help="print a read-only report of detected Spec Kit feature artifacts",
    )
    parser.add_argument(
        "--spec-kit-sync-report",
        action="store_true",
        help="print a read-only Spec Kit feature sync report for changed paths",
    )
    parser.add_argument(
        "--spec-kit-feature",
        help="limit Spec Kit reports to a feature directory name or numeric prefix",
    )
    parser.add_argument(
        "--spec-kit-changed-path",
        action="append",
        default=[],
        help="changed path to include in --spec-kit-sync-report; may be repeated",
    )
    parser.add_argument(
        "--spec-kit-base",
        help="git base ref for --spec-kit-sync-report path discovery using git diff --name-only",
    )
    parser.add_argument(
        "--upgrade-enhancer",
        action="store_true",
        help="preview or apply a reconcile of an existing enhancer install against the current source repo",
    )
    parser.add_argument(
        "--manage-packs",
        action="store_true",
        help="preview or apply selected stack-pack changes in an existing enhancer install",
    )
    parser.add_argument(
        "--manage-workflows",
        action="store_true",
        help="preview or apply selected workflow-pack changes in an existing enhancer install",
    )
    parser.add_argument(
        "--manage-spec-kit-bridge",
        action="store_true",
        help="preview or apply Spec Kit bridge mode changes for an existing enhancer install",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "new", "existing"),
        default="auto",
        help="treat the target as a new repo, an existing repo, or infer automatically",
    )
    write_mode = parser.add_mutually_exclusive_group()
    write_mode.add_argument(
        "--write",
        dest="write",
        action="store_true",
        help="apply the install or refresh instead of only printing a preview plan",
    )
    write_mode.add_argument(
        "--dry-run",
        dest="write",
        action="store_false",
        help="preview the plan without writing files; this is the default",
    )
    parser.set_defaults(write=False)
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print a concise plan summary instead of the full human preview",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="include a unified diff preview for planned text writes",
    )
    parser.add_argument(
        "--diff-full",
        action="store_true",
        help="show full per-file diffs instead of truncating large --diff output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON for reports, inspections, audits, and plans",
    )
    parser.add_argument(
        "--refresh-generated",
        action="store_true",
        help="re-render only enhancer-managed generated outputs in an existing target repo",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite colliding files instead of writing proposals under .codex/enhancer-proposals/",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="allow --write when git status is dirty or cannot verify a clean target worktree",
    )
    parser.add_argument(
        "--allow-source-target",
        action="store_true",
        help="allow --write when the target looks like the Codex Enhancer source checkout",
    )
    parser.add_argument(
        "--use-recommended-packs",
        action="store_true",
        help="select all detected stack packs that are marked as recommended",
    )
    parser.add_argument(
        "--pack",
        action="append",
        default=[],
        help="explicitly select a stack pack by name; repeatable",
    )
    parser.add_argument(
        "--no-pack",
        action="append",
        default=[],
        help="explicitly skip a stack pack by name; repeatable",
    )
    parser.add_argument(
        "--add-pack",
        action="append",
        default=[],
        help="add a stack pack to an existing installed manifest; repeatable and requires --manage-packs",
    )
    parser.add_argument(
        "--remove-pack",
        action="append",
        default=[],
        help="remove a stack pack from an existing installed manifest; repeatable and requires --manage-packs",
    )
    parser.add_argument(
        "--set-pack",
        action="append",
        default=[],
        help="replace the installed stack-pack selection with this exact pack set; repeatable and requires --manage-packs",
    )
    parser.add_argument(
        "--add-workflow",
        action="append",
        default=[],
        help="add a workflow pack to an existing installed manifest; repeatable and requires --manage-workflows",
    )
    parser.add_argument(
        "--remove-workflow",
        action="append",
        default=[],
        help="remove a workflow pack from an existing installed manifest; repeatable and requires --manage-workflows",
    )
    parser.add_argument(
        "--set-workflow",
        action="append",
        default=[],
        help="replace the installed workflow-pack selection with this exact workflow set; repeatable and requires --manage-workflows",
    )
    parser.add_argument(
        "--spec-kit-mode",
        choices=("off", "auto", "attach", "bootstrap"),
        help="set the Spec Kit bridge mode for install or upgrade flows",
    )
    parser.add_argument(
        "--spec-kit-script",
        choices=("auto", "ps", "sh"),
        default="auto",
        help="override the script flavor used for Spec Kit bridge planning",
    )
    parser.add_argument(
        "--spec-kit-command-surface",
        choices=("auto", "dollar", "slash"),
        default="auto",
        help="override the preferred Spec Kit command surface shown in bridge guidance",
    )
    parser.add_argument(
        "--spec-kit-version",
        help="pin the official Spec Kit version or ref to bootstrap",
    )
    parser.add_argument(
        "--spec-kit-exe",
        help="path to a local `specify`-compatible executable to use instead of uvx for bootstrap",
    )
    parser.add_argument(
        "--utility-harness-mode",
        choices=("off", "install"),
        help="install or disable the optional Codex Utility Harness helper files",
    )
    args = parser.parse_args(argv)

    def emit(text: str, data: dict[str, object] | None = None) -> None:
        print(format_json(data) if args.json and data is not None else text)

    def fail(message: str, extra: dict[str, object] | None = None) -> int:
        payload = {"schema_version": PLAN_JSON_SCHEMA_VERSION, "kind": "error", "message": message}
        if extra:
            payload.update(extra)
        emit(message, payload)
        return 1

    def emit_plan(
        plan: InstallPlan,
        diagnostics: tuple[WriteSafetyDiagnostic, ...] = (),
    ) -> None:
        emit(
            format_plan_report(
                plan,
                write=args.write,
                summary=args.summary,
                include_diff=args.diff,
                diff_full=args.diff_full,
                diagnostics=diagnostics,
            ),
            plan_to_dict(plan, write=args.write, diagnostics=diagnostics),
        )

    def emit_plan_and_apply(plan: InstallPlan) -> int:
        diagnostics = (
            collect_write_safety_diagnostics(
                plan.target,
                allow_dirty=args.allow_dirty,
                allow_source_target=args.allow_source_target,
            )
            if args.write
            else ()
        )
        if args.write and has_blocking_write_safety_diagnostics(diagnostics):
            return fail(
                format_write_safety_block_message(diagnostics),
                {"diagnostics": [_write_safety_to_dict(diagnostic) for diagnostic in diagnostics]},
            )
        emit_plan(plan, diagnostics)
        if args.write:
            try:
                apply_install_plan(
                    plan,
                    allow_dirty=args.allow_dirty,
                    allow_source_target=args.allow_source_target,
                )
            except RuntimeError as error:
                return fail(str(error))
        return 0

    if args.list_packs and args.list_workflows:
        return fail("--list-packs and --list-workflows are separate read-only reports.")

    if args.doctor:
        if (
            args.list_packs
            or args.list_workflows
            or args.inspect_install
            or args.audit_adaptation
            or args.spec_kit_report
            or args.spec_kit_sync_report
            or args.upgrade_enhancer
            or args.manage_packs
            or args.manage_workflows
            or args.manage_spec_kit_bridge
            or args.write
            or args.force
            or args.allow_dirty
            or args.allow_source_target
            or args.refresh_generated
            or args.mode != "auto"
            or args.use_recommended_packs
            or args.pack
            or args.no_pack
            or args.add_pack
            or args.remove_pack
            or args.set_pack
            or args.add_workflow
            or args.remove_workflow
            or args.set_workflow
            or args.spec_kit_mode
            or args.spec_kit_script != "auto"
            or args.spec_kit_command_surface != "auto"
            or args.spec_kit_version
            or args.spec_kit_exe
            or args.spec_kit_feature
            or args.spec_kit_changed_path
            or args.spec_kit_base
            or args.utility_harness_mode
            or args.summary
            or args.diff
            or args.diff_full
        ):
            return fail("--doctor is read-only and can only be combined with --target and --json.")
        try:
            report = build_doctor_report(Path(args.target or "."))
        except ValueError as error:
            return fail(str(error))
        emit(format_doctor_report(report), doctor_to_dict(report))
        return 0

    if args.list_packs and args.target is None:
        catalog = format_pack_catalog()
        catalog_data = pack_catalog_to_dict()
        catalog_data["text"] = catalog
        emit(catalog, catalog_data)
        return 0

    if args.list_workflows and args.target is None:
        catalog = format_workflow_catalog()
        catalog_data = workflow_catalog_to_dict()
        catalog_data["text"] = catalog
        emit(catalog, catalog_data)
        return 0

    if args.target is None:
        return fail(
            "Missing required --target. Use --doctor for a read-only check of the current directory, "
            "--list-packs to inspect available stack packs, or --list-workflows to inspect workflow packs without a target repo."
        )

    target = Path(args.target).resolve()

    if args.list_packs:
        try:
            validate_mode(target, args.mode)
        except ValueError as error:
            return fail(str(error))
        catalog = format_pack_catalog(target)
        catalog_data = pack_catalog_to_dict(target)
        catalog_data["text"] = catalog
        emit(catalog, catalog_data)
        return 0

    if args.list_workflows:
        try:
            validate_mode(target, args.mode)
        except ValueError as error:
            return fail(str(error))
        catalog = format_workflow_catalog(target)
        catalog_data = workflow_catalog_to_dict(target)
        catalog_data["text"] = catalog
        emit(catalog, catalog_data)
        return 0

    if args.spec_kit_report and args.spec_kit_sync_report:
        return fail("--spec-kit-report and --spec-kit-sync-report are separate read-only reports.")

    if args.spec_kit_feature and not (args.spec_kit_report or args.spec_kit_sync_report):
        return fail("--spec-kit-feature requires --spec-kit-report or --spec-kit-sync-report.")

    if (args.spec_kit_changed_path or args.spec_kit_base) and not args.spec_kit_sync_report:
        return fail("--spec-kit-changed-path and --spec-kit-base require --spec-kit-sync-report.")

    if (args.spec_kit_report or args.spec_kit_sync_report) and (
        args.inspect_install
        or args.audit_adaptation
        or args.upgrade_enhancer
        or args.manage_packs
        or args.manage_workflows
        or args.manage_spec_kit_bridge
        or args.write
        or args.force
        or args.allow_dirty
        or args.allow_source_target
        or args.refresh_generated
        or args.use_recommended_packs
        or args.pack
        or args.no_pack
        or args.add_pack
        or args.remove_pack
        or args.set_pack
        or args.add_workflow
        or args.remove_workflow
        or args.set_workflow
        or args.spec_kit_mode
        or args.spec_kit_script != "auto"
        or args.spec_kit_command_surface != "auto"
        or args.spec_kit_version
        or args.spec_kit_exe
        or args.utility_harness_mode
        or args.summary
        or args.diff
        or args.diff_full
    ):
        return fail("Spec Kit reports are read-only and cannot be combined with install, write, bridge, utility, or pack-selection flags.")

    if args.spec_kit_report:
        if not target.exists() or not target.is_dir():
            return fail(f"Target {target} does not exist or is not a directory.")
        report = render_spec_kit_feature_report(target, feature=args.spec_kit_feature)
        emit(report, {"schema_version": PLAN_JSON_SCHEMA_VERSION, "kind": "spec-kit-report", "target": str(target), "feature": args.spec_kit_feature, "text": report})
        return 0

    if args.spec_kit_sync_report:
        if not target.exists() or not target.is_dir():
            return fail(f"Target {target} does not exist or is not a directory.")
        report = render_spec_kit_sync_report(
            target,
            feature=args.spec_kit_feature,
            changed_paths=tuple(args.spec_kit_changed_path),
            git_base=args.spec_kit_base,
        )
        emit(report, {"schema_version": PLAN_JSON_SCHEMA_VERSION, "kind": "spec-kit-sync-report", "target": str(target), "feature": args.spec_kit_feature, "changed_paths": list(args.spec_kit_changed_path), "git_base": args.spec_kit_base, "text": report})
        return 0

    if args.audit_adaptation and (
        args.inspect_install
        or args.upgrade_enhancer
        or args.manage_packs
        or args.manage_workflows
        or args.manage_spec_kit_bridge
        or args.write
        or args.force
        or args.allow_dirty
        or args.allow_source_target
        or args.refresh_generated
        or args.use_recommended_packs
        or args.pack
        or args.no_pack
        or args.add_pack
        or args.remove_pack
        or args.set_pack
        or args.add_workflow
        or args.remove_workflow
        or args.set_workflow
        or args.spec_kit_mode
        or args.spec_kit_script != "auto"
        or args.spec_kit_command_surface != "auto"
        or args.spec_kit_version
        or args.spec_kit_exe
        or args.utility_harness_mode
        or args.summary
        or args.diff
        or args.diff_full
    ):
        return fail("--audit-adaptation only inspects the target repo and cannot be combined with write, refresh, force, bridge, utility, summary, diff, or pack-selection flags.")

    if args.audit_adaptation:
        try:
            audit_text = format_adaptation_audit(target)
            audit_data = adaptation_audit_to_dict(target)
        except ValueError as error:
            return fail(str(error))
        emit(audit_text, audit_data)
        return 0

    if args.inspect_install and (
        args.upgrade_enhancer
        or args.manage_packs
        or args.manage_workflows
        or args.manage_spec_kit_bridge
        or args.write
        or args.force
        or args.allow_dirty
        or args.allow_source_target
        or args.refresh_generated
        or args.use_recommended_packs
        or args.pack
        or args.no_pack
        or args.add_pack
        or args.remove_pack
        or args.set_pack
        or args.add_workflow
        or args.remove_workflow
        or args.set_workflow
        or args.spec_kit_mode
        or args.spec_kit_script != "auto"
        or args.spec_kit_command_surface != "auto"
        or args.spec_kit_version
        or args.spec_kit_exe
        or args.spec_kit_report
        or args.spec_kit_sync_report
        or args.spec_kit_feature
        or args.spec_kit_changed_path
        or args.spec_kit_base
        or args.utility_harness_mode
        or args.summary
        or args.diff
        or args.diff_full
    ):
        return fail("--inspect-install only inspects the target repo and cannot be combined with write, refresh, force, summary, diff, or pack-selection flags.")

    if args.inspect_install:
        try:
            inspection = inspect_install(target)
        except ValueError as error:
            return fail(str(error))
        emit(format_install_inspection(inspection), inspection_to_dict(inspection))
        return 0

    if args.upgrade_enhancer and (
        args.force
        or args.manage_packs
        or args.manage_workflows
        or args.manage_spec_kit_bridge
        or args.refresh_generated
        or args.use_recommended_packs
        or args.pack
        or args.no_pack
        or args.add_pack
        or args.remove_pack
        or args.set_pack
        or args.add_workflow
        or args.remove_workflow
        or args.set_workflow
    ):
        return fail("--upgrade-enhancer keeps the installed pack and workflow selection and cannot be combined with refresh, force, or selection flags.")

    if args.upgrade_enhancer:
        if args.mode == "new":
            return fail("--upgrade-enhancer only works with --mode existing or --mode auto.")
        try:
            plan = build_upgrade_plan(
                target,
                spec_kit_mode=args.spec_kit_mode,
                spec_kit_script=args.spec_kit_script,
                spec_kit_command_surface=args.spec_kit_command_surface,
                spec_kit_version=args.spec_kit_version,
                spec_kit_executable=args.spec_kit_exe,
                utility_harness_mode=args.utility_harness_mode,
            )
        except ValueError as error:
            return fail(str(error))
        return emit_plan_and_apply(plan)

    if args.manage_spec_kit_bridge and (
        args.force
        or args.manage_packs
        or args.manage_workflows
        or args.refresh_generated
        or args.use_recommended_packs
        or args.pack
        or args.no_pack
        or args.add_pack
        or args.remove_pack
        or args.set_pack
        or args.add_workflow
        or args.remove_workflow
        or args.set_workflow
        or args.utility_harness_mode
    ):
        return fail("--manage-spec-kit-bridge updates bridge state and cannot be combined with force, refresh, Utility Harness, or selection flags.")

    if args.manage_spec_kit_bridge:
        if args.mode == "new":
            return fail("--manage-spec-kit-bridge only works with --mode existing or --mode auto.")
        try:
            plan = build_spec_kit_bridge_management_plan(
                target,
                spec_kit_mode=args.spec_kit_mode,
                spec_kit_script=args.spec_kit_script,
                spec_kit_command_surface=args.spec_kit_command_surface,
                spec_kit_version=args.spec_kit_version,
                spec_kit_executable=args.spec_kit_exe,
                require_changes=True,
            )
        except ValueError as error:
            return fail(str(error))
        return emit_plan_and_apply(plan)

    if (args.add_pack or args.remove_pack or args.set_pack) and not args.manage_packs:
        return fail("--add-pack, --remove-pack, and --set-pack require --manage-packs.")

    if (args.add_workflow or args.remove_workflow or args.set_workflow) and not args.manage_workflows:
        return fail("--add-workflow, --remove-workflow, and --set-workflow require --manage-workflows.")

    if args.manage_packs and (
        args.force
        or args.manage_workflows
        or args.manage_spec_kit_bridge
        or args.refresh_generated
        or args.use_recommended_packs
        or args.pack
        or args.no_pack
        or args.spec_kit_mode
        or args.spec_kit_script != "auto"
        or args.spec_kit_command_surface != "auto"
        or args.spec_kit_version
        or args.spec_kit_exe
        or args.utility_harness_mode
        or args.add_workflow
        or args.remove_workflow
        or args.set_workflow
    ):
        return fail("--manage-packs updates installed pack selection and cannot be combined with workflow, Spec Kit, Utility Harness, or install-time pack-selection flags.")

    if args.manage_packs:
        if args.mode == "new":
            return fail("--manage-packs only works with --mode existing or --mode auto.")
        try:
            plan = build_pack_management_plan(
                target,
                add_packs=tuple(args.add_pack),
                remove_packs=tuple(args.remove_pack),
                set_packs=tuple(args.set_pack) if args.set_pack else None,
                require_changes=True,
            )
        except ValueError as error:
            return fail(str(error))
        return emit_plan_and_apply(plan)

    if args.manage_workflows and (
        args.force
        or args.manage_spec_kit_bridge
        or args.refresh_generated
        or args.use_recommended_packs
        or args.pack
        or args.no_pack
        or args.add_pack
        or args.remove_pack
        or args.set_pack
        or args.spec_kit_mode
        or args.spec_kit_script != "auto"
        or args.spec_kit_command_surface != "auto"
        or args.spec_kit_version
        or args.spec_kit_exe
        or args.utility_harness_mode
    ):
        return fail("--manage-workflows updates installed workflow selection and cannot be combined with pack, Spec Kit, Utility Harness, or install-time selection flags.")

    if args.manage_workflows:
        if args.mode == "new":
            return fail("--manage-workflows only works with --mode existing or --mode auto.")
        try:
            plan = build_workflow_management_plan(
                target,
                add_workflows=tuple(args.add_workflow),
                remove_workflows=tuple(args.remove_workflow),
                set_workflows=tuple(args.set_workflow) if args.set_workflow else None,
                require_changes=True,
            )
        except ValueError as error:
            return fail(str(error))
        return emit_plan_and_apply(plan)

    if args.refresh_generated and args.force:
        return fail("--refresh-generated only updates safe managed outputs and does not accept --force.")

    if args.refresh_generated and args.mode == "new":
        return fail("--refresh-generated only works with --mode existing or --mode auto.")

    if args.refresh_generated and (
        args.use_recommended_packs
        or args.manage_spec_kit_bridge
        or args.manage_workflows
        or args.pack
        or args.no_pack
        or args.add_pack
        or args.remove_pack
        or args.set_pack
        or args.add_workflow
        or args.remove_workflow
        or args.set_workflow
        or args.spec_kit_mode
        or args.spec_kit_script != "auto"
        or args.spec_kit_command_surface != "auto"
        or args.spec_kit_version
        or args.spec_kit_exe
        or args.utility_harness_mode
    ):
        return fail(
            "--refresh-generated uses the target repo's existing manifest selection and bridge state; "
            "do not combine it with pack-selection, Spec Kit override, or Utility Harness flags. "
            "Use --manage-workflows for workflow-selection changes."
        )

    try:
        plan = build_install_plan(
            target,
            mode=args.mode,
            force=args.force,
            refresh_generated=args.refresh_generated,
            use_recommended_packs=args.use_recommended_packs,
            include_packs=tuple(args.pack),
            exclude_packs=tuple(args.no_pack),
            spec_kit_mode=args.spec_kit_mode,
            spec_kit_script=args.spec_kit_script,
            spec_kit_command_surface=args.spec_kit_command_surface,
            spec_kit_version=args.spec_kit_version,
            spec_kit_executable=args.spec_kit_exe,
            utility_harness_mode=args.utility_harness_mode,
        )
    except ValueError as error:
        return fail(str(error))

    return emit_plan_and_apply(plan)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
