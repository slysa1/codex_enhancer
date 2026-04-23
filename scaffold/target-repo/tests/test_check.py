from __future__ import annotations

import shutil
import textwrap
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from scripts import check


TEST_COMMAND = 'python -m unittest discover -s tests -p "test_*.py" -v'
TEMP_ROOT = Path(__file__).resolve().parent / "_tmp"


def write_file(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def build_valid_repo(root: Path, missing: set[str] | None = None) -> None:
    missing = missing or set()
    files = {
        "AGENTS.md": f"""
        # Example Repo

        Run `python scripts/check.py` and `{TEST_COMMAND}`.

        See [docs/ai/architecture.md](docs/ai/architecture.md),
        [docs/ai/code-review.md](docs/ai/code-review.md),
        [.codex/skills/](.codex/skills/), [tests/](tests/), and `adapt-enhancer`.
        """,
        "docs/ai/architecture.md": """
        # Architecture

        Keep the workflow layer minimal.
        """,
        "docs/ai/code-review.md": f"""
        # Review

        Run `python scripts/check.py` and `{TEST_COMMAND}`.
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
        description: Adapt this workflow layer into a real repository. Use when inherited enhancer guidance still needs repo-specific replacement.
        ---

        # Adapt

        ## Do not use
        - Do not use when the repo guidance is already repo specific.
        """,
        "scripts/check.py": """
        # placeholder check wrapper for fixture
        """,
        "scripts/enhancer_spec.py": """
        # placeholder enhancer spec for fixture
        """,
        "scripts/enhancer_validator.py": """
        # placeholder validator for fixture
        """,
        "tests/test_check.py": """
        # placeholder test file for fixture
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
              - run: python scripts/check.py
              - run: {TEST_COMMAND}
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
            build_valid_repo(root, missing={"AGENTS.md"})

            errors = check.validate(root)

            self.assertTrue(any("Missing required file: AGENTS.md" in error for error in errors))

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

    def test_required_skill_is_enforced(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root, missing={".codex/skills/adapt-enhancer/SKILL.md"})

            errors = check.validate(root)

            self.assertTrue(
                any("Missing required skill: .codex/skills/adapt-enhancer/SKILL.md" in error for error in errors)
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
                    and "python -m unittest discover -s tests -p \"test_*.py\" -v" in error
                    for error in errors
                )
            )


if __name__ == "__main__":
    unittest.main()
