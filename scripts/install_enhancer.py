#!/usr/bin/env python3
"""Install the Codex Enhancer scaffold into a new or existing repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.enhancer_spec import (
    CHECK_COMMAND,
    GITIGNORE_LINES,
    INSTALL_COPY_ASSETS,
    INSTALL_TEMPLATE_ASSETS,
    TEST_COMMAND,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ROOT = Path(".codex/enhancer-proposals")

COMMON_GUIDANCE_PATHS = (
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
    Path(".cursorrules"),
    Path(".cursor/rules"),
    Path(".github/copilot-instructions.md"),
)


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
class InstallPlan:
    target: Path
    mode: str
    force: bool
    writes: tuple[PlannedWrite, ...]
    gitignore: GitignorePlan


ProgressCallback = Callable[[int, int, str], None]


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
        scripts = package_data.get("scripts", {})
        if package_data:
            maybe_set_command(commands, "install", "npm install")
        for name in ("build", "lint", "dev", "check"):
            if name in scripts:
                maybe_set_command(commands, name, f"npm run {name}")
        if "test" in scripts:
            maybe_set_command(commands, "test", "npm test")

    pyproject = target / "pyproject.toml"
    if pyproject.exists():
        try:
            pyproject_data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            pyproject_data = {}

        if "project" in pyproject_data or "build-system" in pyproject_data:
            maybe_set_command(commands, "install", "pip install -e .")

        tool = pyproject_data.get("tool", {})
        if "pytest" in tool or "pytest.ini_options" in tool.get("pytest", {}) or (target / "tests").exists():
            maybe_set_command(commands, "test", "python -m pytest")
        if "ruff" in tool:
            maybe_set_command(commands, "lint", "ruff check .")

    requirements = target / "requirements.txt"
    if requirements.exists():
        maybe_set_command(commands, "install", "pip install -r requirements.txt")

    return commands


def discover_existing_guidance(target: Path) -> list[str]:
    found: list[str] = []
    for relative_path in COMMON_GUIDANCE_PATHS:
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


def build_replacements(target: Path) -> dict[str, str]:
    commands = discover_commands(target)
    repo_name = target.name or "Repository"
    return {
        "REPO_NAME": repo_name,
        "DISCOVERED_COMMANDS": render_discovered_commands(commands),
        "EXISTING_GUIDANCE": render_existing_guidance(discover_existing_guidance(target)),
    }


def plan_template_writes(target: Path, force: bool) -> list[PlannedWrite]:
    replacements = build_replacements(target)
    writes: list[PlannedWrite] = []

    for asset in INSTALL_TEMPLATE_ASSETS:
        template_path = SOURCE_ROOT / asset.template_path
        content = render_template(template_path.read_text(encoding="utf-8"), replacements)
        destination = target / asset.destination
        action = "create"
        write_path = asset.destination
        if destination.exists():
            if force:
                action = "overwrite"
            else:
                action = "proposal"
                write_path = proposal_destination(asset.destination)
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


def plan_copy_writes(target: Path, force: bool) -> list[PlannedWrite]:
    writes: list[PlannedWrite] = []

    for asset in INSTALL_COPY_ASSETS:
        source_path = SOURCE_ROOT / asset.source_path
        content = source_path.read_text(encoding="utf-8")
        destination = target / asset.destination
        action = "create"
        write_path = asset.destination
        if destination.exists():
            if force:
                action = "overwrite"
            else:
                action = "proposal"
                write_path = proposal_destination(asset.destination)
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


def build_install_plan(target: Path, mode: str = "auto", force: bool = False) -> InstallPlan:
    resolved_target = target.resolve()
    validate_mode(resolved_target, mode)
    effective_mode = infer_mode(resolved_target) if mode == "auto" else mode
    writes = tuple(plan_template_writes(resolved_target, force=force) + plan_copy_writes(resolved_target, force=force))
    gitignore = compute_gitignore_update(resolved_target)
    return InstallPlan(
        target=resolved_target,
        mode=effective_mode,
        force=force,
        writes=writes,
        gitignore=gitignore,
    )


def format_plan_header(plan: InstallPlan, write: bool) -> str:
    return (
        f"{'Applying' if write else 'Planned'} Codex Enhancer install into {plan.target} "
        f"(mode={plan.mode}, force={plan.force})"
    )


def format_plan_lines(plan: InstallPlan) -> list[str]:
    lines: list[str] = []
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
    if plan.gitignore.missing_lines:
        lines.append(
            f"- merge: {plan.gitignore.destination.as_posix()} add {', '.join(plan.gitignore.missing_lines)}"
        )
    else:
        lines.append(
            f"- merge: {plan.gitignore.destination.as_posix()} already contains required entries"
        )
    return lines


def format_plan_report(plan: InstallPlan, write: bool) -> str:
    lines = [format_plan_header(plan, write), *format_plan_lines(plan), "", *format_next_steps(plan, write)]
    return "\n".join(lines)


def format_next_steps(plan: InstallPlan, write: bool) -> list[str]:
    proposals = [item for item in plan.writes if item.action == "proposal"]
    if not write:
        return [
            "Next step:",
            "- Re-run this command with --write when the preview looks correct.",
        ]

    lines = ["Next steps:"]
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
    lines.append(f"- Run `{CHECK_COMMAND}` in the target repo.")
    lines.append(f"- Run `{TEST_COMMAND}` in the target repo.")
    return lines


def overwrite_paths(plan: InstallPlan) -> tuple[Path, ...]:
    return tuple(item.destination for item in plan.writes if item.action == "overwrite")


def proposal_paths(plan: InstallPlan) -> tuple[Path, ...]:
    return tuple(item.write_path for item in plan.writes if item.action == "proposal")


def apply_install_plan(plan: InstallPlan, progress_callback: ProgressCallback | None = None) -> None:
    total_steps = len(plan.writes) + 1
    current_step = 0

    if progress_callback:
        progress_callback(current_step, total_steps, "Preparing install...")

    plan.target.mkdir(parents=True, exist_ok=True)
    for planned_write in plan.writes:
        write_text_file(plan.target / planned_write.write_path, planned_write.content)
        current_step += 1
        if progress_callback:
            progress_callback(
                current_step,
                total_steps,
                f"{planned_write.action.title()} {planned_write.write_path.as_posix()}",
            )

    apply_gitignore_update(plan.target / plan.gitignore.destination, plan.gitignore.missing_lines)
    current_step += 1
    if progress_callback:
        message = (
            f"Merged {plan.gitignore.destination.as_posix()}"
            if plan.gitignore.missing_lines
            else f"Checked {plan.gitignore.destination.as_posix()}"
        )
        progress_callback(current_step, total_steps, message)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        required=True,
        help="path to the new or existing repository that should receive the enhancer scaffold",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "new", "existing"),
        default="auto",
        help="treat the target as a new repo, an existing repo, or infer automatically",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="apply the install instead of only printing a dry-run plan",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite colliding files instead of writing proposals under .codex/enhancer-proposals/",
    )
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()

    try:
        plan = build_install_plan(target, mode=args.mode, force=args.force)
    except ValueError as error:
        print(str(error))
        return 1

    print(format_plan_report(plan, write=args.write))

    if args.write:
        apply_install_plan(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
