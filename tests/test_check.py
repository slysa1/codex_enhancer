from __future__ import annotations

import shutil
import textwrap
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from scripts import check
from scripts.enhancer_spec import CHECK_COMMAND, TEST_COMMAND


TEMP_ROOT = Path(__file__).resolve().parent / "_tmp"


def write_file(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def build_valid_repo(root: Path, missing: set[str] | None = None) -> None:
    missing = missing or set()
    files = {
        ".gitignore": "__pycache__/\n*.py[cod]\ntests/_tmp/\n",
        "README.md": f"""
        # Codex Enhancer

        See [AGENTS.md](AGENTS.md).

        Run `{CHECK_COMMAND}` and `{TEST_COMMAND}`.
        Use `pip install -e .` for local CLI packaging.
        Build distributable artifacts with `python -m build`.
        Run `python scripts/codex_enhancer_cli.py list-packs` or `codex-enhancer.bat`.
        Preview bundled installs with `--with-spec-kit`.
        Run `python scripts/codex_enhancer_cli.py spec-report ../repo`,
        `python scripts/codex_enhancer_cli.py spec-sync ../repo --changed src/app.py`,
        and `python scripts/codex_enhancer_cli.py bridge ../repo --attach-spec-kit`.
        Launch `install_enhancer.bat` or inspect `scripts/install_enhancer_gui.py`.
        Read [docs/ai/migration-v3.md](docs/ai/migration-v3.md) before upgrading existing installs.
        See [docs/ai/roadmap.md](docs/ai/roadmap.md) for the next planned evolution.
        See [docs/ai/release.md](docs/ai/release.md) before building packages.
        See [docs/ai/utility-harness.md](docs/ai/utility-harness.md) for the optional harness.
        Preview with `--utility-harness-mode install`.
        """,
        "AGENTS.md": f"""
        # Codex Enhancer

        Run `{CHECK_COMMAND}` and `{TEST_COMMAND}`.
        Local package metadata lives in `pyproject.toml` and package assets live in `codex_enhancer/package_assets.py`.
        Use `scripts/codex_enhancer_cli.py` and `codex-enhancer.bat` for the friendly command facade.
        Use `--with-spec-kit` only when the user explicitly wants official Spec Kit bootstrapped.
        Use `spec-sync` for read-only Spec Kit changed-path sync cues.
        Use `install_enhancer.bat` for the Windows GUI installer.
        See [docs/ai/roadmap.md](docs/ai/roadmap.md) for the enhancer roadmap.
        See [docs/ai/release.md](docs/ai/release.md) for package release checks.
        See [docs/ai/spec-kit-bridge.md](docs/ai/spec-kit-bridge.md) for the optional Spec Kit bridge.
        See [docs/ai/utility-harness.md](docs/ai/utility-harness.md) for the optional Utility Harness.
        The resolver lives in `scripts/utility_harness.py`.

        See [docs/ai/architecture.md](docs/ai/architecture.md),
        [docs/ai/code-review.md](docs/ai/code-review.md),
        [docs/ai/migration-v3.md](docs/ai/migration-v3.md),
        [.codex/skills/](.codex/skills/), and [tests/](tests/).
        """,
        "install_enhancer.bat": """
        @echo off
        """,
        "MANIFEST.in": """
        recursive-include codex_enhancer/assets/root *
        """,
        "pyproject.toml": """
        [build-system]
        requires = ["setuptools>=70"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "codex-enhancer"
        dynamic = ["version"]
        license = "GPL-3.0-or-later"
        license-files = ["LICENSE"]

        [project.scripts]
        codex-enhancer = "scripts.codex_enhancer_cli:main"

        [tool.setuptools]
        include-package-data = true

        [tool.setuptools.packages.find]
        include = ["scripts*", "codex_enhancer*"]

        [tool.setuptools.dynamic]
        version = { attr = "scripts.enhancer_spec.ENHANCER_VERSION" }
        """,
        "codex_enhancer/__init__.py": """
        # package marker
        """,
        "codex_enhancer/package_assets.py": """
        # package asset locator
        """,
        "codex-enhancer": """
        #!/usr/bin/env python3
        """,
        "codex-enhancer.bat": """
        @echo off
        """,
        "docs/ai/architecture.md": """
        # Architecture

        Repo-local workflow guidance only.
        """,
        "docs/ai/code-review.md": f"""
        # Review

        Run `{CHECK_COMMAND}` and `{TEST_COMMAND}`.
        See [docs/ai/migration-v3.md](migration-v3.md).
        See [docs/ai/release.md](release.md).
        See [docs/ai/spec-kit-bridge.md](spec-kit-bridge.md).
        See [docs/ai/utility-harness.md](utility-harness.md).
        """,
        "docs/ai/migration-v3.md": """
        # V3 Migration Notes

        Use `--inspect-install`, `--upgrade-enhancer`, `--manage-packs`,
        `--manage-spec-kit-bridge`, `--spec-kit-report`, `--spec-kit-sync-report`,
        and `--refresh-generated`.
        """,
        "docs/ai/release.md": """
        # Release Checklist

        Run `python -m build`, smoke `codex-enhancer list-packs`,
        keep requirements-codex.txt out of production dependencies, and
        mirror `codex_enhancer/assets/root/`.
        """,
        "docs/ai/roadmap.md": """
        # Codex Enhancer Roadmap

        Optional stack packs live here.
        """,
        "docs/ai/spec-kit-bridge.md": """
        # Spec Kit Bridge

        Treat official Spec Kit files as separately owned.
        Use spec-report and spec-sync for read-only summaries and bridge for bridge mode changes.
        """,
        "docs/ai/utility-harness.md": """
        # Codex Utility Harness

        Keep requirements-codex.txt out of production dependencies.
        """,
        ".codex/skills/AGENTS.md": """
        # Skills

        Keep skills narrow.
        """,
        ".codex/skills/plan-change/SKILL.md": """
        ---
        name: plan-change
        description: Plan repo changes before editing. Use when work spans multiple files.
        ---

        # Plan

        ## Do not use
        - Do not use for trivial edits.
        """,
        ".codex/skills/review-prep/SKILL.md": """
        ---
        name: review-prep
        description: Prepare a repo change for review. Use when a patch needs validation and review notes.
        ---

        # Review

        ## Do not use
        - Do not use before implementation stabilizes.
        """,
        ".codex/skills/adapt-enhancer/SKILL.md": """
        ---
        name: adapt-enhancer
        description: Adapt this workflow layer into another repository. Use when inherited enhancer guidance still needs repo-specific replacement.
        ---

        # Adapt

        ## Do not use
        - Do not use when the repo guidance is already repo specific.
        """,
        "scripts/__init__.py": '"""Repository-local Python helpers for Codex Enhancer."""\n',
        "scripts/check.py": """
        # placeholder script file for fixture
        """,
        "scripts/codex_enhancer_cli.py": """
        # placeholder command facade
        """,
        "scripts/enhancer_spec.py": """
        # placeholder enhancer spec for fixture
        """,
        "scripts/spec_kit_bridge.py": """
        # placeholder Spec Kit bridge helper for fixture
        """,
        "scripts/utility_harness.py": """
        # placeholder Utility Harness helper for fixture
        """,
        "scripts/enhancer_validator.py": """
        # placeholder validator for fixture
        """,
        "scripts/install_enhancer.py": """
        # placeholder installer for fixture
        """,
        "scripts/install_enhancer_gui.py": """
        # placeholder gui installer for fixture
        """,
        "scripts/stack_packs.py": """
        # placeholder stack pack loader for fixture
        """,
        "tests/test_check.py": """
        # placeholder test file for fixture
        """,
        "tests/test_codex_enhancer_cli.py": """
        # placeholder command facade test file
        """,
        "tests/test_install_enhancer.py": """
        # placeholder installer test file for fixture
        """,
        "tests/test_packaging.py": """
        # placeholder packaging test file for fixture
        """,
        "tests/test_spec_kit_bridge.py": """
        # placeholder Spec Kit bridge test file for fixture
        """,
        "tests/test_utility_harness.py": """
        # placeholder Utility Harness test file for fixture
        """,
        "tests/test_stack_packs.py": """
        # placeholder stack pack test file for fixture
        """,
        ".github/workflows/validate.yml": f"""
        name: validate
        on:
          push:
          pull_request:
        jobs:
          validate:
            runs-on: ubuntu-latest
            steps:
              - run: {CHECK_COMMAND}
              - run: {TEST_COMMAND}
        """,
        "scaffold/target-repo/AGENTS.md": """
        # {{REPO_NAME}}
        """,
        "scaffold/target-repo/docs/ai/architecture.md": """
        # Architecture template
        """,
        "scaffold/target-repo/docs/ai/code-review.md": """
        # Review template
        """,
        "scaffold/target-repo/docs/ai/spec-kit-bridge.md": """
        # Spec Kit Bridge template
        """,
        "scaffold/target-repo/docs/ai/utility-harness.md": """
        # Utility Harness template
        """,
        "scaffold/target-repo/.codex/skills/adapt-enhancer/SKILL.md": """
        ---
        name: adapt-enhancer
        description: Adapt this workflow layer into a real repository. Use when inherited enhancer guidance still needs repo-specific replacement.
        ---

        # Adapt

        ## Do not use
        - Do not use once adaptation is complete.
        """,
        "scaffold/target-repo/.codex/skills/spec-implement-bridge/SKILL.md": """
        ---
        name: spec-implement-bridge
        description: Implement code from existing Spec Kit feature artifacts. Use when a repo already has spec and plan artifacts for the active feature.
        ---

        ## Do not use
        - Do not use before official Spec Kit artifacts exist.
        """,
        "scaffold/target-repo/.codex/skills/spec-sync-check/SKILL.md": """
        ---
        name: spec-sync-check
        description: Compare changed code against existing Spec Kit artifacts. Use when code changed and you need to check for drift against spec or task artifacts.
        ---

        ## Do not use
        - Do not use when no Spec Kit feature artifacts exist.
        """,
        "scaffold/target-repo/.codex/skills/spec-review-bridge/SKILL.md": """
        ---
        name: spec-review-bridge
        description: Prepare review notes for Spec Kit-driven work. Use when a branch was implemented from Spec Kit artifacts and the handoff should summarize remaining drift.
        ---

        ## Do not use
        - Do not use when the change was not driven by Spec Kit artifacts.
        """,
        "scaffold/target-repo/requirements-codex.txt": """
        pathspec
        """,
        "scaffold/target-repo/tools/ai/inspect_repo.py": """
        # utility harness inspect repo tool
        """,
        "scaffold/target-repo/tools/ai/read_any.py": """
        # utility harness read any tool
        """,
        "scaffold/target-repo/tools/ai/summarize_tree.py": """
        # utility harness summarize tree tool
        """,
        "scaffold/target-repo/tools/ai/run_checks.py": """
        # utility harness run checks tool
        """,
        "scaffold/target-repo/scripts/check.py": """
        # template check wrapper
        """,
        "scaffold/target-repo/tests/test_check.py": """
        # template test file
        """,
        "scaffold/target-repo/.github/workflows/validate.yml": """
        name: validate
        """,
        "scaffold/stack-packs/monorepo-workspace/pack.toml": """
        schema_version = 1
        name = "monorepo-workspace"
        label = "Monorepo workspace"
        description = "Monorepo rules."
        version = "0.1.0"

        [discovery]
        any_files = ["pnpm-workspace.yaml"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 10

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/monorepo-workspace/fragments/agents-summary.md": """
        Monorepo summary.
        """,
        "scaffold/stack-packs/monorepo-workspace/fragments/stack-guidance.md": """
        Monorepo guidance.
        """,
        "scaffold/stack-packs/monorepo-workspace/fragments/review-notes.md": """
        Monorepo review notes.
        """,
        "scaffold/stack-packs/javascript-typescript-app/pack.toml": """
        schema_version = 1
        name = "javascript-typescript-app"
        label = "JavaScript / TypeScript app"
        description = "JavaScript or TypeScript app rules."
        version = "0.1.0"

        [discovery]
        all_files = ["package.json"]
        any_globs = ["tsconfig*.json"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 20

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/javascript-typescript-app/fragments/agents-summary.md": """
        JS summary.
        """,
        "scaffold/stack-packs/javascript-typescript-app/fragments/stack-guidance.md": """
        JS guidance.
        """,
        "scaffold/stack-packs/javascript-typescript-app/fragments/review-notes.md": """
        JS review notes.
        """,
        "scaffold/stack-packs/frontend-ui/pack.toml": """
        schema_version = 1
        name = "frontend-ui"
        label = "Frontend UI"
        description = "Frontend UI rules."
        version = "0.1.0"

        [discovery]
        any_globs = ["src/**/*.tsx"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 25

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/frontend-ui/fragments/agents-summary.md": """
        Frontend summary.
        """,
        "scaffold/stack-packs/frontend-ui/fragments/stack-guidance.md": """
        Frontend guidance.
        """,
        "scaffold/stack-packs/frontend-ui/fragments/review-notes.md": """
        Frontend review notes.
        """,
        "scaffold/stack-packs/python-service/pack.toml": """
        schema_version = 1
        name = "python-service"
        label = "Python service"
        description = "Python service rules."
        version = "0.1.0"

        [discovery]
        any_files = ["pyproject.toml"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 30

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/python-service/fragments/agents-summary.md": """
        Python summary.
        """,
        "scaffold/stack-packs/python-service/fragments/stack-guidance.md": """
        Python guidance.
        """,
        "scaffold/stack-packs/python-service/fragments/review-notes.md": """
        Python review notes.
        """,
        "scaffold/stack-packs/node-api-service/pack.toml": """
        schema_version = 1
        name = "node-api-service"
        label = "Node API service"
        description = "Node API service rules."
        version = "0.1.0"

        [discovery]
        all_files = ["package.json"]
        any_globs = ["src/server.*"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 35

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/node-api-service/fragments/agents-summary.md": """
        Node API summary.
        """,
        "scaffold/stack-packs/node-api-service/fragments/stack-guidance.md": """
        Node API guidance.
        """,
        "scaffold/stack-packs/node-api-service/fragments/review-notes.md": """
        Node API review notes.
        """,
        "scaffold/stack-packs/library-package/pack.toml": """
        schema_version = 1
        name = "library-package"
        label = "Library package"
        description = "Library package rules."
        version = "0.1.0"

        [discovery]
        all_files = ["package.json"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 40

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/library-package/fragments/agents-summary.md": """
        Library summary.
        """,
        "scaffold/stack-packs/library-package/fragments/stack-guidance.md": """
        Library guidance.
        """,
        "scaffold/stack-packs/library-package/fragments/review-notes.md": """
        Library review notes.
        """,
    }

    for relative_path, content in files.items():
        if relative_path in missing:
            continue
        write_file(root, relative_path, content)


@contextmanager
def repo_fixture() -> Path:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TEMP_ROOT / f"fixture_{uuid.uuid4().hex}"
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class ValidateTests(unittest.TestCase):
    def test_validate_passes_for_valid_repo(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)

            errors = check.validate(root)

            self.assertEqual(errors, [])

    def test_missing_required_file_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root, missing={"README.md"})

            errors = check.validate(root)

            self.assertTrue(any("Missing required file: README.md" in error for error in errors))

    def test_broken_markdown_link_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "docs/ai/architecture.md",
                """
                # Architecture

                See [missing](missing.md).
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any("Broken link in docs/ai/architecture.md -> missing.md" in error for error in errors)
            )

    def test_broken_markdown_link_includes_hint(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "docs/ai/architecture.md",
                """
                # Architecture

                See [missing](missing.md).
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "Broken link in docs/ai/architecture.md -> missing.md" in error
                    and "Hint:" in error
                    for error in errors
                )
            )

    def test_required_skill_is_enforced(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root, missing={".codex/skills/adapt-enhancer/SKILL.md"})

            errors = check.validate(root)

            self.assertTrue(
                any("Missing required skill: .codex/skills/adapt-enhancer/SKILL.md" in error for error in errors)
            )

    def test_skill_missing_do_not_use_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".codex/skills/review-prep/SKILL.md",
                """
                ---
                name: review-prep
                description: Prepare a repo change for review. Use when a patch needs validation and review notes.
                ---

                # Review
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    ".codex/skills/review-prep/SKILL.md must include a '## Do not use' section"
                    in error
                    for error in errors
                )
            )

    def test_skill_missing_do_not_use_includes_hint(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".codex/skills/review-prep/SKILL.md",
                """
                ---
                name: review-prep
                description: Prepare a repo change for review. Use when a patch needs validation and review notes.
                ---

                # Review
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    ".codex/skills/review-prep/SKILL.md must include a '## Do not use' section"
                    in error
                    and "Hint:" in error
                    for error in errors
                )
            )

    def test_workflow_command_drift_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".github/workflows/validate.yml",
                """
                name: validate
                jobs:
                  validate:
                    runs-on: ubuntu-latest
                    steps:
                      - run: python scripts/check.py
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    ".github/workflows/validate.yml is missing required text" in error
                    and TEST_COMMAND in error
                    for error in errors
                )
            )

    def test_workflow_command_drift_includes_hint(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".github/workflows/validate.yml",
                """
                name: validate
                jobs:
                  validate:
                    runs-on: ubuntu-latest
                    steps:
                      - run: python scripts/check.py
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    ".github/workflows/validate.yml is missing required text" in error
                    and "Hint:" in error
                    for error in errors
                )
            )


if __name__ == "__main__":
    unittest.main()
