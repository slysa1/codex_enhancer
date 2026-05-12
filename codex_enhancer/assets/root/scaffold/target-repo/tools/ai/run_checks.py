#!/usr/bin/env python3
"""Run validation commands that are already recorded in this repo."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shlex
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


VALIDATION_NAMES = ("check", "lint", "typecheck", "test", "build")
PACKAGE_MANAGER_LOCKFILES = (
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("bun.lockb", "bun"),
    ("bun.lock", "bun"),
    ("package-lock.json", "npm"),
    ("npm-shrinkwrap.json", "npm"),
)


@dataclass(frozen=True)
class Command:
    label: str
    command: str
    source: str
    trust: str


SHELL_TOKENS = ("&&", "||", ";", "|", ">", "<", "&")


def package_manager(root: Path) -> str:
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            raw = data.get("packageManager")
            if isinstance(raw, str):
                name = raw.split("@", 1)[0].strip()
                if name in {"npm", "pnpm", "yarn", "bun"}:
                    return name
    for lockfile, manager in PACKAGE_MANAGER_LOCKFILES:
        if (root / lockfile).exists():
            return manager
    return "npm"


def package_script_command(manager: str, script_name: str) -> str:
    if manager == "bun":
        return f"bun run {script_name}"
    if script_name == "test":
        return f"{manager} test"
    return f"{manager} run {script_name}"


def commands_from_package_json(root: Path) -> list[Command]:
    path = root / "package.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
    if not isinstance(scripts, dict):
        return []
    manager = package_manager(root)
    commands: list[Command] = []
    for name in VALIDATION_NAMES:
        if name in scripts:
            commands.append(
                Command(
                    label=f"package:{name}",
                    command=package_script_command(manager, name),
                    source="package.json scripts",
                    trust="confirmed",
                )
            )
    return commands


def parse_assignment_string(path: Path, name: str) -> str | None:
    if not path.exists():
        return None
    try:
        module = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    return None


def commands_from_enhancer_spec(root: Path) -> list[Command]:
    spec = root / "scripts/enhancer_spec.py"
    commands: list[Command] = []
    for label, constant in (("enhancer:check", "CHECK_COMMAND"), ("enhancer:test", "TEST_COMMAND")):
        command = parse_assignment_string(spec, constant)
        if command:
            commands.append(
                Command(
                    label=label,
                    command=command,
                    source="scripts/enhancer_spec.py",
                    trust="confirmed",
                )
            )
    return commands


def parse_make_like_targets(path: Path) -> set[str]:
    if not path.exists():
        return set()
    targets: set[str] = set()
    target_re = re.compile(r"^([A-Za-z0-9_.-]+):")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = target_re.match(line)
        if match and not match.group(1).startswith("."):
            targets.add(match.group(1))
    return targets


def commands_from_makefiles(root: Path) -> list[Command]:
    commands: list[Command] = []
    for file_name, runner in (("Makefile", "make"), ("justfile", "just")):
        targets = parse_make_like_targets(root / file_name)
        for name in VALIDATION_NAMES:
            if name in targets:
                commands.append(
                    Command(
                        label=f"{runner}:{name}",
                        command=f"{runner} {name}",
                        source=file_name,
                        trust="confirmed",
                    )
                )
    return commands


def looks_like_validation_command(command: str) -> bool:
    lowered = command.lower()
    if "install_enhancer.py" in lowered:
        return False
    if "tools/ai/run_checks.py" in lowered or "tools\\ai\\run_checks.py" in lowered:
        return False
    return any(name in lowered for name in VALIDATION_NAMES) or "unittest discover" in lowered


def commands_from_agents(root: Path) -> list[Command]:
    path = root / "AGENTS.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    commands: list[Command] = []
    for match in re.finditer(r"`([^`\n]+)`", text):
        command = match.group(1).strip()
        if looks_like_validation_command(command):
            commands.append(
                Command(
                    label=f"agents:{len(commands) + 1}",
                    command=command,
                    source="AGENTS.md",
                    trust="prose",
                )
            )
    return commands


def collect_manifest_command_strings(value: object, *, owner: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_owner = f"{owner}.{key}" if owner else str(key)
            if "command" in str(key):
                if isinstance(child, str):
                    found.append(child)
                elif isinstance(child, list):
                    found.extend(item for item in child if isinstance(item, str))
            found.extend(collect_manifest_command_strings(child, owner=child_owner))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_manifest_command_strings(child, owner=owner))
    return found


def commands_from_manifest(root: Path) -> list[Command]:
    path = root / ".codex/enhancer/manifest.toml"
    if not path.exists():
        return []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return []
    commands: list[Command] = []
    for command in collect_manifest_command_strings(data):
        if looks_like_validation_command(command):
            commands.append(
                Command(
                    label=f"manifest:{len(commands) + 1}",
                    command=command,
                    source=".codex/enhancer/manifest.toml",
                    trust="confirmed",
                )
            )
    return commands


def dedupe(commands: list[Command]) -> list[Command]:
    seen: set[str] = set()
    ordered: list[Command] = []
    for command in commands:
        if command.command in seen:
            continue
        seen.add(command.command)
        ordered.append(command)
    return ordered


def discover_commands(root: Path) -> list[Command]:
    return dedupe(
        [
            *commands_from_enhancer_spec(root),
            *commands_from_agents(root),
            *commands_from_manifest(root),
            *commands_from_package_json(root),
            *commands_from_makefiles(root),
        ]
    )


def print_commands(commands: list[Command]) -> None:
    if not commands:
        print("No recorded validation commands were found.")
        return
    for command in commands:
        flags: list[str] = [command.source, f"trust={command.trust}"]
        if command_requires_shell(command.command):
            flags.append("requires-shell")
        print(f"- {command.label}: `{command.command}` ({', '.join(flags)})")


def command_requires_shell(command: str) -> bool:
    return any(token in command for token in SHELL_TOKENS)


def command_argv(command: str) -> list[str]:
    return shlex.split(command, posix=True)


def run_command(root: Path, command: Command, index: int, total: int, *, allow_shell: bool) -> int:
    print(f"\n=== [{index}/{total}] {command.label}")
    print(f"source: {command.source}")
    print(f"trust: {command.trust}")
    print(f"command: {command.command}")
    if command_requires_shell(command.command):
        if not allow_shell:
            print("skipped: command contains shell control characters; rerun with --allow-shell after review")
            return 0
        completed = subprocess.run(command.command, cwd=root, shell=True)
    else:
        completed = subprocess.run(command_argv(command.command), cwd=root, shell=False)
    print(f"exit code: {completed.returncode}")
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    parser.add_argument("--list", action="store_true", help="list discovered commands and exit")
    parser.add_argument("--dry-run", action="store_true", help="show commands without running them")
    parser.add_argument(
        "--include-prose",
        action="store_true",
        help="allow commands extracted from AGENTS.md prose to run after review",
    )
    parser.add_argument(
        "--allow-shell",
        action="store_true",
        help="allow commands containing shell control characters to run after review",
    )
    parser.add_argument("--only", action="append", default=[], help="run labels containing this text; repeatable")
    parser.add_argument("--fail-fast", action="store_true", help="stop after the first failing command")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}")
        return 2

    commands = discover_commands(root)
    if args.only:
        filters = tuple(item.lower() for item in args.only)
        commands = [
            command
            for command in commands
            if any(item in command.label.lower() or item in command.command.lower() for item in filters)
        ]

    if args.list or args.dry_run:
        print_commands(commands)
        return 0 if commands else 1
    if not commands:
        print_commands(commands)
        return 1

    skipped_prose = [command for command in commands if command.trust == "prose" and not args.include_prose]
    commands = [command for command in commands if command.trust != "prose" or args.include_prose]
    if skipped_prose:
        print("Prose-extracted commands were not run by default:")
        print_commands(skipped_prose)
        print("Rerun with --include-prose after reviewing them if you intentionally want them executed.")
    if not commands:
        print("No confirmed validation commands were selected to run.")
        return 1

    failures = 0
    for index, command in enumerate(commands, start=1):
        return_code = run_command(root, command, index, len(commands), allow_shell=args.allow_shell)
        if return_code != 0:
            failures += 1
            if args.fail_fast:
                return return_code
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
