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
from scripts.install_enhancer import (
    apply_install_plan,
    build_install_plan,
    build_overwrite_confirmation_message,
    format_next_steps,
    overwrite_paths,
)
from scripts.install_enhancer_gui import build_completion_message, build_plan_preview
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

    def test_list_packs_without_target_prints_available_pack_names(self) -> None:
        exit_code, output = run_installer(["--list-packs"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Available stack packs:", output)
        self.assertIn("monorepo-workspace", output)
        self.assertIn("javascript-typescript-app", output)
        self.assertIn("python-service", output)

    def test_dry_run_does_not_create_target(self) -> None:
        with repo_fixture("install_parent") as parent:
            target = parent / "new_repo"

            exit_code, output = run_installer(["--target", str(target), "--mode", "new"])

            self.assertEqual(exit_code, 0)
            self.assertFalse(target.exists())
            self.assertIn("Planned Codex Enhancer install", output)

    def test_dry_run_reports_detected_stack_packs(self) -> None:
        with repo_fixture("install_pack_preview") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            exit_code, output = run_installer(["--target", str(install_target), "--mode", "existing"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Stack pack selection:", output)
            self.assertIn(
                "javascript-typescript-app: available as recommended but not selected",
                output,
            )

    def test_use_recommended_packs_selects_detected_recommendations(self) -> None:
        with repo_fixture("install_recommended") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--use-recommended-packs",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn(
                "javascript-typescript-app: selected from recommended detection",
                output,
            )
            self.assertIn("After install:", output)
            self.assertIn(
                "Review `AGENTS.md` and `docs/ai/stack-guidance.md` for selected packs: `javascript-typescript-app`.",
                output,
            )
            self.assertIn("Next step:", output)
            self.assertIn("Re-run this command with --write", output)

    def test_explicit_pack_selects_undetected_pack(self) -> None:
        with repo_fixture("install_explicit_pack") as install_target:
            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "auto",
                    "--pack",
                    "python-service",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn(
                "python-service: selected explicitly via --pack",
                output,
            )
            self.assertIn('selected_packs = ["python-service"]', output)

    def test_no_pack_overrides_recommended_selection(self) -> None:
        with repo_fixture("install_no_pack") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--use-recommended-packs",
                    "--no-pack",
                    "javascript-typescript-app",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn(
                "javascript-typescript-app: skipped explicitly via --no-pack",
                output,
            )

    def test_unknown_pack_name_is_rejected(self) -> None:
        with repo_fixture("install_unknown_pack") as install_target:
            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "auto",
                    "--pack",
                    "missing-pack",
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("Unknown stack pack name(s): missing-pack", output)

    def test_conflicting_pack_selection_is_rejected(self) -> None:
        with repo_fixture("install_conflicting_pack") as install_target:
            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "auto",
                    "--pack",
                    "python-service",
                    "--no-pack",
                    "python-service",
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("Conflicting stack-pack selection for: python-service", output)

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
            self.assertTrue((install_target / "docs/ai/stack-guidance.md").exists())
            self.assertTrue((install_target / ".codex/skills/adapt-enhancer/SKILL.md").exists())
            self.assertTrue((install_target / ".codex/enhancer/manifest.toml").exists())
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

    def test_dry_run_reports_conflict_severity_for_critical_and_standard_files(self) -> None:
        with repo_fixture("install_conflict_severity") as install_target:
            write_file(install_target, "AGENTS.md", "# Existing Repo\n")
            write_file(
                install_target,
                ".codex/skills/plan-change/SKILL.md",
                """
                ---
                name: plan-change
                description: Existing custom skill.
                ---

                ## Do not use
                - Existing repo rule.
                """,
            )

            exit_code, output = run_installer(
                ["--target", str(install_target), "--mode", "existing"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Conflict severity:", output)
            self.assertIn("Critical proposal files: `AGENTS.md`", output)
            self.assertIn(
                "Standard proposal files: `.codex/skills/plan-change/SKILL.md`",
                output,
            )
            self.assertIn(
                "Proposal mode keeps the listed critical files in place",
                output,
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

    def test_build_install_plan_tracks_selected_pack_names_in_manifest_preview(self) -> None:
        with repo_fixture("install_manifest_selection") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            plan = build_install_plan(
                install_target,
                mode="existing",
                use_recommended_packs=True,
            )

            self.assertIn(
                'selected_packs = ["javascript-typescript-app"]',
                plan.manifest_preview,
            )

    def test_selected_pack_is_rendered_into_installed_target_outputs(self) -> None:
        with repo_fixture("install_selected_pack_outputs") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--use-recommended-packs",
                    "--write",
                    "--force",
                ]
            )

            self.assertEqual(exit_code, 0)
            agents = (install_target / "AGENTS.md").read_text(encoding="utf-8")
            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            stack_guidance = (install_target / "docs/ai/stack-guidance.md").read_text(encoding="utf-8")

            self.assertIn("Selected packs: `javascript-typescript-app`", agents)
            self.assertIn("`javascript-typescript-app` (JavaScript / TypeScript app):", agents)
            self.assertIn('selected_packs = ["javascript-typescript-app"]', manifest)
            self.assertIn("Pack id: `javascript-typescript-app`", stack_guidance)
            self.assertIn("### Review Notes", stack_guidance)

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

    def test_gui_plan_preview_labels_critical_overwrites(self) -> None:
        with repo_fixture("install_preview_conflicts") as install_target:
            write_file(install_target, "AGENTS.md", "# Existing Repo\n")
            write_file(
                install_target,
                ".codex/skills/plan-change/SKILL.md",
                """
                ---
                name: plan-change
                description: Existing custom skill.
                ---

                ## Do not use
                - Existing repo rule.
                """,
            )

            plan = build_install_plan(install_target, mode="existing", force=True)
            preview = build_plan_preview(plan)

            self.assertIn("Conflict severity:", preview)
            self.assertIn("Critical overwrite files: `AGENTS.md`", preview)
            self.assertIn(
                "Standard overwrite files: `.codex/skills/plan-change/SKILL.md`",
                preview,
            )
            self.assertIn(
                "Force mode will replace the listed critical enhancer-owned files.",
                preview,
            )

    def test_gui_plan_preview_lists_selected_stack_packs(self) -> None:
        with repo_fixture("install_preview_packs") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            plan = build_install_plan(
                install_target,
                mode="existing",
                use_recommended_packs=True,
            )
            preview = build_plan_preview(plan)

            self.assertIn("Stack packs:", preview)
            self.assertIn(
                "JavaScript / TypeScript app (`javascript-typescript-app`): selected",
                preview,
            )
            self.assertIn("Manifest selected packs: `javascript-typescript-app`", preview)
            self.assertIn(
                "Review `AGENTS.md` and `docs/ai/stack-guidance.md` for selected packs: `javascript-typescript-app`.",
                preview,
            )

    def test_next_steps_include_pack_aware_follow_up_when_packs_are_selected(self) -> None:
        with repo_fixture("install_next_steps_pack") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            plan = build_install_plan(
                install_target,
                mode="existing",
                use_recommended_packs=True,
            )
            next_steps = format_next_steps(plan, write=True)

            self.assertIn(
                "- Review `AGENTS.md` and `docs/ai/stack-guidance.md` for selected packs: `javascript-typescript-app`.",
                next_steps,
            )
            self.assertTrue(
                any("package manager and lockfile" in line for line in next_steps)
            )

    def test_gui_completion_message_lists_selected_stack_packs(self) -> None:
        with repo_fixture("install_completion_packs") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            plan = build_install_plan(
                install_target,
                mode="existing",
                use_recommended_packs=True,
            )
            message = build_completion_message(plan)

            self.assertIn("Codex Enhancer was installed successfully.", message)
            self.assertIn(f"Target folder: {install_target.resolve()}", message)
            self.assertIn("Installed stack packs:", message)
            self.assertIn("- javascript-typescript-app", message)

    def test_gui_completion_message_reports_when_no_packs_are_selected(self) -> None:
        with repo_fixture("install_completion_none") as install_target:
            plan = build_install_plan(
                install_target,
                mode="new",
            )
            message = build_completion_message(plan)

            self.assertIn("Installed stack packs:", message)
            self.assertIn("- none selected", message)

    def test_build_overwrite_confirmation_message_lists_critical_files(self) -> None:
        with repo_fixture("install_confirm_message") as install_target:
            write_file(install_target, "AGENTS.md", "# Existing Repo\n")

            plan = build_install_plan(install_target, mode="existing", force=True)
            message = build_overwrite_confirmation_message(plan)

            self.assertIn("Confirm the overwrite list before running the installer.", message)
            self.assertIn("Critical enhancer-owned files will be replaced:", message)
            self.assertIn("- AGENTS.md", message)


if __name__ == "__main__":
    unittest.main()
