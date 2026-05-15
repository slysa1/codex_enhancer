#!/usr/bin/env python3
"""Resolve and summarize the optional Codex Utility Harness integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


UTILITY_HARNESS_MODES = ("off", "install")
UTILITY_HARNESS_REQUIREMENTS = Path("requirements-codex.txt")
UTILITY_HARNESS_DEPENDENCY_FILES = (
    UTILITY_HARNESS_REQUIREMENTS,
    Path("requirements-codex-minimal.txt"),
    Path("requirements-codex-readers.txt"),
    Path("requirements-codex-analysis.txt"),
    Path("requirements-codex-cli.txt"),
)
UTILITY_HARNESS_DOC = Path("docs/ai/utility-harness.md")
UTILITY_HARNESS_TOOL_FILES = (
    Path("tools/ai/audit_inputs.py"),
    Path("tools/ai/inspect_repo.py"),
    Path("tools/ai/read_any.py"),
    Path("tools/ai/summarize_tree.py"),
    Path("tools/ai/run_checks.py"),
)
UTILITY_HARNESS_REQUIRED_FILES = (
    *UTILITY_HARNESS_DEPENDENCY_FILES,
    UTILITY_HARNESS_DOC,
    *UTILITY_HARNESS_TOOL_FILES,
)
UTILITY_HARNESS_DEPENDENCY_POLICY = (
    "Codex/operator helper dependencies only; install only into a local helper environment."
)


@dataclass(frozen=True)
class UtilityHarnessConfig:
    mode: str
    state: str
    managed_by: str
    requirements_file: str | None
    dependency_files: tuple[str, ...]
    docs_file: str | None
    tool_files: tuple[str, ...]
    dependency_policy: str

    @property
    def enabled(self) -> bool:
        return self.state == "installed"


def normalize_utility_harness(config: UtilityHarnessConfig) -> UtilityHarnessConfig:
    if not config.enabled:
        return config
    dependency_files = config.dependency_files or tuple(
        path.as_posix() for path in UTILITY_HARNESS_DEPENDENCY_FILES
    )
    requirements_file = config.requirements_file or UTILITY_HARNESS_REQUIREMENTS.as_posix()
    docs_file = config.docs_file or UTILITY_HARNESS_DOC.as_posix()
    tool_files = config.tool_files or tuple(path.as_posix() for path in UTILITY_HARNESS_TOOL_FILES)
    if (
        dependency_files == config.dependency_files
        and requirements_file == config.requirements_file
        and docs_file == config.docs_file
        and tool_files == config.tool_files
    ):
        return config
    return UtilityHarnessConfig(
        mode=config.mode,
        state=config.state,
        managed_by=config.managed_by,
        requirements_file=requirements_file,
        dependency_files=dependency_files,
        docs_file=docs_file,
        tool_files=tool_files,
        dependency_policy=config.dependency_policy,
    )


def resolve_utility_harness(
    *,
    mode: str | None = "off",
    existing: UtilityHarnessConfig | None = None,
) -> UtilityHarnessConfig:
    if mode is None:
        if existing is not None:
            return normalize_utility_harness(existing)
        mode = "off"

    if mode not in UTILITY_HARNESS_MODES:
        choices = ", ".join(UTILITY_HARNESS_MODES)
        raise ValueError(f"Unknown Utility Harness mode {mode!r}. Expected one of: {choices}.")

    if mode == "install":
        return UtilityHarnessConfig(
            mode="install",
            state="installed",
            managed_by="codex-enhancer",
            requirements_file=UTILITY_HARNESS_REQUIREMENTS.as_posix(),
            dependency_files=tuple(path.as_posix() for path in UTILITY_HARNESS_DEPENDENCY_FILES),
            docs_file=UTILITY_HARNESS_DOC.as_posix(),
            tool_files=tuple(path.as_posix() for path in UTILITY_HARNESS_TOOL_FILES),
            dependency_policy=UTILITY_HARNESS_DEPENDENCY_POLICY,
        )

    return UtilityHarnessConfig(
        mode="off",
        state="absent",
        managed_by="codex-enhancer",
        requirements_file=None,
        dependency_files=(),
        docs_file=None,
        tool_files=(),
        dependency_policy=UTILITY_HARNESS_DEPENDENCY_POLICY,
    )


def render_utility_harness_summary(config: UtilityHarnessConfig) -> str:
    if not config.enabled:
        return (
            "- Codex Utility Harness is not installed for this enhancer install.\n"
            "- Re-run the installer with `--utility-harness-mode install` only when this repo needs repo-local helper tools for Codex/operator inspection."
        )

    tools = ", ".join(f"`python {path}`" for path in config.tool_files)
    return "\n".join(
        [
            "- Codex Utility Harness is installed for explicit Codex/operator use.",
            f"- Read [{config.docs_file}]({config.docs_file}) before using the helper scripts.",
            f"- Optional helper dependency groups are listed in `{config.requirements_file}` and the narrower `requirements-codex-*.txt` files; install only the groups you need into a local helper environment.",
            f"- Available tools: {tools}.",
        ]
    )
