#!/usr/bin/env python3
"""Shared constants for validating and installing Codex Enhancer assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


CHECK_COMMAND = "python scripts/check.py"
TEST_COMMAND = 'python -m unittest discover -s tests -p "test_*.py" -v'

GITIGNORE_LINES = (
    "__pycache__/",
    "*.py[cod]",
    "tests/_tmp/",
)


@dataclass(frozen=True)
class ValidationProfile:
    """Describe the files and content a repo-local enhancer must contain."""

    name: str
    required_files: tuple[Path, ...]
    line_limits: dict[Path, int]
    min_required_skills: frozenset[str]
    content_requirements: dict[Path, tuple[str, ...]]


@dataclass(frozen=True)
class TemplateAsset:
    """A scaffold file rendered from a template into the target repository."""

    template_path: Path
    destination: Path


@dataclass(frozen=True)
class CopyAsset:
    """A source-repo file copied into the target repository without templating."""

    source_path: Path
    destination: Path


SOURCE_VALIDATION_PROFILE = ValidationProfile(
    name="source",
    required_files=(
        Path(".gitignore"),
        Path(".github/workflows/validate.yml"),
        Path("AGENTS.md"),
        Path("README.md"),
        Path("install_enhancer.bat"),
        Path("docs/ai/architecture.md"),
        Path("docs/ai/code-review.md"),
        Path(".codex/skills/AGENTS.md"),
        Path(".codex/skills/plan-change/SKILL.md"),
        Path(".codex/skills/review-prep/SKILL.md"),
        Path(".codex/skills/adapt-enhancer/SKILL.md"),
        Path("scripts/check.py"),
        Path("scripts/enhancer_spec.py"),
        Path("scripts/enhancer_validator.py"),
        Path("scripts/install_enhancer.py"),
        Path("scripts/install_enhancer_gui.py"),
        Path("tests/test_check.py"),
        Path("tests/test_install_enhancer.py"),
        Path("scaffold/target-repo/AGENTS.md"),
        Path("scaffold/target-repo/docs/ai/architecture.md"),
        Path("scaffold/target-repo/docs/ai/code-review.md"),
        Path("scaffold/target-repo/.codex/skills/adapt-enhancer/SKILL.md"),
        Path("scaffold/target-repo/scripts/check.py"),
        Path("scaffold/target-repo/tests/test_check.py"),
        Path("scaffold/target-repo/.github/workflows/validate.yml"),
    ),
    line_limits={
        Path("AGENTS.md"): 140,
        Path(".codex/skills/AGENTS.md"): 80,
    },
    min_required_skills=frozenset({"plan-change", "review-prep", "adapt-enhancer"}),
    content_requirements={
        Path("README.md"): (
            "AGENTS.md",
            CHECK_COMMAND,
            TEST_COMMAND,
            "install_enhancer.bat",
            "scripts/install_enhancer_gui.py",
        ),
        Path("AGENTS.md"): (
            CHECK_COMMAND,
            TEST_COMMAND,
            "install_enhancer.bat",
            "docs/ai/architecture.md",
            "docs/ai/code-review.md",
            ".codex/skills/",
            "tests/",
        ),
        Path("docs/ai/code-review.md"): (
            CHECK_COMMAND,
            TEST_COMMAND,
        ),
        Path(".github/workflows/validate.yml"): (
            CHECK_COMMAND,
            TEST_COMMAND,
        ),
    },
)


TARGET_VALIDATION_PROFILE = ValidationProfile(
    name="target",
    required_files=(
        Path("AGENTS.md"),
        Path("docs/ai/architecture.md"),
        Path("docs/ai/code-review.md"),
        Path(".codex/skills/AGENTS.md"),
        Path(".codex/skills/plan-change/SKILL.md"),
        Path(".codex/skills/review-prep/SKILL.md"),
        Path(".codex/skills/adapt-enhancer/SKILL.md"),
        Path("scripts/check.py"),
        Path("scripts/enhancer_spec.py"),
        Path("scripts/enhancer_validator.py"),
        Path("tests/test_check.py"),
        Path(".github/workflows/validate.yml"),
    ),
    line_limits={
        Path("AGENTS.md"): 180,
        Path(".codex/skills/AGENTS.md"): 80,
    },
    min_required_skills=frozenset({"plan-change", "review-prep", "adapt-enhancer"}),
    content_requirements={
        Path("AGENTS.md"): (
            CHECK_COMMAND,
            TEST_COMMAND,
            "docs/ai/architecture.md",
            "docs/ai/code-review.md",
            ".codex/skills/",
            "tests/",
            "adapt-enhancer",
        ),
        Path("docs/ai/code-review.md"): (
            CHECK_COMMAND,
            TEST_COMMAND,
        ),
        Path(".github/workflows/validate.yml"): (
            CHECK_COMMAND,
            TEST_COMMAND,
        ),
    },
)


INSTALL_TEMPLATE_ASSETS = (
    TemplateAsset(
        template_path=Path("scaffold/target-repo/AGENTS.md"),
        destination=Path("AGENTS.md"),
    ),
    TemplateAsset(
        template_path=Path("scaffold/target-repo/docs/ai/architecture.md"),
        destination=Path("docs/ai/architecture.md"),
    ),
    TemplateAsset(
        template_path=Path("scaffold/target-repo/docs/ai/code-review.md"),
        destination=Path("docs/ai/code-review.md"),
    ),
    TemplateAsset(
        template_path=Path("scaffold/target-repo/scripts/check.py"),
        destination=Path("scripts/check.py"),
    ),
    TemplateAsset(
        template_path=Path("scaffold/target-repo/tests/test_check.py"),
        destination=Path("tests/test_check.py"),
    ),
    TemplateAsset(
        template_path=Path("scaffold/target-repo/.github/workflows/validate.yml"),
        destination=Path(".github/workflows/validate.yml"),
    ),
    TemplateAsset(
        template_path=Path("scaffold/target-repo/.codex/skills/adapt-enhancer/SKILL.md"),
        destination=Path(".codex/skills/adapt-enhancer/SKILL.md"),
    ),
)


INSTALL_COPY_ASSETS = (
    CopyAsset(
        source_path=Path(".codex/skills/AGENTS.md"),
        destination=Path(".codex/skills/AGENTS.md"),
    ),
    CopyAsset(
        source_path=Path(".codex/skills/plan-change/SKILL.md"),
        destination=Path(".codex/skills/plan-change/SKILL.md"),
    ),
    CopyAsset(
        source_path=Path(".codex/skills/review-prep/SKILL.md"),
        destination=Path(".codex/skills/review-prep/SKILL.md"),
    ),
    CopyAsset(
        source_path=Path("scripts/enhancer_spec.py"),
        destination=Path("scripts/enhancer_spec.py"),
    ),
    CopyAsset(
        source_path=Path("scripts/enhancer_validator.py"),
        destination=Path("scripts/enhancer_validator.py"),
    ),
)
