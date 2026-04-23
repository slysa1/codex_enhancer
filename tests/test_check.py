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
        """,
        "AGENTS.md": f"""
        # Codex Enhancer

        Run `{CHECK_COMMAND}` and `{TEST_COMMAND}`.
        Use `install_enhancer.bat` for the Windows GUI installer.

        See [docs/ai/architecture.md](docs/ai/architecture.md),
        [docs/ai/code-review.md](docs/ai/code-review.md),
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
        "tests/test_check.py": """
        # placeholder test file for fixture
        """,
        "tests/test_install_enhancer.py": """
        # placeholder installer test file for fixture
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
