#!/usr/bin/env python3
"""Detect, resolve, and summarize optional official GitHub Spec Kit installs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


CORE_COMMAND_ORDER = (
    "constitution",
    "specify",
    "clarify",
    "plan",
    "analyze",
    "tasks",
    "implement",
    "checklist",
    "taskstoissues",
)
PROMPT_SUFFIX = ".prompt.md"
AGENT_SUFFIX = ".agent.md"
SPEC_KIT_BRIDGE_MODES = ("off", "auto", "attach", "bootstrap")
SPEC_KIT_SCRIPT_OPTIONS = ("auto", "ps", "sh")
SPEC_KIT_COMMAND_SURFACE_OPTIONS = ("auto", "dollar", "slash")
SPEC_KIT_BRIDGE_SKILLS = (
    "spec-implement-bridge",
    "spec-sync-check",
    "spec-review-bridge",
)
DEFAULT_BOOTSTRAP_COMMANDS = CORE_COMMAND_ORDER[:7]
DEFAULT_SPEC_KIT_VERSION = "main"


def default_spec_kit_script_type() -> str:
    return "ps" if os.name == "nt" else "sh"


@dataclass(frozen=True)
class SpecKitPaths:
    specify_root: str | None = None
    specs_root: str | None = None
    prompts_root: str | None = None
    agents_root: str | None = None
    codex_skills_root: str | None = None
    context_file: str | None = None
    constitution: str | None = None


@dataclass(frozen=True)
class SpecKitDetection:
    detected: bool
    integration: str | None
    command_surface: str | None
    command_label: str | None
    script_type: str | None
    version: str | None
    commands: tuple[str, ...]
    evidence: tuple[str, ...]
    paths: SpecKitPaths
    has_git_extension: bool = False


@dataclass(frozen=True)
class SpecKitBridgeConfig:
    mode: str
    state: str
    origin: str | None
    integration_key: str | None
    managed_by: str
    script_type: str | None
    command_surface: str | None
    command_label: str | None
    cli_version: str | None
    available_commands: tuple[str, ...]
    evidence: tuple[str, ...]
    paths: SpecKitPaths
    bootstrap_command: tuple[str, ...] = ()

    @property
    def enabled(self) -> bool:
        return self.state in {"attached", "bootstrapped"}


def _read_json_object(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _string_value(data: dict[str, object] | None, key: str) -> str | None:
    if not data:
        return None
    value = data.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _relative_if_exists(root: Path, relative_path: str) -> str | None:
    return relative_path if (root / relative_path).exists() else None


def _collect_prompt_or_agent_commands(directory: Path, suffix: str) -> tuple[str, ...]:
    if not directory.is_dir():
        return ()
    commands: list[str] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        name = path.name
        if not name.startswith("speckit.") or not name.endswith(suffix):
            continue
        commands.append(name[len("speckit.") : -len(suffix)])
    return tuple(commands)


def _collect_codex_skill_commands(directory: Path) -> tuple[str, ...]:
    if not directory.is_dir():
        return ()
    commands: list[str] = []
    for path in sorted(directory.iterdir()):
        if not path.is_dir():
            continue
        name = path.name
        if not name.startswith("speckit-"):
            continue
        commands.append(name[len("speckit-") :].replace("-", "."))
    return tuple(commands)


def _ordered_commands(commands: tuple[str, ...]) -> tuple[str, ...]:
    unique = tuple(dict.fromkeys(command for command in commands if command))
    if not unique:
        return ()
    extras = sorted(command for command in unique if command not in CORE_COMMAND_ORDER)
    core = tuple(command for command in CORE_COMMAND_ORDER if command in unique)
    return core + tuple(command for command in extras if command not in core)


def _resolve_command_surface(
    *,
    integration: str | None,
    has_prompt_or_agent_surface: bool,
    has_codex_skill_surface: bool,
) -> tuple[str | None, str | None]:
    if has_prompt_or_agent_surface and has_codex_skill_surface:
        return ("mixed", "multiple official Spec Kit surfaces detected")
    if has_codex_skill_surface:
        return ("codex-skills", "$speckit-<command>")
    if has_prompt_or_agent_surface:
        return ("github-prompts-agents", ".github/prompts and .github/agents")
    if integration == "codex":
        return ("codex-skills", "$speckit-<command>")
    if integration == "copilot":
        return ("github-prompts-agents", ".github/prompts and .github/agents")
    if integration:
        return (integration, f"official {integration} integration")
    return (None, None)


def _bridge_surface_from_detection(detection: SpecKitDetection) -> tuple[str | None, str | None]:
    if detection.command_surface == "codex-skills":
        return ("dollar", "$speckit-<command>")
    if detection.command_surface == "github-prompts-agents":
        return ("slash", "/prompts:speckit.<command>")
    if detection.command_surface == "mixed":
        return ("mixed", "multiple official Spec Kit surfaces detected")
    return (None, None)


def _bridge_surface_from_preference(
    preference: str,
    detection: SpecKitDetection,
) -> tuple[str | None, str | None]:
    if preference == "dollar":
        return ("dollar", "$speckit-<command>")
    if preference == "slash":
        return ("slash", "/prompts:speckit.<command>")
    resolved_surface, resolved_label = _bridge_surface_from_detection(detection)
    if resolved_surface or resolved_label:
        return (resolved_surface, resolved_label)
    return ("dollar", "$speckit-<command>")


def build_spec_kit_bootstrap_command(
    *,
    script_type: str,
    version: str,
    executable: str | None = None,
) -> tuple[str, ...]:
    if executable:
        return (
            executable,
            "init",
            "--here",
            "--integration",
            "codex",
            "--script",
            script_type,
        )
    return (
        "uvx",
        "--from",
        f"git+https://github.com/github/spec-kit.git@{version}",
        "specify",
        "init",
        "--here",
        "--integration",
        "codex",
        "--script",
        script_type,
    )


def detect_spec_kit(target: Path) -> SpecKitDetection:
    root = target.resolve()
    integration_data = _read_json_object(root / ".specify/integration.json")
    init_options = _read_json_object(root / ".specify/init-options.json")

    prompt_commands = _collect_prompt_or_agent_commands(root / ".github/prompts", PROMPT_SUFFIX)
    agent_commands = _collect_prompt_or_agent_commands(root / ".github/agents", AGENT_SUFFIX)
    codex_skill_commands = _collect_codex_skill_commands(root / ".agents/skills")

    integration = (
        _string_value(init_options, "integration")
        or _string_value(init_options, "ai")
        or _string_value(integration_data, "integration")
    )
    version = _string_value(init_options, "speckit_version") or _string_value(
        integration_data, "version"
    )
    script_type = _string_value(init_options, "script")
    has_prompt_or_agent_surface = bool(prompt_commands or agent_commands)
    has_codex_skill_surface = bool(codex_skill_commands)
    command_surface, command_label = _resolve_command_surface(
        integration=integration,
        has_prompt_or_agent_surface=has_prompt_or_agent_surface,
        has_codex_skill_surface=has_codex_skill_surface,
    )

    paths = SpecKitPaths(
        specify_root=_relative_if_exists(root, ".specify"),
        specs_root=_relative_if_exists(root, "specs"),
        prompts_root=(
            ".github/prompts" if has_prompt_or_agent_surface and (root / ".github/prompts").is_dir() else None
        ),
        agents_root=(
            ".github/agents" if has_prompt_or_agent_surface and (root / ".github/agents").is_dir() else None
        ),
        codex_skills_root=".agents/skills" if has_codex_skill_surface else None,
        context_file=_string_value(init_options, "context_file"),
        constitution=_relative_if_exists(root, ".specify/memory/constitution.md"),
    )

    detected = any(
        (
            paths.specify_root,
            paths.specs_root,
            paths.prompts_root,
            paths.agents_root,
            paths.codex_skills_root,
        )
    )
    commands = _ordered_commands(prompt_commands + agent_commands + codex_skill_commands)
    has_git_extension = (root / ".specify/extensions/git").is_dir()

    evidence: list[str] = []
    if paths.specify_root:
        evidence.append("found .specify/")
    if paths.specs_root:
        evidence.append("found specs/")
    if paths.prompts_root:
        evidence.append("found Spec Kit prompt files under .github/prompts/")
    if paths.agents_root:
        evidence.append("found Spec Kit agent files under .github/agents/")
    if paths.codex_skills_root:
        evidence.append("found Spec Kit skills under .agents/skills/")
    if integration:
        evidence.append(f"integration: {integration}")
    if script_type:
        evidence.append(f"script type: {script_type}")
    if version:
        evidence.append(f"Spec Kit version: {version}")
    if has_git_extension:
        evidence.append("git extension hooks configured")

    return SpecKitDetection(
        detected=detected,
        integration=integration,
        command_surface=command_surface,
        command_label=command_label,
        script_type=script_type,
        version=version,
        commands=commands,
        evidence=tuple(evidence),
        paths=paths,
        has_git_extension=has_git_extension,
    )


def resolve_spec_kit_bridge(
    target: Path,
    *,
    mode: str = "auto",
    script_type: str = "auto",
    command_surface: str = "auto",
    version: str | None = None,
    executable: str | None = None,
    detection: SpecKitDetection | None = None,
    existing_bridge: SpecKitBridgeConfig | None = None,
) -> SpecKitBridgeConfig:
    if mode not in SPEC_KIT_BRIDGE_MODES:
        choices = ", ".join(SPEC_KIT_BRIDGE_MODES)
        raise ValueError(f"Unknown Spec Kit bridge mode {mode!r}. Expected one of: {choices}.")
    if script_type not in SPEC_KIT_SCRIPT_OPTIONS:
        choices = ", ".join(SPEC_KIT_SCRIPT_OPTIONS)
        raise ValueError(
            f"Unknown Spec Kit script type {script_type!r}. Expected one of: {choices}."
        )
    if command_surface not in SPEC_KIT_COMMAND_SURFACE_OPTIONS:
        choices = ", ".join(SPEC_KIT_COMMAND_SURFACE_OPTIONS)
        raise ValueError(
            f"Unknown Spec Kit command surface {command_surface!r}. Expected one of: {choices}."
        )

    detection = detection or detect_spec_kit(target)
    resolved_mode = "attach" if mode == "auto" and detection.detected else "off" if mode == "auto" else mode

    if resolved_mode == "off":
        detected_surface, detected_label = _bridge_surface_from_detection(detection)
        return SpecKitBridgeConfig(
            mode="off",
            state="absent",
            origin=None,
            integration_key=detection.integration,
            managed_by="spec-kit",
            script_type=detection.script_type,
            command_surface=detected_surface,
            command_label=detected_label,
            cli_version=detection.version,
            available_commands=detection.commands,
            evidence=detection.evidence,
            paths=detection.paths,
        )

    if resolved_mode == "attach":
        if not detection.detected:
            raise ValueError(
                "Spec Kit bridge mode 'attach' requires an existing official Spec Kit install in the target repo."
            )
        resolved_script = (
            default_spec_kit_script_type()
            if script_type == "auto" and detection.script_type is None
            else detection.script_type
            if script_type == "auto"
            else script_type
        )
        resolved_surface, resolved_label = _bridge_surface_from_preference(command_surface, detection)
        return SpecKitBridgeConfig(
            mode="attach",
            state="attached",
            origin="preexisting",
            integration_key=detection.integration or "codex",
            managed_by="spec-kit",
            script_type=resolved_script,
            command_surface=resolved_surface,
            command_label=resolved_label,
            cli_version=detection.version or version,
            available_commands=detection.commands or DEFAULT_BOOTSTRAP_COMMANDS,
            evidence=detection.evidence,
            paths=detection.paths,
        )

    if (
        detection.detected
        and existing_bridge is not None
        and existing_bridge.state == "bootstrapped"
        and existing_bridge.mode == "bootstrap"
    ):
        resolved_script = (
            default_spec_kit_script_type()
            if script_type == "auto" and detection.script_type is None
            else detection.script_type
            if script_type == "auto"
            else script_type
        )
        resolved_surface, resolved_label = _bridge_surface_from_preference(command_surface, detection)
        return SpecKitBridgeConfig(
            mode="bootstrap",
            state="bootstrapped",
            origin="enhancer-bootstrap",
            integration_key=detection.integration or "codex",
            managed_by="spec-kit",
            script_type=resolved_script,
            command_surface=resolved_surface,
            command_label=resolved_label,
            cli_version=detection.version or version or existing_bridge.cli_version,
            available_commands=detection.commands or DEFAULT_BOOTSTRAP_COMMANDS,
            evidence=detection.evidence,
            paths=detection.paths,
        )

    if detection.detected:
        raise ValueError(
            "Spec Kit bridge mode 'bootstrap' cannot run because official Spec Kit is already detected in the target repo. "
            "Use 'attach' or 'off' instead."
        )

    resolved_script = default_spec_kit_script_type() if script_type == "auto" else script_type
    resolved_surface, resolved_label = _bridge_surface_from_preference(
        "dollar" if command_surface == "auto" else command_surface,
        detection,
    )
    resolved_version = version or DEFAULT_SPEC_KIT_VERSION
    bootstrap_command = build_spec_kit_bootstrap_command(
        script_type=resolved_script,
        version=resolved_version,
        executable=executable,
    )
    return SpecKitBridgeConfig(
        mode="bootstrap",
        state="bootstrapped",
        origin="enhancer-bootstrap",
        integration_key="codex",
        managed_by="spec-kit",
        script_type=resolved_script,
        command_surface=resolved_surface,
        command_label=resolved_label,
        cli_version=resolved_version,
        available_commands=DEFAULT_BOOTSTRAP_COMMANDS,
        evidence=(
            "installer will bootstrap official Spec Kit for Codex",
            f"script type: {resolved_script}",
            f"requested Spec Kit version: {resolved_version}",
        ),
        paths=SpecKitPaths(
            specify_root=".specify",
            specs_root="specs",
            codex_skills_root=".agents/skills",
            constitution=".specify/memory/constitution.md",
        ),
        bootstrap_command=bootstrap_command,
    )


def render_spec_kit_detection_lines(detection: SpecKitDetection) -> list[str]:
    if not detection.detected:
        return ["- Official Spec Kit not detected."]

    lines = ["- Official Spec Kit detected."]
    if detection.integration:
        lines.append(f"- Integration: `{detection.integration}`")
    if detection.version:
        lines.append(f"- Spec Kit version: `{detection.version}`")
    if detection.script_type:
        lines.append(f"- Script type: `{detection.script_type}`")
    if detection.command_label:
        lines.append(f"- Likely command surface: {detection.command_label}.")
    if detection.commands:
        rendered = ", ".join(f"`{command}`" for command in detection.commands)
        lines.append(f"- Available commands: {rendered}")
    if detection.evidence:
        lines.append("- Evidence: " + "; ".join(detection.evidence))
    return lines


def format_spec_kit_bridge_mode_label(bridge: SpecKitBridgeConfig) -> str:
    if bridge.mode == "bootstrap":
        return "managed bootstrap"
    if bridge.mode == "attach":
        return "attached to an existing official install"
    return "off"


def render_spec_kit_bridge_summary(
    bridge: SpecKitBridgeConfig | SpecKitDetection,
    detection: SpecKitDetection | None = None,
) -> str:
    if isinstance(bridge, SpecKitDetection):
        detection = bridge
        bridge = resolve_spec_kit_bridge(Path("."), detection=detection)

    detection = detection or SpecKitDetection(
        detected=False,
        integration=None,
        command_surface=None,
        command_label=None,
        script_type=None,
        version=None,
        commands=(),
        evidence=(),
        paths=SpecKitPaths(),
    )
    if not bridge.enabled:
        lines = ["- Spec Kit bridge is off for this enhancer install."]
        if detection.detected:
            lines.append(
                "- Official Spec Kit was detected, but the enhancer bridge was left off intentionally."
            )
        else:
            lines.append(
                "- Official Spec Kit is not installed here yet. Re-run the installer with bridge attach or bootstrap if this repo adopts Spec Kit later."
            )
        lines.append(
            "- If `.specify/`, `specs/`, `.github/prompts/`, `.github/agents/`, or `.agents/skills/speckit-*` exist, review [docs/ai/spec-kit-bridge.md](docs/ai/spec-kit-bridge.md) before changing workflow guidance."
        )
        return "\n".join(lines)

    lines = [f"- Spec Kit bridge is {format_spec_kit_bridge_mode_label(bridge)}."]
    if bridge.integration_key:
        lines.append(f"- Official integration: `{bridge.integration_key}`.")
    if bridge.command_label:
        lines.append(f"- Default command surface: {bridge.command_label}.")
    if bridge.available_commands:
        commands = ", ".join(f"`{command}`" for command in bridge.available_commands)
        lines.append(f"- Bridge-aware commands: {commands}.")
    lines.append(
        "- Read feature artifacts in `specs/` before implementation or review, and keep enhancer validation or review notes aligned with the current spec, plan, tasks, contracts, and quickstart."
    )
    lines.append(
        "- Treat `.specify/`, `specs/`, and official Spec Kit prompt, agent, or skill files as separately owned."
    )
    return "\n".join(lines)


def render_spec_kit_bridge_doc_status(
    bridge: SpecKitBridgeConfig,
    detection: SpecKitDetection | None = None,
) -> str:
    detection = detection or SpecKitDetection(
        detected=False,
        integration=None,
        command_surface=None,
        command_label=None,
        script_type=None,
        version=None,
        commands=(),
        evidence=(),
        paths=SpecKitPaths(),
    )
    lines = [f"- Bridge mode: `{bridge.mode}`."]
    lines.append(f"- Bridge state: `{bridge.state}`.")
    if bridge.origin:
        lines.append(f"- Bridge origin: `{bridge.origin}`.")
    if bridge.integration_key:
        lines.append(f"- Official integration: `{bridge.integration_key}`.")
    if bridge.script_type:
        lines.append(f"- Script type: `{bridge.script_type}`.")
    if bridge.cli_version:
        lines.append(f"- Spec Kit version: `{bridge.cli_version}`.")
    if bridge.command_label:
        lines.append(f"- Default command surface: {bridge.command_label}.")
    if detection.detected:
        lines.append("- Official Spec Kit files were detected in this repo.")
    else:
        lines.append("- Official Spec Kit files are not currently detected in this repo.")
    return "\n".join(lines)


def render_spec_kit_bridge_doc_command_surface(bridge: SpecKitBridgeConfig) -> str:
    if not bridge.enabled:
        return (
            "- No bridge-specific command surface is active.\n"
            "- If the repo later adopts official Spec Kit, prefer the official command surface that install created and then re-run the enhancer install or upgrade flow."
        )

    lines = []
    if bridge.command_label:
        lines.append(f"- Use {bridge.command_label} for official Spec Kit workflow steps.")
    if bridge.available_commands:
        commands = ", ".join(f"`{command}`" for command in bridge.available_commands)
        lines.append(f"- Expected commands in this repo: {commands}.")
    lines.append(
        "- Use enhancer skills after Spec Kit has already produced artifacts; do not use the enhancer to replace official Spec Kit planning commands."
    )
    return "\n".join(lines)


def render_spec_kit_bridge_doc_workflow(bridge: SpecKitBridgeConfig) -> str:
    if not bridge.enabled:
        return (
            "1. Use the normal enhancer loop: inspect -> plan -> edit -> validate -> review.\n"
            "2. If official Spec Kit appears later, read this file again and decide whether the bridge should be attached or bootstrapped."
        )

    return (
        "1. Start feature work with official Spec Kit: constitution -> specify -> clarify -> plan -> analyze -> tasks -> implement.\n"
        "2. Before editing code, read the active `spec.md`, `plan.md`, `tasks.md`, and any `contracts/`, `quickstart.md`, `research.md`, or `data-model.md` files for that feature.\n"
        "3. Implement the smallest coherent slice, then compare the code back against the feature artifacts.\n"
        "4. Use the bridge skills below for implementation alignment, drift checks, and review prep."
    )


def render_spec_kit_bridge_doc_skills(bridge: SpecKitBridgeConfig) -> str:
    if not bridge.enabled:
        return (
            "- Bridge skills are not installed while the bridge is off.\n"
            "- Turn the bridge on before adding workflow that assumes `specs/` artifacts exist."
        )

    return "\n".join(
        [
            "- `spec-implement-bridge`: use when a feature already has `plan.md` and `tasks.md` and you want repo-aware implementation work.",
            "- `spec-sync-check`: use when code changed and you need to compare it against `spec.md`, tasks, contracts, quickstart notes, or other feature artifacts.",
            "- `spec-review-bridge`: use when preparing a PR or review summary for a Spec Kit-driven branch.",
        ]
    )
