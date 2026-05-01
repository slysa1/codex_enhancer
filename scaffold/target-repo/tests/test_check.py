from __future__ import annotations

import shutil
import textwrap
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from scripts import check
from scripts.enhancer_spec import ENHANCER_MANIFEST_SCHEMA_VERSION, ENHANCER_VERSION


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
        [docs/ai/code-review.md](docs/ai/code-review.md), [docs/ai/spec-kit-bridge.md](docs/ai/spec-kit-bridge.md),
        [docs/ai/stack-guidance.md](docs/ai/stack-guidance.md),
        [.codex/enhancer/manifest.toml](.codex/enhancer/manifest.toml), [.codex/skills/](.codex/skills/),
        [tests/](tests/), and `adapt-enhancer`.

        ## Selected Stack Packs

        <!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs start -->
        - No stack packs are selected yet. Keep [docs/ai/stack-guidance.md](docs/ai/stack-guidance.md) and
          [.codex/enhancer/manifest.toml](.codex/enhancer/manifest.toml) aligned if pack selection changes later.
        <!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs end -->

        ## Spec Kit Bridge

        <!-- codex-enhancer:managed-section AGENTS.md:spec-kit-bridge start -->
        - Spec Kit bridge is off until this repo adopts official Spec Kit.
        - If `.specify/` or `specs/` appear, review [docs/ai/spec-kit-bridge.md](docs/ai/spec-kit-bridge.md).
        <!-- codex-enhancer:managed-section AGENTS.md:spec-kit-bridge end -->
        """,
        "docs/ai/architecture.md": """
        # Architecture

        Keep the workflow layer minimal and see [Spec Kit bridge](spec-kit-bridge.md),
        [stack guidance](stack-guidance.md), plus
        [.codex/enhancer/manifest.toml](../../.codex/enhancer/manifest.toml).
        """,
        "docs/ai/code-review.md": f"""
        # Review

        Run `python scripts/check.py` and `{TEST_COMMAND}`.
        Check [Spec Kit bridge](spec-kit-bridge.md), [stack guidance](stack-guidance.md), and
        [.codex/enhancer/manifest.toml](../../.codex/enhancer/manifest.toml).
        """,
        "docs/ai/spec-kit-bridge.md": """
        # Spec Kit Bridge

        Bridge mode: `off`.
        Bridge state: `absent`.
        Treat official Spec Kit files as separately owned.
        """,
        "docs/ai/stack-guidance.md": """
        # Stack Guidance

        No stack packs are selected yet.
        """,
        ".codex/skills/AGENTS.md": """
        # Skills

        Keep skills narrow.
        """,
        ".codex/enhancer/manifest.toml": f"""
        schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}
        enhancer_version = "{ENHANCER_VERSION}"
        selected_packs = []

        [lifecycle]
        state = "active"
        pack_selection = "manifest"
        managed_sections = ["AGENTS.md:selected-stack-packs", "AGENTS.md:spec-kit-bridge"]

        [generated_files]
        stack_guidance = "docs/ai/stack-guidance.md"
        spec_kit_bridge = "docs/ai/spec-kit-bridge.md"

        [managed_outputs]
        safe_to_regenerate = ["docs/ai/stack-guidance.md", "docs/ai/spec-kit-bridge.md", ".codex/enhancer/manifest.toml"]
        adapt_manually = ["AGENTS.md", "docs/ai/architecture.md", "docs/ai/code-review.md"]

        [integrations.spec_kit]
        mode = "off"
        state = "absent"
        managed_by = "spec-kit"
        available_commands = []
        detection_evidence = []

        [integrations.spec_kit.paths]
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

    def test_selected_pack_must_appear_in_stack_guidance(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".codex/enhancer/manifest.toml",
                f"""
                schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}
                enhancer_version = "{ENHANCER_VERSION}"
                selected_packs = ["python-service"]

                [lifecycle]
                state = "active"
                pack_selection = "manifest"
                managed_sections = ["AGENTS.md:selected-stack-packs", "AGENTS.md:spec-kit-bridge"]

                [generated_files]
                stack_guidance = "docs/ai/stack-guidance.md"
                spec_kit_bridge = "docs/ai/spec-kit-bridge.md"

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md", "docs/ai/spec-kit-bridge.md", ".codex/enhancer/manifest.toml"]
                adapt_manually = ["AGENTS.md", "docs/ai/architecture.md", "docs/ai/code-review.md"]

                [integrations.spec_kit]
                mode = "off"
                state = "absent"
                managed_by = "spec-kit"
                available_commands = []
                detection_evidence = []

                [integrations.spec_kit.paths]
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "docs/ai/stack-guidance.md is missing guidance for selected pack 'python-service'"
                    in error
                    for error in errors
                )
            )

    def test_selected_pack_must_appear_in_root_agents_summary(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".codex/enhancer/manifest.toml",
                f"""
                schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}
                enhancer_version = "{ENHANCER_VERSION}"
                selected_packs = ["python-service"]

                [lifecycle]
                state = "active"
                pack_selection = "manifest"
                managed_sections = ["AGENTS.md:selected-stack-packs", "AGENTS.md:spec-kit-bridge"]

                [generated_files]
                stack_guidance = "docs/ai/stack-guidance.md"
                spec_kit_bridge = "docs/ai/spec-kit-bridge.md"

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md", "docs/ai/spec-kit-bridge.md", ".codex/enhancer/manifest.toml"]
                adapt_manually = ["AGENTS.md", "docs/ai/architecture.md", "docs/ai/code-review.md"]

                [integrations.spec_kit]
                mode = "off"
                state = "absent"
                managed_by = "spec-kit"
                available_commands = []
                detection_evidence = []

                [integrations.spec_kit.paths]
                """,
            )
            write_file(
                root,
                "docs/ai/stack-guidance.md",
                """
                # Stack Guidance

                Selected packs: `python-service`

                ## Python service

                Pack id: `python-service`
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "AGENTS.md is missing a root summary for selected pack 'python-service'"
                    in error
                    for error in errors
                )
            )

    def test_manifest_must_record_safe_to_regenerate_outputs(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".codex/enhancer/manifest.toml",
                f"""
                schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}
                enhancer_version = "{ENHANCER_VERSION}"
                selected_packs = []

                [lifecycle]
                state = "active"
                pack_selection = "manifest"
                managed_sections = ["AGENTS.md:selected-stack-packs", "AGENTS.md:spec-kit-bridge"]

                [generated_files]
                stack_guidance = "docs/ai/stack-guidance.md"
                spec_kit_bridge = "docs/ai/spec-kit-bridge.md"

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md"]
                adapt_manually = ["AGENTS.md"]

                [integrations.spec_kit]
                mode = "off"
                state = "absent"
                managed_by = "spec-kit"
                available_commands = []
                detection_evidence = []

                [integrations.spec_kit.paths]
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "managed_outputs.safe_to_regenerate" in error
                    for error in errors
                )
            )


if __name__ == "__main__":
    unittest.main()
