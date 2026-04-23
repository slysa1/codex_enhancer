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
    build_upgrade_plan,
    format_next_steps,
    overwrite_paths,
)
from scripts.install_enhancer_gui import build_completion_message, build_plan_preview
from scripts.enhancer_spec import ENHANCER_VERSION, GITIGNORE_LINES, TARGET_VALIDATION_PROFILE
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

    def test_inspect_install_reports_repo_without_enhancer(self) -> None:
        with repo_fixture("inspect_missing") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(["--target", str(install_target), "--inspect-install"])

            self.assertEqual(exit_code, 0)
            self.assertIn(f"Source enhancer version: `{ENHANCER_VERSION}`", output)
            self.assertIn("Target enhancer version: not installed", output)
            self.assertIn("no enhancer install was found", output)

    def test_inspect_install_reports_current_target_state(self) -> None:
        with repo_fixture("inspect_current") as install_target:
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

            exit_code, output = run_installer(["--target", str(install_target), "--inspect-install"])

            self.assertEqual(exit_code, 0)
            self.assertIn(f"Source enhancer version: `{ENHANCER_VERSION}`", output)
            self.assertIn(f"Target enhancer version: `{ENHANCER_VERSION}`", output)
            self.assertIn("Status: target install matches the current source version.", output)
            self.assertIn("Selected packs: `javascript-typescript-app`", output)

    def test_inspect_install_reports_older_target_version(self) -> None:
        with repo_fixture("inspect_outdated") as install_target:
            write_file(
                install_target,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = 1
                enhancer_version = "2"
                selected_packs = ["python-service"]

                [generated_files]
                stack_guidance = "docs/ai/stack-guidance.md"

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md", ".codex/enhancer/manifest.toml"]
                adapt_manually = ["AGENTS.md"]
                """,
            )

            exit_code, output = run_installer(["--target", str(install_target), "--inspect-install"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Target enhancer version: `2`", output)
            self.assertIn("Status: target install is older than the current source version.", output)
            self.assertIn("Selected packs: `python-service`", output)

    def test_inspect_install_rejects_write_and_force_flags(self) -> None:
        with repo_fixture("inspect_invalid") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--inspect-install", "--write"]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("cannot be combined", output)

    def test_upgrade_enhancer_requires_existing_install(self) -> None:
        with repo_fixture("upgrade_missing") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(["--target", str(install_target), "--upgrade-enhancer"])

            self.assertEqual(exit_code, 1)
            self.assertIn("does not contain an enhancer install yet", output)

    def test_upgrade_enhancer_rejects_force_and_pack_flags(self) -> None:
        with repo_fixture("upgrade_invalid") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--upgrade-enhancer", "--force"]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("cannot be combined", output)

            exit_code, output = run_installer(
                ["--target", str(install_target), "--upgrade-enhancer", "--pack", "python-service"]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("cannot be combined", output)

    def test_upgrade_enhancer_reports_no_drift_for_current_install(self) -> None:
        with repo_fixture("upgrade_current") as install_target:
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

            exit_code, output = run_installer(["--target", str(install_target), "--upgrade-enhancer"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Planned Codex Enhancer upgrade reconcile plan", output)
            self.assertIn("Upgrade drift: none.", output)
            self.assertIn("Upgrade reconcile keeps the installed pack selection", output)
            self.assertIn("`--upgrade-enhancer --write`", output)

    def test_upgrade_enhancer_write_is_noop_for_current_install(self) -> None:
        with repo_fixture("upgrade_apply_current") as install_target:
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

            exit_code, output = run_installer(
                ["--target", str(install_target), "--upgrade-enhancer", "--write"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Applying Codex Enhancer upgrade reconcile plan", output)
            self.assertIn("Upgrade drift: none.", output)
            self.assertIn("No reconcile changes were needed", output)
            self.assertFalse((install_target / ".codex/enhancer-proposals").exists())

    def test_upgrade_enhancer_groups_outdated_install_changes(self) -> None:
        with repo_fixture("upgrade_outdated") as install_target:
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

            write_file(install_target, "docs/ai/stack-guidance.md", "# stale guidance\n")
            write_file(install_target, ".codex/skills/plan-change/SKILL.md", "# stale skill\n")
            write_file(install_target, "AGENTS.md", "# Custom Repo\n")
            write_file(
                install_target,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = 1
                enhancer_version = "2"
                selected_packs = ["javascript-typescript-app"]

                [generated_files]
                stack_guidance = "docs/ai/stack-guidance.md"

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md", ".codex/enhancer/manifest.toml"]
                adapt_manually = ["AGENTS.md"]
                """,
            )

            exit_code, output = run_installer(["--target", str(install_target), "--upgrade-enhancer"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Managed generated outputs:", output)
            self.assertIn("- overwrite: docs/ai/stack-guidance.md", output)
            self.assertIn("- overwrite: .codex/enhancer/manifest.toml", output)
            self.assertIn("Source-aligned direct copies:", output)
            self.assertIn(".codex/skills/plan-change/SKILL.md", output)
            self.assertIn("Repo-owned proposal files:", output)
            self.assertIn(".codex/enhancer-proposals/AGENTS.md", output)

    def test_upgrade_enhancer_write_applies_outdated_install_changes(self) -> None:
        with repo_fixture("upgrade_apply_outdated") as install_target:
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

            write_file(install_target, "docs/ai/stack-guidance.md", "# stale guidance\n")
            write_file(install_target, ".codex/skills/plan-change/SKILL.md", "# stale skill\n")
            write_file(install_target, "AGENTS.md", "# Custom Repo\n")
            write_file(
                install_target,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = 1
                enhancer_version = "2"
                selected_packs = ["javascript-typescript-app"]

                [generated_files]
                stack_guidance = "docs/ai/stack-guidance.md"

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md", ".codex/enhancer/manifest.toml"]
                adapt_manually = ["AGENTS.md"]
                """,
            )

            exit_code, output = run_installer(
                ["--target", str(install_target), "--upgrade-enhancer", "--write"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Applying Codex Enhancer upgrade reconcile plan", output)
            self.assertIn(
                "Review the proposal files under `.codex/enhancer-proposals/`",
                output,
            )
            self.assertNotEqual(
                (install_target / "docs/ai/stack-guidance.md").read_text(encoding="utf-8"),
                "# stale guidance\n",
            )
            self.assertNotEqual(
                (install_target / ".codex/skills/plan-change/SKILL.md").read_text(encoding="utf-8"),
                "# stale skill\n",
            )
            self.assertEqual(
                (install_target / "AGENTS.md").read_text(encoding="utf-8"),
                "# Custom Repo\n",
            )
            self.assertTrue((install_target / ".codex/enhancer-proposals/AGENTS.md").exists())
            self.assertIn(
                f'enhancer_version = "{ENHANCER_VERSION}"',
                (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8"),
            )

    def test_upgrade_enhancer_plans_creates_for_partially_missing_install(self) -> None:
        with repo_fixture("upgrade_missing_files") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")
            write_file(
                install_target,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = 1
                enhancer_version = "2.0"
                selected_packs = ["javascript-typescript-app"]

                [generated_files]
                stack_guidance = "docs/ai/stack-guidance.md"

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md", ".codex/enhancer/manifest.toml"]
                adapt_manually = ["AGENTS.md"]
                """,
            )

            exit_code, output = run_installer(["--target", str(install_target), "--upgrade-enhancer"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Managed generated outputs:", output)
            self.assertIn("- create: docs/ai/stack-guidance.md", output)
            self.assertIn("Source-aligned direct copies:", output)
            self.assertIn("- create: .codex/skills/review-prep/SKILL.md", output)

    def test_dry_run_does_not_create_target(self) -> None:
        with repo_fixture("install_parent") as parent:
            target = parent / "new_repo"

            exit_code, output = run_installer(["--target", str(target), "--mode", "new"])

            self.assertEqual(exit_code, 0)
            self.assertFalse(target.exists())
            self.assertIn("Planned Codex Enhancer install", output)
            self.assertIn("Output ownership:", output)
            self.assertIn(
                "Safe to regenerate later: `docs/ai/stack-guidance.md`, `.codex/enhancer/manifest.toml`",
                output,
            )

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

    def test_refresh_generated_requires_existing_installed_target(self) -> None:
        with repo_fixture("refresh_missing_manifest") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--refresh-generated"]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("does not contain .codex/enhancer/manifest.toml", output)

    def test_refresh_generated_rejects_force_and_pack_flags(self) -> None:
        with repo_fixture("refresh_invalid_flags") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--refresh-generated", "--force"]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("does not accept --force", output)

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--refresh-generated",
                    "--pack",
                    "python-service",
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("do not combine it with pack-selection flags", output)

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

    def test_target_validation_requires_manifest_enhancer_version(self) -> None:
        with repo_fixture("install_manifest_version") as target:
            install_target = target / "repo"

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )

            self.assertEqual(exit_code, 0)

            manifest_path = install_target / ".codex/enhancer/manifest.toml"
            manifest_text = manifest_path.read_text(encoding="utf-8").replace(
                f'enhancer_version = "{ENHANCER_VERSION}"\n',
                "",
            )
            manifest_path.write_text(manifest_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any("must define enhancer_version as a non-empty string" in error for error in errors)
            )

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
            self.assertIn(f'enhancer_version = "{ENHANCER_VERSION}"', manifest)
            self.assertIn("`javascript-typescript-app` (JavaScript / TypeScript app):", agents)
            self.assertIn('selected_packs = ["javascript-typescript-app"]', manifest)
            self.assertIn(
                'safe_to_regenerate = ["docs/ai/stack-guidance.md", ".codex/enhancer/manifest.toml"]',
                manifest,
            )
            self.assertIn('adapt_manually = ["AGENTS.md"', manifest)
            self.assertIn("Pack id: `javascript-typescript-app`", stack_guidance)
            self.assertIn("### Review Notes", stack_guidance)

    def test_refresh_generated_dry_run_only_updates_safe_outputs(self) -> None:
        with repo_fixture("refresh_dry_run") as install_target:
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )
            self.assertEqual(exit_code, 0)

            exit_code, output = run_installer(
                ["--target", str(install_target), "--refresh-generated"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Planned Codex Enhancer generated-output refresh", output)
            self.assertIn("After refresh:", output)
            self.assertIn(
                "Stack guidance and the pack manifest will be regenerated from the existing target manifest.",
                output,
            )
            self.assertIn("- overwrite: docs/ai/stack-guidance.md", output)
            self.assertIn("- overwrite: .codex/enhancer/manifest.toml", output)
            self.assertIn("Manual scaffold files stay untouched during refresh.", output)
            self.assertNotIn("- overwrite: AGENTS.md", output)
            self.assertNotIn("- merge: .gitignore", output)

    def test_refresh_generated_write_updates_generated_outputs_without_touching_agents(self) -> None:
        with repo_fixture("refresh_write") as install_target:
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

            agents_path = install_target / "AGENTS.md"
            guidance_path = install_target / "docs/ai/stack-guidance.md"

            agents_path.write_text(
                agents_path.read_text(encoding="utf-8") + "\nCustom manual note.\n",
                encoding="utf-8",
            )
            guidance_path.write_text("# stale guidance\n", encoding="utf-8")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--refresh-generated", "--write"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Applying Codex Enhancer generated-output refresh", output)
            self.assertIn("selected from existing target manifest", output)
            self.assertIn("Refreshed stack-pack guidance for: `javascript-typescript-app`.", output)
            self.assertIn("Custom manual note.", agents_path.read_text(encoding="utf-8"))
            refreshed_guidance = guidance_path.read_text(encoding="utf-8")
            self.assertNotIn("# stale guidance", refreshed_guidance)
            self.assertIn("Pack id: `javascript-typescript-app`", refreshed_guidance)

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

            self.assertIn("Output ownership:", preview)
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

    def test_gui_refresh_preview_uses_refresh_wording(self) -> None:
        with repo_fixture("install_preview_refresh") as install_target:
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

            plan = build_install_plan(install_target, refresh_generated=True)
            preview = build_plan_preview(plan)

            self.assertIn("Operation: Refresh managed outputs", preview)
            self.assertIn("Repo mode: existing", preview)
            self.assertIn(
                "Refresh behavior: overwrite only enhancer-managed generated outputs.",
                preview,
            )
            self.assertIn("After refresh:", preview)
            self.assertNotIn(".gitignore update:", preview)
            self.assertNotIn("Conflict severity:", preview)
            self.assertIn("Manifest selected packs: `javascript-typescript-app`", preview)

    def test_gui_upgrade_preview_uses_upgrade_wording(self) -> None:
        with repo_fixture("install_preview_upgrade") as install_target:
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

            write_file(install_target, "docs/ai/stack-guidance.md", "# stale guidance\n")
            write_file(install_target, ".codex/skills/plan-change/SKILL.md", "# stale skill\n")
            write_file(install_target, "AGENTS.md", "# Custom Repo\n")

            plan = build_upgrade_plan(install_target)
            preview = build_plan_preview(plan)

            self.assertIn("Operation: Upgrade or reconcile existing install", preview)
            self.assertIn(
                "Upgrade behavior: overwrite tracked managed outputs and source-aligned copies; write repo-owned scaffold drift as proposals.",
                preview,
            )
            self.assertIn("Managed generated outputs:", preview)
            self.assertIn("Source-aligned direct copies:", preview)
            self.assertIn("Repo-owned proposal files:", preview)
            self.assertIn("After upgrade:", preview)
            self.assertIn(
                "Review the proposal files under `.codex/enhancer-proposals/`",
                preview,
            )
            self.assertIn("Manifest selected packs: `javascript-typescript-app`", preview)

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

    def test_gui_completion_message_reports_refresh(self) -> None:
        with repo_fixture("install_completion_refresh") as install_target:
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

            plan = build_install_plan(install_target, refresh_generated=True)
            message = build_completion_message(plan)

            self.assertIn("Codex Enhancer managed outputs were refreshed successfully.", message)
            self.assertIn("Stack packs from the target manifest:", message)
            self.assertIn("- javascript-typescript-app", message)

    def test_gui_completion_message_reports_upgrade(self) -> None:
        with repo_fixture("install_completion_upgrade") as install_target:
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

            write_file(install_target, "docs/ai/stack-guidance.md", "# stale guidance\n")

            plan = build_upgrade_plan(install_target)
            message = build_completion_message(plan)

            self.assertIn("Codex Enhancer upgrade reconcile completed successfully.", message)
            self.assertIn("Stack packs from the target manifest:", message)
            self.assertIn("- javascript-typescript-app", message)

    def test_build_overwrite_confirmation_message_lists_critical_files(self) -> None:
        with repo_fixture("install_confirm_message") as install_target:
            write_file(install_target, "AGENTS.md", "# Existing Repo\n")

            plan = build_install_plan(install_target, mode="existing", force=True)
            message = build_overwrite_confirmation_message(plan)

            self.assertIn("Confirm the overwrite list before running the installer.", message)
            self.assertIn("Critical enhancer-owned files will be replaced:", message)
            self.assertIn("- AGENTS.md", message)

    def test_build_overwrite_confirmation_message_lists_upgrade_overwrites(self) -> None:
        with repo_fixture("upgrade_confirm_message") as install_target:
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

            write_file(install_target, "docs/ai/stack-guidance.md", "# stale guidance\n")

            plan = build_upgrade_plan(install_target)
            message = build_overwrite_confirmation_message(plan)

            self.assertIn("Tracked enhancer files will be updated in place:", message)
            self.assertIn("- docs/ai/stack-guidance.md", message)


if __name__ == "__main__":
    unittest.main()
