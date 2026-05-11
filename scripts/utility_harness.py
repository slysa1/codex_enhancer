#!/usr/bin/env python3
"""Resolve and summarize the optional Codex Utility Harness integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


UTILITY_HARNESS_MODES = ("off", "install")
UTILITY_HARNESS_REQUIREMENTS = Path("requirements-codex.txt")
UTILITY_HARNESS_DOC = Path("docs/ai/utility-harness.md")
UTILITY_HARNESS_TOOL_FILES = (
    Path("tools/ai/inspect_repo.py"),
    Path("tools/ai/read_any.py"),
    Path("tools/ai/summarize_tree.py"),
    Path("tools/ai/run_checks.py"),
)
UTILITY_HARNESS_REQUIRED_FILES = (
    UTILITY_HARNESS_REQUIREMENTS,
    UTILITY_HARNESS_DOC,
    *UTILITY_HARNESS_TOOL_FILES,
)
UTILITY_HARNESS_DEPENDENCY_POLICY = (
    "Codex/operator helper dependencies only; install manually into a local helper environment."
)


@dataclass(frozen=True)
class UtilityHarnessConfig:
    mode: str
    state: str
    managed_by: str
    requirements_file: str | None
    docs_file: str | None
    tool_files: tuple[str, ...]
    dependency_policy: str

    @property
    def enabled(self) -> bool:
        return self.state == "installed"


def resolve_utility_harness(
    *,
    mode: str | None = "off",
    existing: UtilityHarnessConfig | None = None,
) -> UtilityHarnessConfig:
    if mode is None:
        if existing is not None:
            return existing
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
            docs_file=UTILITY_HARNESS_DOC.as_posix(),
            tool_files=tuple(path.as_posix() for path in UTILITY_HARNESS_TOOL_FILES),
            dependency_policy=UTILITY_HARNESS_DEPENDENCY_POLICY,
        )

    return UtilityHarnessConfig(
        mode="off",
        state="absent",
        managed_by="codex-enhancer",
        requirements_file=None,
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
            f"- Optional helper dependencies are listed in `{config.requirements_file}`; install them manually outside production dependency files.",
            f"- Available tools: {tools}.",
        ]
    )
