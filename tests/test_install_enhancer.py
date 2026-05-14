from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import textwrap
import unittest
import uuid
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import install_enhancer
from scripts.install_enhancer import (
    apply_install_plan,
    audit_adaptation,
    build_install_plan,
    build_overwrite_confirmation_message,
    build_pack_management_plan,
    build_spec_kit_bridge_management_plan,
    build_upgrade_plan,
    build_workflow_management_plan,
    discover_commands,
    format_next_steps,
    inspect_install,
    overwrite_paths,
    proposal_paths,
)
from scripts.install_enhancer_gui import (
    PACK_VIEWPORT_HEIGHT,
    WINDOW_MAX_HEIGHT,
    build_completion_message,
    build_plan_preview,
    compute_window_geometry,
)
from scripts.enhancer_spec import (
    AUDIT_SPECIALIST_SKILL_NAMES,
    ENHANCER_MANIFEST_SCHEMA_VERSION,
    ENHANCER_VERSION,
    GITIGNORE_LINES,
    TARGET_VALIDATION_PROFILE,
)
from scripts.enhancer_validator import validate as validate_profile


TEMP_ROOT = Path(__file__).resolve().parent / "_tmp"
MANAGED_SECTION_LIST = (
    'managed_sections = ["AGENTS.md:selected-stack-packs", '
    '"AGENTS.md:spec-kit-bridge"]'
)


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
    def test_compute_window_geometry_stays_within_large_screen_bounds(self) -> None:
        width, height, x, y = compute_window_geometry(2560, 1440)

        self.assertLessEqual(width, 2560)
        self.assertLessEqual(height, 1440)
        self.assertLessEqual(height, WINDOW_MAX_HEIGHT)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

    def test_compute_window_geometry_shrinks_to_small_screen_bounds(self) -> None:
        width, height, x, y = compute_window_geometry(800, 600)

        self.assertLessEqual(width, 800)
        self.assertLessEqual(height, 600)
        self.assertGreater(PACK_VIEWPORT_HEIGHT, 0)
        self.assertLess(PACK_VIEWPORT_HEIGHT, height)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

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
        self.assertIn("frontend-ui", output)
        self.assertIn("Enable when:", output)
        self.assertIn("Adds:", output)
        self.assertIn("Skip when:", output)
        self.assertIn("python-service", output)
        self.assertIn("node-api-service", output)
        self.assertIn("library-package", output)

    def test_list_packs_with_target_explains_detection_audit(self) -> None:
        with repo_fixture("list_packs_audit") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            exit_code, output = run_installer(["--list-packs", "--target", str(install_target)])

            self.assertEqual(exit_code, 0)
            self.assertIn("Detection audit:", output)
            self.assertIn("Evidence is local only", output)
            self.assertIn("This report does not select packs", output)
            self.assertIn("Signals checked:", output)
            self.assertIn("required files: package.json", output)
            self.assertIn("optional detection signals: globs tsconfig*.json", output)
            self.assertIn("False-positive boundary:", output)
            self.assertIn("javascript-typescript-app", output)
            self.assertIn("status: recommended", output)
            self.assertIn("evidence: found package.json; matched tsconfig.json", output)

    def test_doctor_reports_plain_repo_first_run_path(self) -> None:
        with repo_fixture("doctor_plain") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(["--target", str(install_target), "--doctor"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Codex Enhancer doctor for", output)
            self.assertIn("Repo kind: `plain-repo`", output)
            self.assertIn("Safety: read-only check", output)
            self.assertIn("codex-enhancer init", output)
            self.assertIn("--existing --summary", output)
            self.assertFalse((install_target / ".codex/enhancer/manifest.toml").exists())

    def test_doctor_reports_source_checkout_validation_path(self) -> None:
        with repo_fixture("doctor_source") as install_target:
            write_file(install_target, "scripts/install_enhancer.py", "# placeholder\n")
            write_file(install_target, "docs/ai/roadmap.md", "# Roadmap\n")
            write_file(install_target, "scaffold/target-repo/AGENTS.md", "# Target\n")

            exit_code, output = run_installer(["--target", str(install_target), "--doctor"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Repo kind: `source-checkout`", output)
            self.assertIn("Source checkout: yes", output)
            self.assertIn("python scripts/check.py", output)
            self.assertIn("python -m unittest discover", output)

    def test_doctor_json_reports_installed_target_state(self) -> None:
        with repo_fixture("doctor_installed") as install_target:
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )
            self.assertEqual(exit_code, 0)

            exit_code, output = run_installer(["--target", str(install_target), "--doctor", "--json"])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output)
            self.assertEqual(payload["kind"], "doctor-report")
            self.assertEqual(payload["repo_kind"], "installed-target")
            self.assertEqual(payload["install_status"], "current")
            self.assertEqual(payload["install"]["kind"], "install-inspection")
            self.assertIn("next_steps", payload)

    def test_doctor_rejects_write_flags(self) -> None:
        with repo_fixture("doctor_invalid") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--doctor", "--write"]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("--doctor is read-only", output)

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
            self.assertIn(f"Target manifest schema: `{ENHANCER_MANIFEST_SCHEMA_VERSION}`", output)
            self.assertIn("Status: target install matches the current source version.", output)
            self.assertIn("Selected packs: `javascript-typescript-app`", output)

    def test_inspect_install_treats_trailing_zero_versions_as_equivalent(self) -> None:
        with repo_fixture("inspect_equivalent_version") as install_target:
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )
            self.assertEqual(exit_code, 0)

            manifest_path = install_target / ".codex/enhancer/manifest.toml"
            manifest_text = manifest_path.read_text(encoding="utf-8").replace(
                f'enhancer_version = "{ENHANCER_VERSION}"',
                f'enhancer_version = "{ENHANCER_VERSION}.0"',
            )
            manifest_path.write_text(manifest_text, encoding="utf-8")

            inspection = inspect_install(install_target)

            self.assertEqual(inspection.status, "current")

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
            self.assertIn("Target manifest schema: `1`", output)
            self.assertIn("Status: target install is older than the current source version.", output)
            self.assertIn("Selected packs: `python-service`", output)

    def test_inspect_install_reports_older_manifest_schema(self) -> None:
        with repo_fixture("inspect_old_schema") as install_target:
            write_file(
                install_target,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = 1
                enhancer_version = "%s"
                selected_packs = []

                [generated_files]
                stack_guidance = "docs/ai/stack-guidance.md"

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md", ".codex/enhancer/manifest.toml"]
                adapt_manually = ["AGENTS.md"]
                """ % ENHANCER_VERSION,
            )

            exit_code, output = run_installer(["--target", str(install_target), "--inspect-install"])

            self.assertEqual(exit_code, 0)
            self.assertIn(f"Target enhancer version: `{ENHANCER_VERSION}`", output)
            self.assertIn("Target manifest schema: `1`", output)
            self.assertIn(
                "Status: target install uses an older manifest schema than the current source version.",
                output,
            )

    def test_inspect_install_reports_detected_spec_kit_surface(self) -> None:
        with repo_fixture("inspect_spec_kit") as install_target:
            write_file(
                install_target,
                ".specify/integration.json",
                '{\n  "integration": "copilot",\n  "version": "0.8.3"\n}\n',
            )
            write_file(
                install_target,
                ".specify/init-options.json",
                '{\n  "integration": "copilot",\n  "ai": "copilot",\n  "script": "ps",\n  "speckit_version": "0.8.3"\n}\n',
            )
            write_file(install_target, ".github/prompts/speckit.plan.prompt.md", "# Plan\n")
            write_file(install_target, ".github/agents/speckit.tasks.agent.md", "# Tasks\n")

            exit_code, output = run_installer(["--target", str(install_target), "--inspect-install"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Spec Kit bridge:", output)
            self.assertIn("Official Spec Kit detected.", output)
            self.assertIn("Integration: `copilot`", output)
            self.assertIn("Likely command surface: .github/prompts and .github/agents.", output)

            exit_code, output = run_installer(
                ["--target", str(install_target), "--inspect-install", "--json"]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output)
            self.assertTrue(payload["spec_kit_detection"]["detected"])
            self.assertEqual(payload["spec_kit_detection"]["integration"], "copilot")
            self.assertEqual(
                payload["spec_kit_detection"]["command_label"],
                ".github/prompts and .github/agents",
            )

    def test_inspect_install_reports_utility_harness_state(self) -> None:
        with repo_fixture("inspect_utility") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--utility-harness-mode",
                    "install",
                    "--write",
                    "--force",
                ]
            )
            self.assertEqual(exit_code, 0)

            exit_code, output = run_installer(["--target", str(install_target), "--inspect-install"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Utility Harness:", output)
            self.assertIn("Utility Harness mode: `install`", output)
            self.assertIn("Utility Harness state: `installed`", output)

    def test_install_attach_mode_requires_existing_spec_kit(self) -> None:
        with repo_fixture("install_attach_missing") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--spec-kit-mode",
                    "attach",
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("requires an existing official Spec Kit install", output)

    def test_install_attach_mode_adds_bridge_skills_and_manifest_state(self) -> None:
        with repo_fixture("install_attach") as install_target:
            write_file(
                install_target,
                ".specify/integration.json",
                '{\n  "integration": "codex",\n  "version": "0.8.3"\n}\n',
            )
            write_file(
                install_target,
                ".specify/init-options.json",
                '{\n  "integration": "codex",\n  "script": "ps",\n  "speckit_version": "0.8.3"\n}\n',
            )
            write_file(install_target, ".agents/skills/speckit-plan/SKILL.md", "# Plan\n")

            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--spec-kit-mode",
                    "attach",
                    "--write",
                    "--force",
                ]
            )

            self.assertEqual(exit_code, 0)
            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            agents = (install_target / "AGENTS.md").read_text(encoding="utf-8")

            self.assertIn('mode = "attach"', manifest)
            self.assertIn('state = "attached"', manifest)
            self.assertIn('integration_key = "codex"', manifest)
            self.assertIn("Spec Kit bridge is attached to an existing official install.", agents)
            self.assertTrue((install_target / ".codex/skills/spec-implement-bridge/SKILL.md").exists())
            self.assertTrue((install_target / ".codex/skills/spec-sync-check/SKILL.md").exists())
            self.assertTrue((install_target / ".codex/skills/spec-review-bridge/SKILL.md").exists())

    def test_install_bootstrap_mode_plans_external_step(self) -> None:
        with repo_fixture("install_bootstrap") as install_target:
            plan = build_install_plan(
                install_target,
                mode="new",
                spec_kit_mode="bootstrap",
                spec_kit_script="ps",
                spec_kit_version="v0.8.3",
            )

            self.assertEqual(len(plan.external_steps), 1)
            self.assertIn("uvx", plan.external_steps[0].argv[0])
            self.assertIn("bootstrap", plan.spec_kit_bridge.mode)
            self.assertIn("docs/ai/spec-kit-bridge.md", plan.manifest_preview)

    def test_bootstrap_external_step_is_auditable_in_human_previews(self) -> None:
        with repo_fixture("install_bootstrap_preview") as install_target:
            plan = build_install_plan(
                install_target,
                mode="new",
                spec_kit_mode="bootstrap",
                spec_kit_script="ps",
                spec_kit_version="v0.8.3",
            )

            with patch.object(install_enhancer.shutil, "which", return_value=None):
                summary = install_enhancer.format_plan_report(plan, write=False, summary=True)
                full_preview = install_enhancer.format_plan_report(plan, write=False)
                gui_preview = build_plan_preview(plan)

            for rendered in (summary, full_preview, gui_preview):
                self.assertIn("uvx --from git+https://github.com/github/spec-kit.git@v0.8.3", rendered)
                self.assertIn("executable", rendered)
                self.assertIn("not found on PATH", rendered)
                self.assertIn("pinned ref", rendered)
                self.assertIn("v0.8.3", rendered)
                self.assertIn("network", rendered)
                self.assertIn("--spec-kit-exe <path>", rendered)
                self.assertIn("before enhancer-owned writes", rendered)

    def test_bootstrap_external_step_is_auditable_in_json_preview(self) -> None:
        with repo_fixture("install_bootstrap_json") as install_target:
            with patch.object(install_enhancer.shutil, "which", return_value=None):
                exit_code, output = run_installer(
                    [
                        "--target",
                        str(install_target),
                        "--mode",
                        "new",
                        "--spec-kit-mode",
                        "bootstrap",
                        "--spec-kit-script",
                        "ps",
                        "--spec-kit-version",
                        "v0.8.3",
                        "--json",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output)
            self.assertEqual(len(payload["external_steps"]), 1)
            step = payload["external_steps"][0]
            self.assertIn("uvx --from git+https://github.com/github/spec-kit.git@v0.8.3", step["command"])
            self.assertEqual(step["executable"], "uvx")
            self.assertFalse(step["executable_found"])
            self.assertEqual(step["executable_status"], "not found on PATH")
            self.assertEqual(step["pinned_ref"], "v0.8.3")
            self.assertTrue(step["requires_network"])
            self.assertEqual(step["order"], "before-enhancer-writes")
            self.assertIn("--spec-kit-exe <path>", step["recovery_hint"])

    def test_bootstrap_dry_run_does_not_execute_external_step(self) -> None:
        with repo_fixture("install_bootstrap_dry_run") as install_target:
            with patch.object(
                install_enhancer,
                "run_external_step",
                side_effect=AssertionError("dry run executed external step"),
            ):
                exit_code, output = run_installer(
                    [
                        "--target",
                        str(install_target),
                        "--mode",
                        "new",
                        "--spec-kit-mode",
                        "bootstrap",
                        "--summary",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("External steps: 1", output)
            self.assertFalse((install_target / ".specify").exists())

    def test_install_bootstrap_mode_write_runs_external_step(self) -> None:
        with repo_fixture("install_bootstrap_write") as parent:
            install_target = parent / "repo"
            if sys.platform == "win32":
                fake_specify = parent / "fake-specify.cmd"
                fake_specify.write_text(
                    "@echo off\r\n"
                    "mkdir .specify\\memory >nul 2>nul\r\n"
                    "mkdir specs >nul 2>nul\r\n"
                    "mkdir .agents\\skills\\speckit-plan >nul 2>nul\r\n"
                    "echo # Constitution> .specify\\memory\\constitution.md\r\n"
                    "echo # Plan> .agents\\skills\\speckit-plan\\SKILL.md\r\n",
                    encoding="utf-8",
                )
            else:
                fake_specify = parent / "fake-specify"
                fake_specify.write_text(
                    "#!/bin/sh\n"
                    "mkdir -p .specify/memory specs .agents/skills/speckit-plan\n"
                    "printf '# Constitution\\n' > .specify/memory/constitution.md\n"
                    "printf '# Plan\\n' > .agents/skills/speckit-plan/SKILL.md\n",
                    encoding="utf-8",
                )
                fake_specify.chmod(0o755)

            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "new",
                    "--spec-kit-mode",
                    "bootstrap",
                    "--spec-kit-script",
                    "ps",
                    "--spec-kit-exe",
                    str(fake_specify),
                    "--write",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((install_target / ".specify/memory/constitution.md").exists())
            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            self.assertIn('mode = "bootstrap"', manifest)
            self.assertIn('state = "bootstrapped"', manifest)

    def test_spec_kit_report_prints_feature_summary(self) -> None:
        with repo_fixture("spec_report") as install_target:
            write_file(install_target, "specs/001-login/spec.md", "# Spec\n")
            write_file(install_target, "specs/001-login/plan.md", "# Plan\n")
            write_file(
                install_target,
                "specs/001-login/tasks.md",
                """
                # Tasks
                - [x] T001 Done
                - [ ] T002 Open
                """,
            )

            exit_code, output = run_installer(
                ["--target", str(install_target), "--spec-kit-report", "--spec-kit-feature", "001"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Spec Kit feature report", output)
            self.assertIn("`001-login` at `specs/001-login`", output)
            self.assertIn("Tasks: 2 total, 1 done, 1 open", output)

    def test_spec_kit_sync_report_prints_changed_path_context(self) -> None:
        with repo_fixture("spec_sync_report") as install_target:
            write_file(install_target, "specs/001-login/spec.md", "# Spec\n")
            write_file(install_target, "specs/001-login/plan.md", "# Plan\n")
            write_file(
                install_target,
                "specs/001-login/tasks.md",
                """
                # Tasks
                - [x] T001 Done
                - [ ] T002 Open
                """,
            )

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--spec-kit-sync-report",
                    "--spec-kit-feature",
                    "001",
                    "--spec-kit-changed-path",
                    "src/auth.py",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Spec Kit sync report", output)
            self.assertIn("`001-login` at `specs/001-login`", output)
            self.assertIn("Artifacts to re-read:", output)
            self.assertIn("`src/auth.py`", output)

    def test_manage_spec_kit_bridge_turns_bridge_off_without_touching_spec_kit_files(self) -> None:
        with repo_fixture("manage_spec_kit_bridge") as install_target:
            write_file(
                install_target,
                ".specify/integration.json",
                '{\n  "integration": "codex",\n  "version": "0.8.3"\n}\n',
            )
            write_file(
                install_target,
                ".specify/init-options.json",
                '{\n  "integration": "codex",\n  "script": "ps",\n  "speckit_version": "0.8.3"\n}\n',
            )
            write_file(install_target, ".agents/skills/speckit-plan/SKILL.md", "# Plan\n")

            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--spec-kit-mode",
                    "attach",
                    "--write",
                    "--force",
                ]
            )
            self.assertEqual(exit_code, 0)

            plan = build_spec_kit_bridge_management_plan(
                install_target,
                spec_kit_mode="off",
                require_changes=True,
            )
            self.assertEqual(plan.operation, "manage-spec-kit-bridge")
            self.assertFalse(plan.spec_kit_bridge.enabled)
            self.assertTrue(all(not item.destination.parts[0].startswith(".specify") for item in plan.writes))

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-spec-kit-bridge",
                    "--spec-kit-mode",
                    "off",
                    "--write",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Applying Codex Enhancer Spec Kit bridge management plan", output)
            self.assertTrue((install_target / ".specify/integration.json").exists())
            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            agents = (install_target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn('mode = "off"', manifest)
            self.assertIn("Spec Kit bridge is off", agents)

    def test_manage_spec_kit_bridge_requires_bridge_option(self) -> None:
        with repo_fixture("manage_spec_kit_bridge_missing_option") as install_target:
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )
            self.assertEqual(exit_code, 0)

            exit_code, output = run_installer(
                ["--target", str(install_target), "--manage-spec-kit-bridge"]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("requires a Spec Kit bridge option", output)

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

    def test_upgrade_enhancer_refreshes_managed_agents_section_in_place(self) -> None:
        with repo_fixture("upgrade_managed_agents_section") as install_target:
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
            agents_text = agents_path.read_text(encoding="utf-8")
            agents_text = agents_text.replace("`javascript-typescript-app`", "`python-service`", 1)
            agents_text += "\n## Local Notes\nKeep this human-owned note.\n"
            agents_path.write_text(agents_text, encoding="utf-8")

            plan = build_upgrade_plan(install_target)

            self.assertIn(Path("AGENTS.md"), overwrite_paths(plan))
            self.assertIn(Path(".codex/enhancer-proposals/AGENTS.md"), proposal_paths(plan))

            apply_install_plan(plan)
            refreshed_agents = agents_path.read_text(encoding="utf-8")

            self.assertIn("`javascript-typescript-app`", refreshed_agents)
            self.assertIn("Keep this human-owned note.", refreshed_agents)
            self.assertTrue((install_target / ".codex/enhancer-proposals/AGENTS.md").exists())

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
                "Safe to regenerate later: `docs/ai/stack-guidance.md`, `docs/ai/spec-kit-bridge.md`, `.codex/enhancer/manifest.toml`",
                output,
            )

    def test_dry_run_alias_keeps_preview_behavior_explicit(self) -> None:
        with repo_fixture("install_parent_alias") as parent:
            target = parent / "new_repo"

            exit_code, output = run_installer(
                ["--target", str(target), "--mode", "new", "--dry-run"]
            )

            self.assertEqual(exit_code, 0)
            self.assertFalse(target.exists())
            self.assertIn("Planned Codex Enhancer install", output)

    def test_summary_and_diff_preview_are_available_for_plans(self) -> None:
        with repo_fixture("summary_diff") as install_target:
            write_file(install_target, "AGENTS.md", "# Existing\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--summary", "--diff"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Plan summary:", output)
            self.assertIn("Diff preview:", output)
            self.assertIn("--- AGENTS.md", output)
            self.assertIn("+++ .codex/enhancer-proposals/AGENTS", output)
            self.assertNotIn("--- AGENTS.md\n\n+++ ", output)

    def test_diff_preview_truncates_large_files_unless_full_is_requested(self) -> None:
        with repo_fixture("summary_diff_truncated") as install_target:
            write_file(install_target, "AGENTS.md", "# Existing\n")
            plan = build_install_plan(install_target, mode="existing")

            truncated = "\n".join(
                install_enhancer.format_plan_diff_lines(plan, file_line_limit=4)
            )
            full = "\n".join(
                install_enhancer.format_plan_diff_lines(plan, file_line_limit=4, full=True)
            )

            self.assertIn("diff truncated after 4 lines", truncated)
            self.assertNotIn("diff truncated after 4 lines", full)

    def test_json_plan_output_is_machine_readable(self) -> None:
        with repo_fixture("json_plan") as install_target:
            exit_code, output = run_installer(
                ["--target", str(install_target), "--mode", "new", "--json"]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output)
            self.assertEqual(payload["kind"], "install-plan")
            self.assertEqual(payload["operation"], "install")
            self.assertFalse(payload["write"])
            self.assertIn("writes", payload)
            self.assertIn("schema_version", payload)
            self.assertIn("spec_kit_detection", payload)
            self.assertFalse(payload["spec_kit_detection"]["detected"])
            self.assertEqual(payload["diagnostics"], [])
            self.assertIn("next_steps", payload)

    def test_write_plan_blocks_existing_git_changes_by_default(self) -> None:
        with repo_fixture("write_safety_dirty") as install_target:
            write_file(install_target, ".git/HEAD", "ref: refs/heads/main\n")
            write_file(install_target, "README.md", "# Existing local work\n")
            git_status = subprocess.CompletedProcess(
                args=("git", "status", "--short"),
                returncode=0,
                stdout="?? README.md\n",
                stderr="",
            )

            with (
                patch.object(install_enhancer.shutil, "which", return_value="git"),
                patch.object(install_enhancer.subprocess, "run", return_value=git_status),
            ):
                exit_code, output = run_installer(
                    [
                        "--target",
                        str(install_target),
                        "--mode",
                        "existing",
                        "--write",
                        "--force",
                        "--summary",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("Write safety blocked apply:", output)
            self.assertIn("Target git worktree already has 1 local change(s)", output)
            self.assertIn("Review `git status --short`", output)
            self.assertIn("--allow-dirty", output)
            self.assertIn("?? README.md", output)
            self.assertFalse((install_target / "AGENTS.md").exists())

    def test_write_plan_allows_dirty_target_with_explicit_override(self) -> None:
        with repo_fixture("write_safety_allow_dirty") as install_target:
            write_file(install_target, ".git/HEAD", "ref: refs/heads/main\n")
            write_file(install_target, "README.md", "# Existing local work\n")
            git_status = subprocess.CompletedProcess(
                args=("git", "status", "--short"),
                returncode=0,
                stdout="?? README.md\n",
                stderr="",
            )

            with (
                patch.object(install_enhancer.shutil, "which", return_value="git"),
                patch.object(install_enhancer.subprocess, "run", return_value=git_status),
            ):
                exit_code, output = run_installer(
                    [
                        "--target",
                        str(install_target),
                        "--mode",
                        "existing",
                        "--write",
                        "--force",
                        "--allow-dirty",
                        "--summary",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("Write safety:", output)
            self.assertIn("warning: Target git worktree already has 1 local change(s)", output)
            self.assertTrue((install_target / "AGENTS.md").exists())

    def test_write_plan_json_includes_git_change_diagnostics(self) -> None:
        with repo_fixture("write_safety_json") as install_target:
            write_file(install_target, ".git/HEAD", "ref: refs/heads/main\n")
            write_file(install_target, "README.md", "# Existing local work\n")
            git_status = subprocess.CompletedProcess(
                args=("git", "status", "--short"),
                returncode=0,
                stdout="?? README.md\n",
                stderr="",
            )

            with (
                patch.object(install_enhancer.shutil, "which", return_value="git"),
                patch.object(install_enhancer.subprocess, "run", return_value=git_status),
            ):
                exit_code, output = run_installer(
                    [
                        "--target",
                        str(install_target),
                        "--mode",
                        "existing",
                        "--write",
                        "--force",
                        "--json",
                    ]
                )

            self.assertEqual(exit_code, 1)
            payload = json.loads(output)
            self.assertEqual(payload["kind"], "error")
            self.assertEqual(payload["diagnostics"][0]["severity"], "error")
            self.assertEqual(payload["diagnostics"][0]["code"], "dirty-git-worktree")
            self.assertIn("?? README.md", payload["diagnostics"][0]["details"])

    def test_write_plan_blocks_source_checkout_target_by_default(self) -> None:
        with repo_fixture("write_safety_source") as install_target:
            write_file(install_target, "scripts/install_enhancer.py", "# source marker\n")
            write_file(install_target, "docs/ai/roadmap.md", "# source marker\n")
            write_file(install_target, "scaffold/target-repo/AGENTS.md", "# source marker\n")

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--write",
                    "--force",
                    "--summary",
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("source checkout", output)
            self.assertIn("--allow-source-target", output)
            self.assertFalse((install_target / ".codex/enhancer/manifest.toml").exists())

    def test_write_plan_allows_source_checkout_with_explicit_override(self) -> None:
        with repo_fixture("write_safety_source_allowed") as install_target:
            write_file(install_target, "scripts/install_enhancer.py", "# source marker\n")
            write_file(install_target, "docs/ai/roadmap.md", "# source marker\n")
            write_file(install_target, "scaffold/target-repo/AGENTS.md", "# source marker\n")

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--write",
                    "--force",
                    "--allow-source-target",
                    "--summary",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Write safety:", output)
            self.assertIn("warning: Target looks like the Codex Enhancer source checkout", output)
            self.assertTrue((install_target / ".codex/enhancer/manifest.toml").exists())

    def test_json_output_covers_read_only_reports_and_errors(self) -> None:
        exit_code, output = run_installer(["--list-packs", "--json"])
        self.assertEqual(exit_code, 0)
        pack_catalog = json.loads(output)
        self.assertEqual(pack_catalog["kind"], "pack-catalog")
        self.assertIn("packs", pack_catalog)
        self.assertIn("detection_signals", pack_catalog["packs"][0])

        exit_code, output = run_installer(["--mode", "new", "--json"])
        self.assertEqual(exit_code, 1)
        error_payload = json.loads(output)
        self.assertEqual(error_payload["kind"], "error")
        self.assertIn("Missing required --target", error_payload["message"])

        with repo_fixture("json_readonly") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--inspect-install", "--json"]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(output)["kind"], "install-inspection")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--spec-kit-report", "--json"]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(output)["kind"], "spec-kit-report")

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--spec-kit-sync-report",
                    "--spec-kit-changed-path",
                    "README.md",
                    "--json",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(output)["kind"], "spec-kit-sync-report")

    def test_json_pack_catalog_with_target_includes_structured_detection_evidence(self) -> None:
        with repo_fixture("json_pack_catalog_target") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")

            exit_code, output = run_installer(["--list-packs", "--target", str(install_target), "--json"])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output)
            self.assertEqual(payload["kind"], "pack-catalog")
            self.assertEqual(payload["target"], str(install_target.resolve()))
            self.assertIn("Detection uses only local", payload["notes"][0])

            javascript_pack = next(
                pack for pack in payload["packs"] if pack["name"] == "javascript-typescript-app"
            )
            self.assertEqual(javascript_pack["status"], "recommended")
            self.assertTrue(javascript_pack["detected"])
            self.assertTrue(javascript_pack["recommended"])
            self.assertEqual(javascript_pack["detection_signals"]["all_files"], ["package.json"])
            self.assertIn("tsconfig*.json", javascript_pack["detection_signals"]["any_globs"])
            self.assertIn("found package.json", javascript_pack["evidence"])
            self.assertIn("matched tsconfig.json", javascript_pack["evidence"])
            self.assertIn("package.json exists only", javascript_pack["guidance"]["skip_when"][0])

    def test_json_output_covers_management_plan_operations(self) -> None:
        with repo_fixture("json_management") as install_target:
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )
            self.assertEqual(exit_code, 0)
            write_file(
                install_target,
                ".specify/integration.json",
                '{\n  "integration": "codex",\n  "version": "0.8.3"\n}\n',
            )
            write_file(
                install_target,
                ".specify/init-options.json",
                '{\n  "integration": "codex",\n  "script": "ps",\n  "speckit_version": "0.8.3"\n}\n',
            )
            write_file(install_target, ".agents/skills/speckit-plan/SKILL.md", "# Plan\n")

            operations = (
                (
                    "manage-packs",
                    [
                        "--target",
                        str(install_target),
                        "--manage-packs",
                        "--add-pack",
                        "python-service",
                        "--json",
                    ],
                ),
                (
                    "manage-spec-kit-bridge",
                    [
                        "--target",
                        str(install_target),
                        "--manage-spec-kit-bridge",
                        "--spec-kit-mode",
                        "attach",
                        "--json",
                    ],
                ),
                (
                    "refresh-generated",
                    ["--target", str(install_target), "--refresh-generated", "--json"],
                ),
                (
                    "upgrade-enhancer",
                    ["--target", str(install_target), "--upgrade-enhancer", "--json"],
                ),
            )

            for operation, arguments in operations:
                with self.subTest(operation=operation):
                    exit_code, output = run_installer(arguments)
                    self.assertEqual(exit_code, 0)
                    payload = json.loads(output)
                    self.assertEqual(payload["kind"], "install-plan")
                    self.assertEqual(payload["operation"], operation)

    def test_audit_adaptation_reports_inherited_guidance(self) -> None:
        with repo_fixture("adapt_audit") as install_target:
            plan = build_install_plan(install_target, mode="new")
            apply_install_plan(plan)

            findings = audit_adaptation(install_target)
            messages = "\n".join(finding.message for finding in findings)

            self.assertIn("inherited generic guidance", messages)

    def test_audit_adaptation_can_emit_json(self) -> None:
        with repo_fixture("adapt_json") as install_target:
            plan = build_install_plan(install_target, mode="new")
            apply_install_plan(plan)

            exit_code, output = run_installer(
                ["--target", str(install_target), "--audit-adaptation", "--json"]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output)
            self.assertEqual(payload["kind"], "adaptation-audit")
            self.assertEqual(payload["status"], "needs-adaptation")
            self.assertGreater(payload["finding_count"], 0)
            self.assertGreater(payload["severity_counts"]["medium"], 0)

    def test_audit_adaptation_can_pass_clean_target(self) -> None:
        with repo_fixture("adapt_clean") as install_target:
            write_file(install_target, "AGENTS.md", "# Demo\n\nRun `python scripts/check.py`.\n")
            write_file(install_target, "docs/ai/architecture.md", "# Architecture\n\nDemo-specific notes.\n")
            write_file(install_target, "docs/ai/code-review.md", "# Review\n\nDemo-specific checks.\n")
            write_file(install_target, ".codex/enhancer/manifest.toml", "schema_version = 1\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--audit-adaptation"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Status: ready", output)
            self.assertIn("Severity summary: none", output)
            self.assertIn("no obvious inherited placeholders", output)

            exit_code, output = run_installer(
                ["--target", str(install_target), "--audit-adaptation", "--json"]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output)
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["severity_counts"]["high"], 0)
            self.assertEqual(payload["severity_counts"]["medium"], 0)

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

    def test_dry_run_surfaces_manifest_evidence_for_detected_stack_packs(self) -> None:
        with repo_fixture("install_pack_evidence_preview") as install_target:
            write_file(
                install_target,
                "package.json",
                json.dumps(
                    {
                        "name": "demo",
                        "packageManager": "pnpm@9.0.0",
                        "scripts": {
                            "build": "vite build",
                            "test": "vitest run",
                        },
                        "devDependencies": {
                            "typescript": "latest",
                            "vite": "latest",
                        },
                    }
                ),
            )
            write_file(install_target, "tsconfig.json", "{}\n")

            exit_code, output = run_installer(["--target", str(install_target), "--mode", "existing"])

            self.assertEqual(exit_code, 0)
            self.assertIn("package manager: pnpm from package.json packageManager", output)
            self.assertIn("package.json scripts: build, test", output)
            self.assertIn("package.json packages: typescript, vite", output)

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

    def test_use_recommended_packs_selects_frontend_bundle(self) -> None:
        with repo_fixture("install_recommended_frontend") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")
            write_file(install_target, "src/App.tsx", "export function App() { return <main />; }\n")

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
            self.assertIn("frontend-ui: selected from recommended detection", output)
            self.assertIn(
                'selected_packs = ["javascript-typescript-app", "frontend-ui"]',
                output,
            )

    def test_use_recommended_packs_selects_node_api_bundle(self) -> None:
        with repo_fixture("install_recommended_node_api") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")
            write_file(install_target, "src/server.ts", "export const server = {};\n")

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
            self.assertIn("node-api-service: selected from recommended detection", output)
            self.assertIn(
                'selected_packs = ["javascript-typescript-app", "node-api-service"]',
                output,
            )

    def test_use_recommended_packs_selects_library_package_bundle(self) -> None:
        with repo_fixture("install_recommended_library") as install_target:
            write_file(
                install_target,
                "package.json",
                json.dumps(
                    {
                        "name": "@scope/demo-library",
                        "exports": "./dist/index.js",
                        "types": "./dist/index.d.ts",
                        "files": ["dist"],
                        "scripts": {
                            "build": "tsup src/index.ts",
                            "test": "vitest run",
                            "typecheck": "tsc --noEmit",
                        },
                        "devDependencies": {
                            "typescript": "latest",
                            "tsup": "latest",
                        },
                    }
                ),
            )
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
            self.assertIn("library-package: selected from recommended detection", output)
            self.assertIn("package.json library fields: exports, types, files", output)
            self.assertIn(
                'selected_packs = ["javascript-typescript-app", "library-package"]',
                output,
            )

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
            self.assertIn("do not combine it with pack-selection, Spec Kit override, or Utility Harness flags", output)

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
            self.assertTrue((install_target / "scripts/spec_kit_bridge.py").exists())
            self.assertTrue((install_target / "scripts/utility_harness.py").exists())
            self.assertTrue((install_target / "scripts/enhancer_validator.py").exists())
            self.assertTrue((install_target / "tests/test_check.py").exists())
            self.assertTrue((install_target / ".github/workflows/validate.yml").exists())

            gitignore = (install_target / ".gitignore").read_text(encoding="utf-8")
            for line in GITIGNORE_LINES:
                self.assertIn(line, gitignore)

    def test_install_preserves_external_agents_skills_root(self) -> None:
        with repo_fixture("install_agents_skills_external") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            write_file(
                install_target,
                ".agents/skills/custom-audit/SKILL.md",
                "# External skill\n\nThis file is not enhancer-owned.\n",
            )

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write"]
            )

            self.assertEqual(exit_code, 0)
            external_skill = install_target / ".agents/skills/custom-audit/SKILL.md"
            self.assertEqual(
                external_skill.read_text(encoding="utf-8"),
                "# External skill\n\nThis file is not enhancer-owned.\n",
            )
            self.assertTrue((install_target / ".codex/skills/adapt-enhancer/SKILL.md").exists())
            self.assertFalse((install_target / ".agents/skills/adapt-enhancer/SKILL.md").exists())

    def test_utility_harness_install_adds_helper_files_and_manifest_state(self) -> None:
        with repo_fixture("install_utility") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--utility-harness-mode",
                    "install",
                    "--write",
                    "--force",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Utility Harness:", output)
            self.assertTrue((install_target / "requirements-codex.txt").exists())
            self.assertTrue((install_target / "requirements-codex-minimal.txt").exists())
            self.assertTrue((install_target / "requirements-codex-readers.txt").exists())
            self.assertTrue((install_target / "requirements-codex-analysis.txt").exists())
            self.assertTrue((install_target / "requirements-codex-cli.txt").exists())
            self.assertTrue((install_target / "tools/ai/audit_inputs.py").exists())
            self.assertTrue((install_target / "tools/ai/inspect_repo.py").exists())
            self.assertTrue((install_target / "tools/ai/read_any.py").exists())
            self.assertTrue((install_target / "tools/ai/summarize_tree.py").exists())
            self.assertTrue((install_target / "tools/ai/run_checks.py").exists())
            self.assertTrue((install_target / "docs/ai/utility-harness.md").exists())

            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            agents = (install_target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("[integrations.utility_harness]", manifest)
            self.assertIn('mode = "install"', manifest)
            self.assertIn('state = "installed"', manifest)
            self.assertIn('"requirements-codex-readers.txt"', manifest)
            self.assertIn('"tools/ai/audit_inputs.py"', manifest)
            self.assertIn('"tools/ai/run_checks.py"', manifest)
            self.assertIn("Codex Utility Harness is installed", agents)
            self.assertEqual(validate_profile(install_target, TARGET_VALIDATION_PROFILE), [])

            listed_checks = subprocess.run(
                [sys.executable, "-B", "tools/ai/run_checks.py", "--list"],
                cwd=install_target,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(listed_checks.returncode, 0)
            self.assertIn("enhancer:check", listed_checks.stdout)
            self.assertIn("trust=confirmed", listed_checks.stdout)
            self.assertNotIn("tools/ai/run_checks.py", listed_checks.stdout)

            audit_inputs = subprocess.run(
                [sys.executable, "-B", "tools/ai/audit_inputs.py", "--json"],
                cwd=install_target,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(audit_inputs.returncode, 0)
            self.assertIn('"schema_version": 1', audit_inputs.stdout)
            self.assertIn('"validation_commands"', audit_inputs.stdout)

    def test_utility_harness_run_checks_does_not_execute_prose_commands_by_default(self) -> None:
        with repo_fixture("utility_prose_safety") as install_target:
            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "new",
                    "--utility-harness-mode",
                    "install",
                    "--write",
                ]
            )
            self.assertEqual(exit_code, 0)
            agents = install_target / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8")
                + '\nUnsafe example: `python -c "open(\'ran.txt\',\'w\').write(\'x\')" test`\n',
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, "-B", "tools/ai/run_checks.py", "--only", "agents"],
                cwd=install_target,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(completed.returncode, 1)
            self.assertIn("Prose-extracted commands were not run by default", completed.stdout)
            self.assertFalse((install_target / "ran.txt").exists())

    def test_utility_harness_run_checks_requires_shell_opt_in_for_manifest_commands(self) -> None:
        with repo_fixture("utility_manifest_shell_safety") as install_target:
            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "new",
                    "--utility-harness-mode",
                    "install",
                    "--write",
                ]
            )
            self.assertEqual(exit_code, 0)
            manifest = install_target / ".codex/enhancer/manifest.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8")
                + '\n[commands]\ncheck_command = "python -c \\"from pathlib import Path; Path(\'ran.txt\').write_text(\'x\')\\" test && echo done"\n',
                encoding="utf-8",
            )

            listed = subprocess.run(
                [sys.executable, "-B", "tools/ai/run_checks.py", "--list", "--only", "manifest"],
                cwd=install_target,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(listed.returncode, 0)
            self.assertIn("trust=confirmed", listed.stdout)
            self.assertIn("requires-shell", listed.stdout)

            completed = subprocess.run(
                [sys.executable, "-B", "tools/ai/run_checks.py", "--only", "manifest"],
                cwd=install_target,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(completed.returncode, 0)
            self.assertIn("skipped: command contains shell control characters", completed.stdout)
            self.assertFalse((install_target / "ran.txt").exists())

    def test_utility_harness_dry_run_does_not_write_helper_files(self) -> None:
        with repo_fixture("install_utility_preview") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--utility-harness-mode",
                    "install",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Utility Harness:", output)
            self.assertIn("Codex Utility Harness is installed", output)
            self.assertIn("- create: requirements-codex.txt", output)
            self.assertIn("- create: requirements-codex-readers.txt", output)
            self.assertFalse((install_target / "requirements-codex.txt").exists())

    def test_refresh_generated_preserves_utility_harness_state(self) -> None:
        with repo_fixture("refresh_utility") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--mode",
                    "existing",
                    "--utility-harness-mode",
                    "install",
                    "--write",
                    "--force",
                ]
            )
            self.assertEqual(exit_code, 0)

            exit_code, output = run_installer(
                ["--target", str(install_target), "--refresh-generated", "--write"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Applying Codex Enhancer generated-output refresh", output)
            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            self.assertIn("[integrations.utility_harness]", manifest)
            self.assertIn('state = "installed"', manifest)
            self.assertTrue((install_target / "tools/ai/audit_inputs.py").exists())
            self.assertTrue((install_target / "tools/ai/run_checks.py").exists())

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

    def test_target_validation_requires_current_manifest_schema(self) -> None:
        with repo_fixture("install_manifest_schema") as target:
            install_target = target / "repo"

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )

            self.assertEqual(exit_code, 0)

            manifest_path = install_target / ".codex/enhancer/manifest.toml"
            manifest_text = manifest_path.read_text(encoding="utf-8").replace(
                f"schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}\n",
                "schema_version = 1\n",
            )
            manifest_path.write_text(manifest_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any(
                    f"must use schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}" in error
                    for error in errors
                )
            )

    def test_target_validation_requires_manifest_lifecycle(self) -> None:
        with repo_fixture("install_manifest_lifecycle") as target:
            install_target = target / "repo"

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )

            self.assertEqual(exit_code, 0)

            manifest_path = install_target / ".codex/enhancer/manifest.toml"
            manifest_text = manifest_path.read_text(encoding="utf-8").replace(
                """[lifecycle]
state = "active"
pack_selection = "manifest"
managed_sections = ["AGENTS.md:selected-stack-packs", "AGENTS.md:spec-kit-bridge"]

""",
                "",
            )
            manifest_path.write_text(manifest_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(any("must set lifecycle.state" in error for error in errors))

    def test_target_validation_requires_managed_section_marker_pair(self) -> None:
        with repo_fixture("install_managed_section_missing") as target:
            install_target = target / "repo"

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )

            self.assertEqual(exit_code, 0)

            agents_path = install_target / "AGENTS.md"
            agents_text = agents_path.read_text(encoding="utf-8").replace(
                "<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs start -->\n",
                "",
            )
            agents_path.write_text(agents_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any("must contain exactly one managed section marker pair" in error for error in errors)
            )

    def test_target_validation_requires_manifest_managed_section_id(self) -> None:
        with repo_fixture("install_managed_section_manifest") as target:
            install_target = target / "repo"

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )

            self.assertEqual(exit_code, 0)

            manifest_path = install_target / ".codex/enhancer/manifest.toml"
            manifest_text = manifest_path.read_text(encoding="utf-8").replace(
                MANAGED_SECTION_LIST,
                "managed_sections = []",
            )
            manifest_path.write_text(manifest_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any(
                    "is missing managed section ids: AGENTS.md:selected-stack-packs, AGENTS.md:spec-kit-bridge"
                    in error
                    for error in errors
                )
            )

    def test_target_validation_rejects_reversed_managed_section_markers(self) -> None:
        with repo_fixture("install_managed_section_reversed") as target:
            install_target = target / "repo"

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )

            self.assertEqual(exit_code, 0)

            agents_path = install_target / "AGENTS.md"
            agents_text = agents_path.read_text(encoding="utf-8")
            start = "<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs start -->"
            end = "<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs end -->"
            agents_path.write_text(
                agents_text.replace(start, "__TEMP_MARKER__").replace(end, start).replace("__TEMP_MARKER__", end),
                encoding="utf-8",
            )

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any("has reversed managed section markers" in error for error in errors)
            )

    def test_target_validation_requires_spec_kit_bridge_marker_pair(self) -> None:
        with repo_fixture("install_spec_kit_bridge_missing") as target:
            install_target = target / "repo"

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "new", "--write"]
            )

            self.assertEqual(exit_code, 0)

            agents_path = install_target / "AGENTS.md"
            agents_text = agents_path.read_text(encoding="utf-8").replace(
                "<!-- codex-enhancer:managed-section AGENTS.md:spec-kit-bridge start -->\n",
                "",
            )
            agents_path.write_text(agents_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any(
                    "must contain exactly one managed section marker pair" in error
                    and "AGENTS.md:spec-kit-bridge" in error
                    for error in errors
                )
            )

    def test_target_validation_requires_selected_pack_state_to_match_detection_records(self) -> None:
        with repo_fixture("install_pack_state_drift") as install_target:
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

            manifest_path = install_target / ".codex/enhancer/manifest.toml"
            manifest_text = manifest_path.read_text(encoding="utf-8").replace(
                'name = "javascript-typescript-app"\n'
                "selected = true\n",
                'name = "javascript-typescript-app"\n'
                "selected = false\n",
            )
            if manifest_text == manifest_path.read_text(encoding="utf-8"):
                self.fail("manifest fixture mutation did not change the selected flag")
            manifest_path.write_text(manifest_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any("selected_packs disagree with detected_packs selected flags" in error for error in errors)
            )

    def test_target_validation_checks_selected_pack_summary_inside_managed_section(self) -> None:
        with repo_fixture("install_managed_section_drift") as install_target:
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
            agents_text = agents_path.read_text(encoding="utf-8")
            start = "<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs start -->"
            end = "<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs end -->"
            start_index = agents_text.index(start) + len(start)
            end_index = agents_text.index(end)
            agents_text = (
                agents_text[:start_index]
                + "\nSelected packs: `python-service`\n"
                + agents_text[end_index:]
            )
            agents_text += "\nOutside the managed section: `javascript-typescript-app`.\n"
            agents_path.write_text(agents_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any("managed selected-stack-packs section is missing" in error for error in errors)
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

    def test_existing_repo_uses_unique_proposal_paths_for_existing_review_work(self) -> None:
        with repo_fixture("install_existing_proposal_collision") as install_target:
            write_file(install_target, "AGENTS.md", "# Existing guidance\n")
            write_file(
                install_target,
                ".codex/enhancer-proposals/AGENTS.md",
                "# Existing proposal under review\n",
            )

            plan = build_install_plan(install_target, mode="existing", force=False)

            self.assertIn(Path(".codex/enhancer-proposals/AGENTS.1.md"), proposal_paths(plan))

            apply_install_plan(plan)

            self.assertEqual(
                "# Existing proposal under review\n",
                (install_target / ".codex/enhancer-proposals/AGENTS.md").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertTrue((install_target / ".codex/enhancer-proposals/AGENTS.1.md").exists())

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
            self.assertIn(f"schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}", manifest)
            self.assertIn(f'enhancer_version = "{ENHANCER_VERSION}"', manifest)
            self.assertIn("[lifecycle]", manifest)
            self.assertIn('state = "active"', manifest)
            self.assertIn('pack_selection = "manifest"', manifest)
            self.assertIn(MANAGED_SECTION_LIST, manifest)
            self.assertIn("`javascript-typescript-app` (JavaScript / TypeScript app):", agents)
            self.assertIn(
                "<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs start -->",
                agents,
            )
            self.assertIn(
                "<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs end -->",
                agents,
            )
            self.assertIn(
                "<!-- codex-enhancer:managed-section AGENTS.md:spec-kit-bridge start -->",
                agents,
            )
            self.assertIn(
                "<!-- codex-enhancer:managed-section AGENTS.md:spec-kit-bridge end -->",
                agents,
            )
            self.assertIn('selected_packs = ["javascript-typescript-app"]', manifest)
            self.assertIn('evidence = ["found package.json", "matched tsconfig.json"]', manifest)
            self.assertIn(
                'safe_to_regenerate = ["docs/ai/stack-guidance.md", "docs/ai/spec-kit-bridge.md", ".codex/enhancer/manifest.toml"]',
                manifest,
            )
            self.assertIn('spec_kit_bridge = "docs/ai/spec-kit-bridge.md"', manifest)
            self.assertIn('[integrations.spec_kit]', manifest)
            self.assertIn('mode = "off"', manifest)
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
                "Stack guidance, the Spec Kit bridge guide, and the pack manifest will be regenerated from the existing target manifest.",
                output,
            )
            self.assertIn("- overwrite: docs/ai/stack-guidance.md", output)
            self.assertIn("- overwrite: docs/ai/spec-kit-bridge.md", output)
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

    def test_manage_packs_adds_pack_and_updates_managed_outputs(self) -> None:
        with repo_fixture("manage_add") as install_target:
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
                ["--target", str(install_target), "--manage-packs", "--add-pack", "python-service"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Planned Codex Enhancer stack-pack management plan", output)
            self.assertIn("python-service: added by --add-pack", output)
            self.assertIn("- overwrite: AGENTS.md", output)
            self.assertIn('Manifest preview selected_packs = ["javascript-typescript-app", "python-service"]', output)

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-packs",
                    "--add-pack",
                    "python-service",
                    "--write",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Applying Codex Enhancer stack-pack management plan", output)

            agents = (install_target / "AGENTS.md").read_text(encoding="utf-8")
            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            stack_guidance = (install_target / "docs/ai/stack-guidance.md").read_text(encoding="utf-8")

            self.assertIn("Selected packs: `javascript-typescript-app`, `python-service`", agents)
            self.assertIn('selected_packs = ["javascript-typescript-app", "python-service"]', manifest)
            self.assertIn("Pack id: `javascript-typescript-app`", stack_guidance)
            self.assertIn("Pack id: `python-service`", stack_guidance)
            self.assertEqual(validate_profile(install_target, TARGET_VALIDATION_PROFILE), [])

    def test_manage_packs_removes_pack_without_touching_manual_agents_content(self) -> None:
        with repo_fixture("manage_remove") as install_target:
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
            agents_path.write_text(
                agents_path.read_text(encoding="utf-8") + "\nManual note outside markers.\n",
                encoding="utf-8",
            )

            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-packs",
                    "--remove-pack",
                    "javascript-typescript-app",
                    "--write",
                ]
            )

            self.assertEqual(exit_code, 0)
            agents = agents_path.read_text(encoding="utf-8")
            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            stack_guidance = (install_target / "docs/ai/stack-guidance.md").read_text(encoding="utf-8")

            self.assertIn("No stack packs are selected yet.", agents)
            self.assertIn("Manual note outside markers.", agents)
            self.assertIn("selected_packs = []", manifest)
            self.assertIn("No stack packs are selected yet.", stack_guidance)

    def test_manage_packs_set_replaces_selected_pack_set(self) -> None:
        with repo_fixture("manage_set") as install_target:
            write_file(install_target, "package.json", '{"name": "demo"}\n')
            write_file(install_target, "tsconfig.json", "{}\n")
            write_file(install_target, "src/App.tsx", "export function App() { return <main />; }\n")

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
                [
                    "--target",
                    str(install_target),
                    "--manage-packs",
                    "--set-pack",
                    "node-api-service",
                    "--write",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("javascript-typescript-app: removed by --set-pack replacement", output)
            self.assertIn("frontend-ui: removed by --set-pack replacement", output)
            self.assertIn("node-api-service: selected by --set-pack", output)

            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            agents = (install_target / "AGENTS.md").read_text(encoding="utf-8")

            self.assertIn('selected_packs = ["node-api-service"]', manifest)
            self.assertIn("Selected packs: `node-api-service`", agents)
            self.assertNotIn("Selected packs: `javascript-typescript-app`", agents)

    def test_manage_packs_rejects_invalid_flag_combinations(self) -> None:
        with repo_fixture("manage_invalid") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--add-pack", "python-service"]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("require --manage-packs", output)

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )
            self.assertEqual(exit_code, 0)

            exit_code, output = run_installer(
                ["--target", str(install_target), "--manage-packs"]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("--manage-packs requires --add-pack", output)

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-packs",
                    "--add-pack",
                    "python-service",
                    "--set-pack",
                    "python-service",
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("--set-pack cannot be combined", output)

    def test_list_workflows_without_target_prints_available_workflow_names(self) -> None:
        exit_code, output = run_installer(["--list-workflows"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Available workflow packs:", output)
        self.assertIn("repository-improvement-audit", output)

    def test_install_does_not_add_audit_workflow_assets_by_default(self) -> None:
        with repo_fixture("install_no_workflow_assets") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )

            self.assertEqual(exit_code, 0)
            self.assertFalse((install_target / "docs/ai/workflow-guidance.md").exists())
            self.assertFalse((install_target / "docs/ai/repo-improvement-audit.md").exists())
            self.assertFalse((install_target / "docs/ai/repo-audit-finding-schema.md").exists())
            self.assertFalse((install_target / "docs/ai/repo-audit-roadmap-rubric.md").exists())
            self.assertFalse(
                (install_target / ".codex/skills/full-repo-improvement-audit/SKILL.md").exists()
            )
            for skill_name in AUDIT_SPECIALIST_SKILL_NAMES:
                self.assertFalse((install_target / f".codex/skills/{skill_name}/SKILL.md").exists())
            self.assertFalse((install_target / "roadmap.md").exists())
            self.assertEqual(validate_profile(install_target, TARGET_VALIDATION_PROFILE), [])

    def test_manage_workflows_adds_repository_audit_workflow_and_roadmap(self) -> None:
        with repo_fixture("manage_workflow_add") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            write_file(
                install_target,
                "roadmap.md",
                """
                # Existing Roadmap

                Keep this product-owned roadmap note.
                """,
            )

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )
            self.assertEqual(exit_code, 0)

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-workflows",
                    "--add-workflow",
                    "repository-improvement-audit",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Planned Codex Enhancer workflow-pack management plan", output)
            self.assertIn("repository-improvement-audit: added by --add-workflow", output)
            self.assertIn('Manifest preview selected_workflows = ["repository-improvement-audit"]', output)
            self.assertIn("- overwrite: .codex/enhancer/manifest.toml", output)
            self.assertIn("- create: docs/ai/repo-improvement-audit.md", output)
            self.assertIn("- create: docs/ai/repo-audit-finding-schema.md", output)
            self.assertIn("- create: docs/ai/repo-audit-roadmap-rubric.md", output)
            self.assertIn("- create: .codex/skills/full-repo-improvement-audit/SKILL.md", output)
            self.assertIn("- create: .codex/skills/repo-test-audit/SKILL.md", output)
            self.assertIn("- create: docs/ai/workflow-guidance.md", output)
            self.assertIn("- overwrite: roadmap.md", output)

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-workflows",
                    "--add-workflow",
                    "repository-improvement-audit",
                    "--write",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Applying Codex Enhancer workflow-pack management plan", output)

            manifest = (install_target / ".codex/enhancer/manifest.toml").read_text(encoding="utf-8")
            workflow_guidance = (install_target / "docs/ai/workflow-guidance.md").read_text(encoding="utf-8")
            roadmap = (install_target / "roadmap.md").read_text(encoding="utf-8")

            self.assertIn('selected_workflows = ["repository-improvement-audit"]', manifest)
            self.assertIn("[[detected_workflows]]", manifest)
            self.assertIn('workflow_guidance = "docs/ai/workflow-guidance.md"', manifest)
            self.assertIn('"docs/ai/repo-improvement-audit.md"', manifest)
            self.assertIn('"docs/ai/repo-audit-finding-schema.md"', manifest)
            self.assertIn('"docs/ai/repo-audit-roadmap-rubric.md"', manifest)
            self.assertIn('".codex/skills/full-repo-improvement-audit/SKILL.md"', manifest)
            for skill_name in AUDIT_SPECIALIST_SKILL_NAMES:
                self.assertIn(f'".codex/skills/{skill_name}/SKILL.md"', manifest)
            self.assertIn('"roadmap.md"', manifest)
            self.assertIn("Pack id: `repository-improvement-audit`", workflow_guidance)
            self.assertIn("`repo-test-audit`", workflow_guidance)
            self.assertIn("Keep this product-owned roadmap note.", roadmap)
            self.assertIn("codex-enhancer:managed-section roadmap.md:repository-improvement-audit start", roadmap)
            self.assertTrue((install_target / "docs/ai/repo-improvement-audit.md").exists())
            self.assertTrue((install_target / "docs/ai/repo-audit-finding-schema.md").exists())
            self.assertTrue((install_target / "docs/ai/repo-audit-roadmap-rubric.md").exists())
            self.assertTrue(
                (install_target / ".codex/skills/full-repo-improvement-audit/SKILL.md").exists()
            )
            self.assertFalse(
                (install_target / ".agents/skills/full-repo-improvement-audit/SKILL.md").exists()
            )
            for skill_name in AUDIT_SPECIALIST_SKILL_NAMES:
                self.assertTrue((install_target / f".codex/skills/{skill_name}/SKILL.md").exists())
                self.assertFalse((install_target / f".agents/skills/{skill_name}/SKILL.md").exists())
            self.assertEqual(validate_profile(install_target, TARGET_VALIDATION_PROFILE), [])

    def test_manage_workflows_proposes_existing_audit_workflow_doc(self) -> None:
        with repo_fixture("manage_workflow_existing_doc") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )
            self.assertEqual(exit_code, 0)
            write_file(
                install_target,
                "docs/ai/repo-improvement-audit.md",
                """
                # Custom Audit Notes

                Keep this repo-owned audit note.
                """,
            )

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-workflows",
                    "--add-workflow",
                    "repository-improvement-audit",
                    "--write",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn(
                "- proposal: .codex/enhancer-proposals/docs/ai/repo-improvement-audit.md",
                output,
            )
            live_doc = (install_target / "docs/ai/repo-improvement-audit.md").read_text(encoding="utf-8")
            proposal = (
                install_target
                / ".codex/enhancer-proposals/docs/ai/repo-improvement-audit.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Keep this repo-owned audit note.", live_doc)
            self.assertIn("## Evidence Standards", proposal)

    def test_manage_workflows_preserves_existing_audit_roadmap_section(self) -> None:
        with repo_fixture("manage_workflow_existing_roadmap") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )
            self.assertEqual(exit_code, 0)
            write_file(
                install_target,
                "roadmap.md",
                """
                # Roadmap

                <!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit start -->
                ## Repository Improvement Audit

                - P1: Preserve this audit finding.
                <!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit end -->

                Outside note.
                """,
            )

            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-workflows",
                    "--add-workflow",
                    "repository-improvement-audit",
                    "--write",
                ]
            )

            self.assertEqual(exit_code, 0)
            roadmap = (install_target / "roadmap.md").read_text(encoding="utf-8")
            self.assertNotIn("- P1: Preserve this audit finding.", roadmap)
            self.assertIn("No audit findings recorded yet.", roadmap)
            self.assertIn("Outside note.", roadmap)

    def test_target_validation_rejects_reversed_repository_audit_roadmap_markers(self) -> None:
        with repo_fixture("manage_workflow_reversed_roadmap") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )
            self.assertEqual(exit_code, 0)
            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-workflows",
                    "--add-workflow",
                    "repository-improvement-audit",
                    "--write",
                ]
            )
            self.assertEqual(exit_code, 0)
            write_file(
                install_target,
                "roadmap.md",
                """
                # Roadmap

                <!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit end -->
                reversed content
                <!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit start -->
                """,
            )

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any(
                    "roadmap.md has reversed repository-improvement audit managed markers" in error
                    for error in errors
                )
            )

    def test_target_validation_requires_selected_audit_workflow_assets(self) -> None:
        with repo_fixture("manage_workflow_missing_asset") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )
            self.assertEqual(exit_code, 0)
            manifest_path = install_target / ".codex/enhancer/manifest.toml"
            manifest_text = manifest_path.read_text(encoding="utf-8").replace(
                "selected_workflows = []",
                'selected_workflows = ["repository-improvement-audit"]',
            )
            manifest_path.write_text(manifest_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any(
                    "Missing repository improvement audit workflow file: docs/ai/repo-audit-finding-schema.md" in error
                    for error in errors
                )
            )

    def test_target_validation_requires_selected_workflow_state_to_match_detection_records(self) -> None:
        with repo_fixture("install_workflow_state_drift") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )
            self.assertEqual(exit_code, 0)
            exit_code, _ = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-workflows",
                    "--add-workflow",
                    "repository-improvement-audit",
                    "--write",
                ]
            )
            self.assertEqual(exit_code, 0)

            manifest_path = install_target / ".codex/enhancer/manifest.toml"
            manifest_text = manifest_path.read_text(encoding="utf-8").replace(
                'selected_workflows = ["repository-improvement-audit"]',
                "selected_workflows = []",
            )
            if manifest_text == manifest_path.read_text(encoding="utf-8"):
                self.fail("manifest fixture mutation did not change selected_workflows")
            manifest_path.write_text(manifest_text, encoding="utf-8")

            errors = validate_profile(install_target, TARGET_VALIDATION_PROFILE)

            self.assertTrue(
                any(
                    "detected_workflows selected flags are stale for unselected workflows" in error
                    for error in errors
                )
            )

    def test_manage_workflows_rejects_invalid_flag_combinations(self) -> None:
        with repo_fixture("manage_workflow_invalid") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, output = run_installer(
                ["--target", str(install_target), "--add-workflow", "repository-improvement-audit"]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("require --manage-workflows", output)

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )
            self.assertEqual(exit_code, 0)

            exit_code, output = run_installer(
                ["--target", str(install_target), "--manage-workflows"]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("--manage-workflows requires --add-workflow", output)

            exit_code, output = run_installer(
                [
                    "--target",
                    str(install_target),
                    "--manage-workflows",
                    "--add-workflow",
                    "repository-improvement-audit",
                    "--set-workflow",
                    "repository-improvement-audit",
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("--set-workflow cannot be combined", output)

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

    def test_package_json_commands_respect_package_manager_evidence(self) -> None:
        cases = (
            ("npm_lock", {}, ("package-lock.json",), "npm install", "npm run build", "npm test"),
            ("pnpm_field", {"packageManager": "pnpm@9.0.0"}, (), "pnpm install", "pnpm run build", "pnpm test"),
            ("yarn_lock", {}, ("yarn.lock",), "yarn install", "yarn run build", "yarn test"),
            ("bun_lock", {}, ("bun.lockb",), "bun install", "bun run build", "bun run test"),
        )

        for prefix, package_extra, lockfiles, expected_install, expected_build, expected_test in cases:
            with self.subTest(prefix=prefix):
                with repo_fixture(prefix) as install_target:
                    package_data = {
                        "name": "demo-repo",
                        "scripts": {
                            "build": "vite build",
                            "test": "vitest run",
                        },
                    }
                    package_data.update(package_extra)
                    write_file(install_target, "package.json", json.dumps(package_data))
                    for lockfile in lockfiles:
                        write_file(install_target, lockfile, "\n")

                    commands = discover_commands(install_target)

                    self.assertEqual(commands["install"], expected_install)
                    self.assertEqual(commands["build"], expected_build)
                    self.assertEqual(commands["test"], expected_test)

    def test_python_tests_directory_does_not_guess_pytest(self) -> None:
        with repo_fixture("python_no_pytest_guess") as install_target:
            write_file(install_target, "pyproject.toml", "[project]\nname = \"demo\"\n")
            write_file(install_target, "tests/test_demo.py", "def test_demo():\n    pass\n")

            commands = discover_commands(install_target)

            self.assertEqual(commands["install"], "pip install -e .")
            self.assertNotIn("test", commands)

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

    def test_write_failure_reports_partial_apply_recovery(self) -> None:
        with repo_fixture("install_write_failure") as parent:
            install_target = parent / "repo"
            real_write_text_file = install_enhancer.write_text_file
            write_attempts: list[Path] = []

            def fail_after_first_write(path: Path, content: str) -> None:
                write_attempts.append(path)
                if len(write_attempts) == 2:
                    raise OSError("simulated disk full")
                real_write_text_file(path, content)

            with patch.object(
                install_enhancer,
                "write_text_file",
                side_effect=fail_after_first_write,
            ):
                exit_code, output = run_installer(
                    ["--target", str(install_target), "--mode", "new", "--write"]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("Failed while writing", output)
            self.assertIn("simulated disk full", output)
            self.assertIn("Codex Enhancer does not roll back partial writes", output)
            self.assertIn("Likely enhancer-owned files already touched", output)
            self.assertIn("AGENTS.md", output)

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
            self.assertIn("enable when:", preview)
            self.assertIn("adds:", preview)
            self.assertIn("skip when:", preview)
            self.assertIn("Manifest selected packs: `javascript-typescript-app`", preview)
            self.assertIn(
                "Review `AGENTS.md` and `docs/ai/stack-guidance.md` for selected packs: `javascript-typescript-app`.",
                preview,
            )

    def test_gui_plan_preview_reports_detected_spec_kit_surface(self) -> None:
        with repo_fixture("install_preview_spec_kit") as install_target:
            write_file(
                install_target,
                ".specify/integration.json",
                '{\n  "integration": "copilot",\n  "version": "0.8.3"\n}\n',
            )
            write_file(
                install_target,
                ".specify/init-options.json",
                '{\n  "integration": "copilot",\n  "ai": "copilot",\n  "script": "ps",\n  "speckit_version": "0.8.3"\n}\n',
            )
            write_file(install_target, ".github/prompts/speckit.plan.prompt.md", "# Plan\n")

            plan = build_install_plan(install_target, mode="existing")
            preview = build_plan_preview(plan)

            self.assertIn("Spec Kit bridge:", preview)
            self.assertIn("Official Spec Kit detected.", preview)
            self.assertIn("Integration: `copilot`", preview)
            self.assertIn("Likely command surface: .github/prompts and .github/agents.", preview)

    def test_gui_plan_preview_lists_utility_harness(self) -> None:
        with repo_fixture("install_preview_utility") as install_target:
            write_file(install_target, "README.md", "# Demo\n")
            plan = build_install_plan(
                install_target,
                mode="existing",
                utility_harness_mode="install",
            )
            preview = build_plan_preview(plan)

            self.assertIn("Utility Harness:", preview)
            self.assertIn("Mode: install (installed)", preview)
            self.assertIn("tools/ai/audit_inputs.py", preview)
            self.assertIn("tools/ai/run_checks.py", preview)

    def test_gui_pack_management_preview_and_completion_message(self) -> None:
        with repo_fixture("install_preview_manage") as install_target:
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

            plan = build_pack_management_plan(
                install_target,
                add_packs=("python-service",),
            )
            preview = build_plan_preview(plan)
            message = build_completion_message(plan)

            self.assertIn("Operation: Manage stack packs", preview)
            self.assertIn("Pack management behavior:", preview)
            self.assertIn("After pack management:", preview)
            self.assertIn("Manifest selected packs: `javascript-typescript-app`, `python-service`", preview)
            self.assertIn("Codex Enhancer stack packs were updated successfully.", message)
            self.assertIn("Selected stack packs now:", message)
            self.assertIn("- python-service", message)

    def test_gui_workflow_management_preview_and_completion_message(self) -> None:
        with repo_fixture("install_preview_workflows") as install_target:
            write_file(install_target, "README.md", "# Demo\n")

            exit_code, _ = run_installer(
                ["--target", str(install_target), "--mode", "existing", "--write", "--force"]
            )
            self.assertEqual(exit_code, 0)

            plan = build_workflow_management_plan(
                install_target,
                add_workflows=("repository-improvement-audit",),
            )
            preview = build_plan_preview(plan)
            message = build_completion_message(plan)

            self.assertIn("Operation: Manage workflow packs", preview)
            self.assertIn("Workflow management behavior:", preview)
            self.assertIn("Workflow packs:", preview)
            self.assertIn("Manifest selected workflows: `repository-improvement-audit`", preview)
            self.assertIn("After workflow management:", preview)
            self.assertIn("Codex Enhancer workflow packs were updated successfully.", message)
            self.assertIn("Selected workflow packs now:", message)
            self.assertIn("- repository-improvement-audit", message)
            self.assertIn("roadmap.md managed audit section is present", message)

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

    def test_external_step_fails_before_subprocess_when_executable_is_missing(self) -> None:
        missing_executable = f"missing-codex-enhancer-{uuid.uuid4().hex}"
        step = install_enhancer.ExternalStep(
            argv=(missing_executable,),
            cwd=TEMP_ROOT,
            label="Bootstrap official Spec Kit",
            source_label="official Spec Kit bootstrap",
        )

        with self.assertRaisesRegex(RuntimeError, "was not found") as captured:
            install_enhancer.run_external_step(step)

        message = str(captured.exception)
        self.assertIn("Command:", message)
        self.assertIn(missing_executable, message)
        self.assertIn("Working directory:", message)
        self.assertIn("Recovery:", message)


if __name__ == "__main__":
    unittest.main()
