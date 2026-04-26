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
        Launch `install_enhancer.bat` or inspect `scripts/install_enhancer_gui.py`.
        Read [docs/ai/migration-v3.md](docs/ai/migration-v3.md) before upgrading existing installs.
        See [docs/ai/roadmap.md](docs/ai/roadmap.md) for the next planned evolution.
        """,
        "AGENTS.md": f"""
        # Codex Enhancer

        Run `{CHECK_COMMAND}` and `{TEST_COMMAND}`.
        Use `install_enhancer.bat` for the Windows GUI installer.
        See [docs/ai/roadmap.md](docs/ai/roadmap.md) for the enhancer roadmap.

        See [docs/ai/architecture.md](docs/ai/architecture.md),
        [docs/ai/code-review.md](docs/ai/code-review.md),
        [docs/ai/migration-v3.md](docs/ai/migration-v3.md),
        [.codex/skills/](.codex/skills/), and [tests/](tests/).
        """,
        "install_enhancer.bat": """
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
        """,
        "docs/ai/migration-v3.md": """
        # V3 Migration Notes

        Use `--inspect-install`, `--upgrade-enhancer`, `--manage-packs`,
        and `--refresh-generated`.
        """,
        "docs/ai/roadmap.md": """
        # Codex Enhancer Roadmap

        Optional stack packs live here.
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
        "scripts/enhancer_spec.py": """
        # placeholder enhancer spec for fixture
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
        "tests/test_install_enhancer.py": """
        # placeholder installer test file for fixture
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
        "scaffold/target-repo/.codex/skills/adapt-enhancer/SKILL.md": """
        ---
        name: adapt-enhancer
        description: Adapt this workflow layer into a real repository. Use when inherited enhancer guidance still needs repo-specific replacement.
        ---

        # Adapt

        ## Do not use
        - Do not use once adaptation is complete.
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
