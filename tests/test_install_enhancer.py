from __future__ import annotations

import io
import json
import shutil
import textwrap
import unittest
import uuid
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

from scripts import install_enhancer
from scripts.install_enhancer import apply_install_plan, build_install_plan, overwrite_paths
from scripts.install_enhancer_gui import build_plan_preview
from scripts.enhancer_spec import GITIGNORE_LINES, TARGET_VALIDATION_PROFILE
from scripts.enhancer_validator import validate as validate_profile


TEMP_ROOT = Path(__file__).resolve().parent / "_tmp"


def write_file(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


@contextmanager
def repo_fixture(prefix: str) -> Path:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TEMP_ROOT / f"{prefix}_{uuid.uuid4().hex}"
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_installer(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with redirect_stdout(output):
        exit_code = install_enhancer.main(arguments)
    return exit_code, output.getvalue()


class InstallEnhancerTests(unittest.TestCase):
    def test_file_target_is_rejected(self) -> None:
        with repo_fixture("install_file_target") as parent:
            target_file = parent / "not_a_repo.txt"
            target_file.write_text("hello", encoding="utf-8")

            exit_code, output = run_installer(["--target", str(target_file), "--mode", "auto"])

            self.assertEqual(exit_code, 1)
            self.assertIn("is not a directory", output)

    def test_dry_run_does_not_create_target(self) -> None:
        with repo_fixture("install_parent") as parent:
            target = parent / "new_repo"

            exit_code, output = run_installer(["--target", str(target), "--mode", "new"])

            self.assertEqual(exit_code, 0)
            self.assertFalse(target.exists())
            self.assertIn("Planned Codex Enhancer install", output)

    def test_new_repo_install_creates_expected_files(self) -> None:
        with repo_fixture("install_new") as target:
            install_target = target / "repo"

            exit_code, output = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Applying Codex Enhancer install", output)
            self.assertTrue((install_target / "AGENTS.md").exists())
            self.assertTrue((install_target / "docs/ai/architecture.md").exists())
            self.assertTrue((install_target / ".codex/skills/adapt-enhancer/SKILL.md").exists())
            self.assertTrue((install_target / "scripts/check.py").exists())
            self.assertTrue((install_target / "scripts/enhancer_spec.py").exists())
            self.assertTrue((install_target / "scripts/enhancer_validator.py").exists())
            self.assertTrue((install_target / "tests/test_check.py").exists())
            self.assertTrue((install_target / ".github/workflows/validate.yml").exists())

            gitignore = (install_target / ".gitignore").read_text(encoding="utf-8")
            for line in GITIGNORE_LINES:
                self.assertIn(line, gitignore)

    def test_new_repo_install_produces_valid_target_profile(self) -> None:
        with repo_fixture("install_valid") as target:
            install_target = target / "repo"

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )

            self.assertEqual(exit_code, 0)
            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)
            self.assertEqual(errors, [])

    def test_existing_repo_writes_proposals_for_conflicts(self) -> None:
        with repo_fixture("install_existing") as install_target:
            write_file(
                install_target,
                "AGENTS.md",
                """
                # Existing Repo

                Keep my original AGENTS.
                """,
            )
            write_file(
                install_target,
                "scripts/check.py",
                """
                print("existing check")
                """,
            )

            exit_code, output = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("proposal", output)
            self.assertEqual(
                (install_target / "AGENTS.md").read_text(encoding="utf-8").strip(),
                "# Existing Repo\n\nKeep my original AGENTS.",
            )
            self.assertTrue(
                (install_target / ".codex/enhancer-proposals/AGENTS.md").exists()
            )
            self.assertTrue(
                (install_target / ".codex/enhancer-proposals/scripts/check.py").exists()
            )

    def test_build_install_plan_tracks_proposals_and_overwrites(self) -> None:
        with repo_fixture("install_plan") as install_target:
            write_file(
                install_target,
                "AGENTS.md",
                """
                # Existing Repo
                """,
            )

            proposal_plan = build_install_plan(install_target, mode="existing", force=False)
            self.assertTrue(
                any(
                    item.action == "proposal"
                    and item.destination == Path("AGENTS.md")
                    for item in proposal_plan.writes
                )
            )

            overwrite_plan = build_install_plan(install_target, mode="existing", force=True)
            self.assertIn(Path("AGENTS.md"), overwrite_paths(overwrite_plan))

    def test_force_overwrite_updates_existing_agents(self) -> None:
        with repo_fixture("install_force") as install_target:
            write_file(
                install_target,
                "AGENTS.md",
                """
                # Existing Repo

                Keep my original AGENTS.
                """,
            )

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )

            self.assertEqual(exit_code, 0)
            content = (install_target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("This workflow layer was bootstrapped by Codex Enhancer.", content)

    def test_package_json_commands_are_discovered(self) -> None:
        with repo_fixture("install_package") as install_target:
            write_file(
                install_target,
                "package.json",
                json.dumps(
                    {
                        "name": "demo-repo",
                        "scripts": {
                            "build": "vite build",
                            "lint": "eslint .",
                            "test": "vitest run",
                            "dev": "vite",
                        },
                    }
                ),
            )

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )

            self.assertEqual(exit_code, 0)
            agents = (install_target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("`install`: `npm install`", agents)
            self.assertIn("`build`: `npm run build`", agents)
            self.assertIn("`lint`: `npm run lint`", agents)
            self.assertIn("`test`: `npm test`", agents)
            self.assertIn("`dev`: `npm run dev`", agents)

    def test_apply_install_plan_reports_progress(self) -> None:
        with repo_fixture("install_progress") as parent:
            install_target = parent / "repo"
            plan = build_install_plan(install_target, mode="new", force=False)
            events: list[tuple[int, int, str]] = []

            apply_install_plan(plan, progress_callback=lambda current, total, message: events.append((current, total, message)))

            self.assertGreaterEqual(len(events), 2)
            self.assertEqual(events[0], (0, len(plan.writes) + 1, "Preparing install..."))
            self.assertEqual(events[-1][0], events[-1][1])
            self.assertIn(".gitignore", events[-1][2])

    def test_gui_plan_preview_lists_overwrites(self) -> None:
        with repo_fixture("install_preview") as install_target:
            write_file(
                install_target,
                "AGENTS.md",
                """
                # Existing Repo
                """,
            )

            plan = build_install_plan(install_target, mode="existing", force=True)
            preview = build_plan_preview(plan)

            self.assertIn("Files to overwrite:", preview)
            self.assertIn("- AGENTS.md", preview)
            self.assertIn("After install:", preview)


if __name__ == "__main__":
    unittest.main()
