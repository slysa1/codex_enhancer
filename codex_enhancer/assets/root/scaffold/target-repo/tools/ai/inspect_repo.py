#!/usr/bin/env python3
"""Produce a bounded, Codex-friendly repository inspection report."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_IGNORE_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
}
DEFAULT_IGNORE_PATHS = {".codex/enhancer-proposals"}
BINARY_SUFFIXES = {
    ".7z",
    ".avi",
    ".bmp",
    ".bz2",
    ".class",
    ".dll",
    ".dmg",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".iso",
    ".jar",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".obj",
    ".pdf",
    ".png",
    ".pyc",
    ".rar",
    ".so",
    ".tar",
    ".webp",
    ".zip",
}
LANGUAGE_SUFFIXES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript React",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".cs": "C#",
    ".cpp": "C++",
    ".cxx": "C++",
    ".cc": "C++",
    ".c": "C",
    ".h": "C/C++ header",
    ".hpp": "C++ header",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".md": "Markdown",
}
CONFIG_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements-codex.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Makefile",
    "justfile",
    "docker-compose.yml",
    "Dockerfile",
    ".github/workflows",
}
TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs"}
DOC_DIR_NAMES = {"doc", "docs", "documentation"}


def load_pathspec(root: Path):
    patterns: list[str] = []
    for name in (".gitignore", ".ignore"):
        path = root / name
        if path.exists():
            patterns.extend(path.read_text(encoding="utf-8", errors="replace").splitlines())
    if not patterns:
        return None
    try:
        import pathspec  # type: ignore[import-not-found]
    except ImportError:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def is_default_ignored(root: Path, path: Path) -> bool:
    relative = relative_path(root, path)
    parts = Path(relative).parts
    return bool(set(parts) & DEFAULT_IGNORE_NAMES) or any(
        relative == ignored or relative.startswith(f"{ignored}/")
        for ignored in DEFAULT_IGNORE_PATHS
    )


def is_ignored(root: Path, path: Path, spec) -> bool:
    if is_default_ignored(root, path):
        return True
    if spec is None:
        return False
    return spec.match_file(relative_path(root, path))


def walk_files(root: Path, *, max_files: int, include_binary: bool) -> tuple[list[Path], bool]:
    spec = load_pathspec(root)
    files: list[Path] = []
    truncated = False
    for current, dir_names, file_names in os.walk(root):
        current_path = Path(current)
        dir_names[:] = [
            name
            for name in sorted(dir_names)
            if not is_ignored(root, current_path / name, spec)
        ]
        for name in sorted(file_names):
            path = current_path / name
            if is_ignored(root, path, spec):
                continue
            if not include_binary and path.suffix.lower() in BINARY_SUFFIXES:
                continue
            files.append(path)
            if len(files) >= max_files:
                return files, True
    return files, truncated


def read_package_scripts(root: Path) -> dict[str, str]:
    package_json = root / "package.json"
    if not package_json.exists():
        return {}
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in sorted(scripts.items())}


def top_level_name(root: Path, path: Path) -> str:
    parts = path.relative_to(root).parts
    return parts[0] if parts else "."


def print_section(title: str, lines: list[str]) -> None:
    print(f"\n## {title}")
    if not lines:
        print("- none found")
        return
    for line in lines:
        print(f"- {line}")


def build_report(root: Path, *, max_files: int, include_binary: bool) -> None:
    files, truncated = walk_files(root, max_files=max_files, include_binary=include_binary)
    dir_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    configs: list[str] = []
    docs: list[str] = []
    tests: list[str] = []
    suffix_counts: Counter[str] = Counter()
    by_directory: dict[str, int] = defaultdict(int)

    for path in files:
        relative = relative_path(root, path)
        top = top_level_name(root, path)
        by_directory[top] += 1
        suffix = path.suffix.lower() or "<none>"
        suffix_counts[suffix] += 1
        language = LANGUAGE_SUFFIXES.get(path.suffix.lower())
        if language:
            language_counts[language] += 1
        if path.name in CONFIG_NAMES or relative in CONFIG_NAMES:
            configs.append(relative)
        if any(part.lower() in DOC_DIR_NAMES for part in path.relative_to(root).parts) or path.name.lower().startswith("readme"):
            docs.append(relative)
        if any(part.lower() in TEST_DIR_NAMES for part in path.relative_to(root).parts):
            tests.append(relative)

    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if child.is_dir() and not is_default_ignored(root, child):
            dir_counts[child.name] = by_directory.get(child.name, 0)

    print(f"# Repository Inspection: {root.name}")
    print(f"- Root: {root}")
    print(f"- Files scanned: {len(files)}{' (truncated)' if truncated else ''}")
    print(f"- Binary/media/archive files: {'included' if include_binary else 'skipped by suffix'}")
    print("- Ignore rules: built-in junk ignores plus .gitignore/.ignore when pathspec is installed")

    print_section(
        "Major Directories",
        [f"{name}/ ({count} scanned file(s))" for name, count in dir_counts.most_common(12)],
    )
    print_section(
        "Likely Languages",
        [f"{name}: {count} file(s)" for name, count in language_counts.most_common(12)],
    )
    print_section(
        "Common File Types",
        [f"{suffix}: {count}" for suffix, count in suffix_counts.most_common(12)],
    )
    print_section("Config And Manifests", sorted(configs)[:40])
    print_section("Docs", sorted(docs)[:30])
    print_section("Tests", sorted(tests)[:30])

    scripts = read_package_scripts(root)
    validation_script_names = [name for name in ("check", "lint", "test", "typecheck", "build") if name in scripts]
    print_section(
        "Package Validation Scripts",
        [f"{name}: {scripts[name]}" for name in validation_script_names],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root to inspect")
    parser.add_argument("--max-files", type=int, default=2000, help="maximum files to scan")
    parser.add_argument(
        "--include-binary",
        action="store_true",
        help="include binary/media/archive suffixes in the scan",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}")
        return 2
    build_report(root, max_files=max(1, args.max_files), include_binary=args.include_binary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
