#!/usr/bin/env python3
"""Print a bounded project tree for Codex context gathering."""

from __future__ import annotations

import argparse
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
    ".dll",
    ".dmg",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".iso",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".rar",
    ".tar",
    ".webp",
    ".zip",
}


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


def is_ignored(root: Path, path: Path, spec, *, include_binary: bool) -> bool:
    relative = relative_path(root, path)
    parts = Path(relative).parts
    if set(parts) & DEFAULT_IGNORE_NAMES:
        return True
    if any(relative == ignored or relative.startswith(f"{ignored}/") for ignored in DEFAULT_IGNORE_PATHS):
        return True
    if path.is_file() and not include_binary and path.suffix.lower() in BINARY_SUFFIXES:
        return True
    if spec is not None and spec.match_file(relative):
        return True
    return False


def visible_children(root: Path, directory: Path, spec, *, include_binary: bool) -> list[Path]:
    try:
        children = sorted(directory.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
    except OSError:
        return []
    return [
        child
        for child in children
        if not is_ignored(root, child, spec, include_binary=include_binary)
    ]


def render_tree(
    root: Path,
    directory: Path,
    spec,
    *,
    depth: int,
    max_depth: int,
    max_entries: int,
    include_binary: bool,
    counts: dict[str, int],
) -> None:
    if depth > max_depth or counts["entries"] >= max_entries:
        return
    children = visible_children(root, directory, spec, include_binary=include_binary)
    if depth == 0:
        print(f"{root.name}/")
    for index, child in enumerate(children):
        if counts["entries"] >= max_entries:
            print("... entry limit reached")
            return
        is_last = index == len(children) - 1
        branch = "`-- " if is_last else "|-- "
        prefix = "    " * depth
        suffix = "/" if child.is_dir() else ""
        print(f"{prefix}{branch}{child.name}{suffix}")
        counts["entries"] += 1
        if child.is_dir():
            render_tree(
                root,
                child,
                spec,
                depth=depth + 1,
                max_depth=max_depth,
                max_entries=max_entries,
                include_binary=include_binary,
                counts=counts,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    parser.add_argument("--max-depth", type=int, default=3, help="maximum directory depth")
    parser.add_argument("--max-entries", type=int, default=250, help="maximum printed entries")
    parser.add_argument("--include-binary", action="store_true", help="include binary/media/archive files")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}")
        return 2
    spec = load_pathspec(root)
    render_tree(
        root,
        root,
        spec,
        depth=0,
        max_depth=max(0, args.max_depth),
        max_entries=max(1, args.max_entries),
        include_binary=args.include_binary,
        counts={"entries": 0},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
