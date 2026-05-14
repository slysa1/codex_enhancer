#!/usr/bin/env python3
"""Shared constants for validating and installing Codex Enhancer assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ENHANCER_VERSION = "4.1.0"
ENHANCER_MANIFEST_SCHEMA_VERSION = 3
SUPPORTED_ENHANCER_MANIFEST_SCHEMA_VERSIONS = frozenset({1, 2, ENHANCER_MANIFEST_SCHEMA_VERSION})

CHECK_COMMAND = "python scripts/check.py"
TEST_COMMAND = 'python -m unittest discover -s tests -p "test_*.py" -v'

GITIGNORE_LINES = (
    "__pycache__/",
    "*.py[cod]",
    "tests/_tmp/",
)


@dataclass(frozen=True)
class ManagedSection:
    """A visible enhancer-owned section inside an otherwise repo-owned file."""

    identifier: str
    path: Path
    start_marker: str
    end_marker: str


MANAGED_SECTIONS = (
    ManagedSection(
        identifier="AGENTS.md:selected-stack-packs",
        path=Path("AGENTS.md"),
        start_marker="<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs start -->",
        end_marker="<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs end -->",
    ),
    ManagedSection(
        identifier="AGENTS.md:spec-kit-bridge",
        path=Path("AGENTS.md"),
        start_marker="<!-- codex-enhancer:managed-section AGENTS.md:spec-kit-bridge start -->",
        end_marker="<!-- codex-enhancer:managed-section AGENTS.md:spec-kit-bridge end -->",
    ),
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


SPEC_KIT_BRIDGE_TEMPLATE_PATH = Path("scaffold/target-repo/docs/ai/spec-kit-bridge.md")


SOURCE_VALIDATION_PROFILE = ValidationProfile(
    name="source",
    required_files=(
        Path(".gitignore"),
        Path(".github/workflows/validate.yml"),
        Path("AGENTS.md"),
        Path("README.md"),
        Path("MANIFEST.in"),
        Path("pyproject.toml"),
        Path("codex-enhancer"),
        Path("codex-enhancer.bat"),
        Path("codex_enhancer/__init__.py"),
        Path("codex_enhancer/package_assets.py"),
        Path("install_enhancer.bat"),
        Path("docs/ai/architecture.md"),
        Path("docs/ai/code-review.md"),
        Path("docs/ai/migration-v3.md"),
        Path("docs/ai/roadmap.md"),
        Path("docs/ai/release.md"),
        Path("docs/ai/spec-kit-bridge.md"),
        Path("docs/ai/utility-harness.md"),
        Path(".codex/skills/AGENTS.md"),
        Path(".codex/skills/plan-change/SKILL.md"),
        Path(".codex/skills/review-prep/SKILL.md"),
        Path(".codex/skills/adapt-enhancer/SKILL.md"),
        Path("scripts/check.py"),
        Path("scripts/codex_enhancer_cli.py"),
        Path("scripts/enhancer_spec.py"),
        Path("scripts/spec_kit_bridge.py"),
        Path("scripts/utility_harness.py"),
        Path("scripts/enhancer_validator.py"),
        Path("scripts/install_enhancer.py"),
        Path("scripts/install_enhancer_gui.py"),
        Path("scripts/stack_packs.py"),
        Path("tests/test_check.py"),
        Path("tests/test_codex_enhancer_cli.py"),
        Path("tests/test_install_enhancer.py"),
        Path("tests/test_packaging.py"),
        Path("tests/test_spec_kit_bridge.py"),
        Path("tests/test_utility_harness.py"),
        Path("tests/test_stack_packs.py"),
        Path("scaffold/target-repo/AGENTS.md"),
        Path("scaffold/target-repo/docs/ai/architecture.md"),
        Path("scaffold/target-repo/docs/ai/code-review.md"),
        Path("scaffold/target-repo/docs/ai/spec-kit-bridge.md"),
        Path("scaffold/target-repo/docs/ai/utility-harness.md"),
        Path("scaffold/target-repo/.codex/skills/adapt-enhancer/SKILL.md"),
        Path("scaffold/target-repo/.codex/skills/spec-implement-bridge/SKILL.md"),
        Path("scaffold/target-repo/.codex/skills/spec-sync-check/SKILL.md"),
        Path("scaffold/target-repo/.codex/skills/spec-review-bridge/SKILL.md"),
        Path("scaffold/target-repo/requirements-codex.txt"),
        Path("scaffold/target-repo/requirements-codex-minimal.txt"),
        Path("scaffold/target-repo/requirements-codex-readers.txt"),
        Path("scaffold/target-repo/requirements-codex-analysis.txt"),
        Path("scaffold/target-repo/requirements-codex-cli.txt"),
        Path("scaffold/target-repo/tools/ai/inspect_repo.py"),
        Path("scaffold/target-repo/tools/ai/read_any.py"),
        Path("scaffold/target-repo/tools/ai/summarize_tree.py"),
        Path("scaffold/target-repo/tools/ai/run_checks.py"),
        Path("scaffold/target-repo/scripts/check.py"),
        Path("scaffold/target-repo/tests/test_check.py"),
        Path("scaffold/target-repo/.github/workflows/validate.yml"),
        Path("scaffold/stack-packs/monorepo-workspace/pack.toml"),
        Path("scaffold/stack-packs/monorepo-workspace/fragments/agents-summary.md"),
        Path("scaffold/stack-packs/monorepo-workspace/fragments/stack-guidance.md"),
        Path("scaffold/stack-packs/monorepo-workspace/fragments/review-notes.md"),
        Path("scaffold/stack-packs/javascript-typescript-app/pack.toml"),
        Path("scaffold/stack-packs/javascript-typescript-app/fragments/agents-summary.md"),
        Path("scaffold/stack-packs/javascript-typescript-app/fragments/stack-guidance.md"),
        Path("scaffold/stack-packs/javascript-typescript-app/fragments/review-notes.md"),
        Path("scaffold/stack-packs/frontend-ui/pack.toml"),
        Path("scaffold/stack-packs/frontend-ui/fragments/agents-summary.md"),
        Path("scaffold/stack-packs/frontend-ui/fragments/stack-guidance.md"),
        Path("scaffold/stack-packs/frontend-ui/fragments/review-notes.md"),
        Path("scaffold/stack-packs/python-service/pack.toml"),
        Path("scaffold/stack-packs/python-service/fragments/agents-summary.md"),
        Path("scaffold/stack-packs/python-service/fragments/stack-guidance.md"),
        Path("scaffold/stack-packs/python-service/fragments/review-notes.md"),
        Path("scaffold/stack-packs/node-api-service/pack.toml"),
        Path("scaffold/stack-packs/node-api-service/fragments/agents-summary.md"),
        Path("scaffold/stack-packs/node-api-service/fragments/stack-guidance.md"),
        Path("scaffold/stack-packs/node-api-service/fragments/review-notes.md"),
        Path("scaffold/stack-packs/library-package/pack.toml"),
        Path("scaffold/stack-packs/library-package/fragments/agents-summary.md"),
        Path("scaffold/stack-packs/library-package/fragments/stack-guidance.md"),
        Path("scaffold/stack-packs/library-package/fragments/review-notes.md"),
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
            "pip install -e .",
            "python -m build",
            "codex-enhancer.bat",
            "scripts/codex_enhancer_cli.py",
            "--with-spec-kit",
            "install_enhancer.bat",
            "scripts/install_enhancer_gui.py",
            "docs/ai/migration-v3.md",
            "docs/ai/roadmap.md",
            "docs/ai/release.md",
            "docs/ai/utility-harness.md",
            "requirements-codex-readers.txt",
            "--utility-harness-mode",
            "--summary",
            "--diff",
            "--json",
            "audit",
            "spec-report",
            "spec-sync",
            "bridge",
        ),
        Path("AGENTS.md"): (
            CHECK_COMMAND,
            TEST_COMMAND,
            "pyproject.toml",
            "codex_enhancer/package_assets.py",
            "codex-enhancer.bat",
            "scripts/codex_enhancer_cli.py",
            "--with-spec-kit",
            "install_enhancer.bat",
            "docs/ai/architecture.md",
            "docs/ai/code-review.md",
            "docs/ai/migration-v3.md",
            "docs/ai/roadmap.md",
            "docs/ai/release.md",
            "docs/ai/spec-kit-bridge.md",
            "docs/ai/utility-harness.md",
            ".codex/skills/",
            "audit",
            "spec-sync",
            "scripts/utility_harness.py",
            "tests/",
        ),
        Path("docs/ai/code-review.md"): (
            CHECK_COMMAND,
            TEST_COMMAND,
            "docs/ai/migration-v3.md",
            "docs/ai/release.md",
            "docs/ai/spec-kit-bridge.md",
            "docs/ai/utility-harness.md",
        ),
        Path("pyproject.toml"): (
            "setuptools",
            "GPL-3.0-or-later",
            "license-files",
            "include-package-data",
            "codex_enhancer*",
            "scripts.codex_enhancer_cli:main",
            "scripts.enhancer_spec.ENHANCER_VERSION",
        ),
        Path("MANIFEST.in"): (
            "codex_enhancer/assets/root",
            "recursive-include",
        ),
        Path("docs/ai/migration-v3.md"): (
            "--inspect-install",
            "--upgrade-enhancer",
            "--manage-packs",
            "--manage-spec-kit-bridge",
            "--spec-kit-report",
            "--spec-kit-sync-report",
            "--refresh-generated",
            "audit",
        ),
        Path("docs/ai/release.md"): (
            "python -m build",
            "codex-enhancer list-packs",
            "requirements-codex.txt",
            "requirements-codex-readers.txt",
            "codex_enhancer/assets/root/",
        ),
        Path("docs/ai/spec-kit-bridge.md"): (
            "uvx",
            "--spec-kit-exe",
            "spec-report",
            "spec-sync",
            "bridge",
            "official Spec Kit files",
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
        Path("docs/ai/spec-kit-bridge.md"),
        Path("docs/ai/stack-guidance.md"),
        Path(".codex/skills/AGENTS.md"),
        Path(".codex/skills/plan-change/SKILL.md"),
        Path(".codex/skills/review-prep/SKILL.md"),
        Path(".codex/skills/adapt-enhancer/SKILL.md"),
        Path(".codex/enhancer/manifest.toml"),
        Path("scripts/check.py"),
        Path("scripts/enhancer_spec.py"),
        Path("scripts/spec_kit_bridge.py"),
        Path("scripts/utility_harness.py"),
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
            "docs/ai/spec-kit-bridge.md",
            "docs/ai/stack-guidance.md",
            ".codex/enhancer/manifest.toml",
            ".codex/skills/",
            "tests/",
            "adapt-enhancer",
        ),
        Path("docs/ai/architecture.md"): (
            "spec-kit-bridge.md",
            "stack-guidance.md",
            ".codex/enhancer/manifest.toml",
        ),
        Path("docs/ai/code-review.md"): (
            CHECK_COMMAND,
            TEST_COMMAND,
            "spec-kit-bridge.md",
            "stack-guidance.md",
            ".codex/enhancer/manifest.toml",
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


OPTIONAL_SPEC_KIT_TEMPLATE_ASSETS = (
    TemplateAsset(
        template_path=Path("scaffold/target-repo/.codex/skills/spec-implement-bridge/SKILL.md"),
        destination=Path(".codex/skills/spec-implement-bridge/SKILL.md"),
    ),
    TemplateAsset(
        template_path=Path("scaffold/target-repo/.codex/skills/spec-sync-check/SKILL.md"),
        destination=Path(".codex/skills/spec-sync-check/SKILL.md"),
    ),
    TemplateAsset(
        template_path=Path("scaffold/target-repo/.codex/skills/spec-review-bridge/SKILL.md"),
        destination=Path(".codex/skills/spec-review-bridge/SKILL.md"),
    ),
)


OPTIONAL_UTILITY_HARNESS_COPY_ASSETS = (
    CopyAsset(
        source_path=Path("scaffold/target-repo/requirements-codex.txt"),
        destination=Path("requirements-codex.txt"),
    ),
    CopyAsset(
        source_path=Path("scaffold/target-repo/requirements-codex-minimal.txt"),
        destination=Path("requirements-codex-minimal.txt"),
    ),
    CopyAsset(
        source_path=Path("scaffold/target-repo/requirements-codex-readers.txt"),
        destination=Path("requirements-codex-readers.txt"),
    ),
    CopyAsset(
        source_path=Path("scaffold/target-repo/requirements-codex-analysis.txt"),
        destination=Path("requirements-codex-analysis.txt"),
    ),
    CopyAsset(
        source_path=Path("scaffold/target-repo/requirements-codex-cli.txt"),
        destination=Path("requirements-codex-cli.txt"),
    ),
    CopyAsset(
        source_path=Path("scaffold/target-repo/tools/ai/inspect_repo.py"),
        destination=Path("tools/ai/inspect_repo.py"),
    ),
    CopyAsset(
        source_path=Path("scaffold/target-repo/tools/ai/read_any.py"),
        destination=Path("tools/ai/read_any.py"),
    ),
    CopyAsset(
        source_path=Path("scaffold/target-repo/tools/ai/summarize_tree.py"),
        destination=Path("tools/ai/summarize_tree.py"),
    ),
    CopyAsset(
        source_path=Path("scaffold/target-repo/tools/ai/run_checks.py"),
        destination=Path("tools/ai/run_checks.py"),
    ),
    CopyAsset(
        source_path=Path("scaffold/target-repo/docs/ai/utility-harness.md"),
        destination=Path("docs/ai/utility-harness.md"),
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
        source_path=Path("scripts/spec_kit_bridge.py"),
        destination=Path("scripts/spec_kit_bridge.py"),
    ),
    CopyAsset(
        source_path=Path("scripts/utility_harness.py"),
        destination=Path("scripts/utility_harness.py"),
    ),
    CopyAsset(
        source_path=Path("scripts/enhancer_validator.py"),
        destination=Path("scripts/enhancer_validator.py"),
    ),
)
