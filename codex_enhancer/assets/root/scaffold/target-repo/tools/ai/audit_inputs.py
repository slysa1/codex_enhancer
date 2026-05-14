#!/usr/bin/env python3
"""Inventory repository inputs for a no-implementation improvement audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Callable


HELPER_DIR = Path(__file__).resolve().parent
if str(HELPER_DIR) not in sys.path:
    sys.path.insert(0, str(HELPER_DIR))

from inspect_repo import relative_path, walk_files  # noqa: E402
from run_checks import command_requires_shell, discover_commands  # noqa: E402


MANIFEST_NAMES = {
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "bun.lock",
    "bun.lockb",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-codex.txt",
    "poetry.lock",
    "uv.lock",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "composer.json",
    "Gemfile",
    "Gemfile.lock",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
    "justfile",
}
GUIDANCE_NAMES = {"AGENTS.md", "CLAUDE.md", "README.md", "CONTEXT.md"}
GUIDANCE_PREFIXES = (
    ".codex/skills/",
    ".agents/skills/",
    ".github/prompts/",
    ".github/agents/",
    "docs/ai/",
)
TEST_PARTS = {"test", "tests", "__tests__", "spec", "specs"}
CI_NAMES = {
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    "Jenkinsfile",
}
SECURITY_HINTS = (
    "dependabot",
    "codeql",
    "semgrep",
    "bandit",
    "pip-audit",
    "safety",
    "trivy",
    "grype",
    "osv-scanner",
    "snyk",
    "security",
)
PERFORMANCE_HINTS = (
    "benchmark",
    "bench",
    "performance",
    "perf",
    "load-test",
    "load_test",
    "lighthouse",
    "k6",
    "locust",
)
ROADMAP_NAMES = {"roadmap.md", "roadmap.txt"}


def posix_parts(relative: str) -> tuple[str, ...]:
    return PurePosixPath(relative).parts


def has_part(relative: str, candidates: set[str]) -> bool:
    return any(part.lower() in candidates for part in posix_parts(relative))


def starts_with_any(relative: str, prefixes: tuple[str, ...]) -> bool:
    return any(relative == prefix.rstrip("/") or relative.startswith(prefix) for prefix in prefixes)


def limited_paths(
    root: Path,
    files: list[Path],
    predicate: Callable[[str, Path], bool],
    *,
    limit: int,
) -> list[str]:
    found = sorted(
        {
            relative
            for path in files
            for relative in [relative_path(root, path)]
            if predicate(relative, path)
        }
    )
    return found[:limit]


def is_manifest(relative: str, path: Path) -> bool:
    return path.name in MANIFEST_NAMES or relative in MANIFEST_NAMES


def is_guidance(relative: str, path: Path) -> bool:
    return path.name in GUIDANCE_NAMES or starts_with_any(relative, GUIDANCE_PREFIXES)


def is_test(relative: str, path: Path) -> bool:
    return has_part(relative, TEST_PARTS) or path.name.startswith("test_") or path.name.endswith("_test.py")


def is_ci(relative: str, path: Path) -> bool:
    return relative.startswith(".github/workflows/") or path.name in CI_NAMES


def is_security(relative: str, path: Path) -> bool:
    lowered = relative.lower()
    return any(hint in lowered for hint in SECURITY_HINTS)


def is_performance(relative: str, path: Path) -> bool:
    lowered = relative.lower()
    return any(hint in lowered for hint in PERFORMANCE_HINTS)


def is_roadmap(relative: str, path: Path) -> bool:
    return path.name.lower() in ROADMAP_NAMES or relative.lower() in {
        "docs/roadmap.md",
        "docs/ai/roadmap.md",
    }


def roadmap_target(root: Path, roadmap_inputs: list[str]) -> dict[str, str]:
    for candidate in ("roadmap.md", "ROADMAP.md"):
        if (root / candidate).exists():
            return {"status": "existing", "path": candidate}
    if roadmap_inputs:
        return {"status": "existing", "path": roadmap_inputs[0]}
    return {"status": "missing", "path": "roadmap.md"}


def build_inventory(
    root: Path,
    *,
    max_files: int,
    max_entries: int,
    include_binary: bool,
) -> dict[str, object]:
    files, truncated = walk_files(root, max_files=max_files, include_binary=include_binary)
    manifests = limited_paths(root, files, is_manifest, limit=max_entries)
    guidance = limited_paths(root, files, is_guidance, limit=max_entries)
    tests = limited_paths(root, files, is_test, limit=max_entries)
    ci = limited_paths(root, files, is_ci, limit=max_entries)
    security = limited_paths(root, files, is_security, limit=max_entries)
    performance = limited_paths(root, files, is_performance, limit=max_entries)
    roadmaps = limited_paths(root, files, is_roadmap, limit=max_entries)
    commands = discover_commands(root)

    return {
        "schema_version": 1,
        "root": str(root),
        "files_scanned": len(files),
        "truncated": truncated,
        "roadmap_target": roadmap_target(root, roadmaps),
        "system_map_inputs": sorted(set(guidance + manifests + ci))[:max_entries],
        "guidance_inputs": guidance,
        "manifest_inputs": manifests,
        "test_inputs": tests,
        "ci_inputs": ci,
        "security_inputs": security,
        "performance_inputs": performance,
        "roadmap_inputs": roadmaps,
        "validation_commands": [
            {
                "label": command.label,
                "command": command.command,
                "source": command.source,
                "trust": command.trust,
                "requires_shell": command_requires_shell(command.command),
            }
            for command in commands
        ],
        "limitations": [
            "This inventory does not execute commands, install dependencies, or validate findings.",
            "Treat every listed path as an audit input candidate that still needs direct inspection.",
        ],
    }


def print_path_section(title: str, paths: list[str]) -> None:
    print(f"\n## {title}")
    if not paths:
        print("- none found")
        return
    for path in paths:
        print(f"- {path}")


def print_command_section(commands: list[dict[str, object]]) -> None:
    print("\n## Validation Commands")
    if not commands:
        print("- none found")
        return
    for command in commands:
        flags = [str(command["source"]), f"trust={command['trust']}"]
        if command["requires_shell"]:
            flags.append("requires-shell")
        print(f"- {command['label']}: `{command['command']}` ({', '.join(flags)})")


def print_inventory(inventory: dict[str, object]) -> None:
    roadmap = inventory["roadmap_target"]
    if not isinstance(roadmap, dict):
        raise TypeError("roadmap_target must be a mapping")

    print("# Audit Input Inventory")
    print(f"- Root: {inventory['root']}")
    print(f"- Files scanned: {inventory['files_scanned']}{' (truncated)' if inventory['truncated'] else ''}")
    print(f"- Roadmap target: {roadmap['path']} ({roadmap['status']})")
    print("- Commands are only listed; nothing is executed.")

    for title, key in (
        ("System Map Inputs", "system_map_inputs"),
        ("Guidance Inputs", "guidance_inputs"),
        ("Manifests And Config", "manifest_inputs"),
        ("Tests", "test_inputs"),
        ("CI", "ci_inputs"),
        ("Security And Supply Chain", "security_inputs"),
        ("Performance", "performance_inputs"),
        ("Roadmap Inputs", "roadmap_inputs"),
    ):
        value = inventory[key]
        if not isinstance(value, list):
            raise TypeError(f"{key} must be a list")
        print_path_section(title, [str(item) for item in value])

    commands = inventory["validation_commands"]
    if not isinstance(commands, list):
        raise TypeError("validation_commands must be a list")
    print_command_section([item for item in commands if isinstance(item, dict)])

    limitations = inventory["limitations"]
    if isinstance(limitations, list):
        print_path_section("Limitations", [str(item) for item in limitations])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    parser.add_argument("--max-files", type=int, default=2000, help="maximum files to scan")
    parser.add_argument("--max-entries", type=int, default=40, help="maximum entries per section")
    parser.add_argument("--include-binary", action="store_true", help="include binary/media/archive files")
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}")
        return 2

    inventory = build_inventory(
        root,
        max_files=max(1, args.max_files),
        max_entries=max(1, args.max_entries),
        include_binary=args.include_binary,
    )
    if args.json:
        print(json.dumps(inventory, indent=2, sort_keys=True))
    else:
        print_inventory(inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
