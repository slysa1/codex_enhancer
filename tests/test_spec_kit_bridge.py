from __future__ import annotations

import json
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from scripts.spec_kit_bridge import (
    build_spec_kit_sync_report,
    detect_spec_kit,
    discover_spec_kit_features,
    render_spec_kit_feature_report,
    render_spec_kit_bridge_summary,
    render_spec_kit_detection_lines,
    render_spec_kit_sync_report,
    resolve_spec_kit_bridge,
)


TEMP_ROOT = Path(__file__).resolve().parent / "_tmp"


def write_file(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(root: Path, relative_path: str, data: dict[str, object]) -> None:
    write_file(root, relative_path, json.dumps(data, indent=2) + "\n")


@contextmanager
def repo_fixture(prefix: str) -> Path:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TEMP_ROOT / f"{prefix}_{uuid.uuid4().hex}"
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class SpecKitBridgeTests(unittest.TestCase):
    def test_detect_spec_kit_returns_not_detected_for_plain_repo(self) -> None:
        with repo_fixture("spec_kit_absent") as root:
            detection = detect_spec_kit(root)

            self.assertFalse(detection.detected)
            self.assertEqual(detection.integration, None)
            self.assertEqual(detection.commands, ())
            self.assertEqual(render_spec_kit_detection_lines(detection), ["- Official Spec Kit not detected."])
            self.assertIn("Spec Kit bridge is off", render_spec_kit_bridge_summary(detection))

    def test_detect_spec_kit_reads_copilot_prompt_and_agent_surface(self) -> None:
        with repo_fixture("spec_kit_copilot") as root:
            write_json(root, ".specify/integration.json", {"integration": "copilot", "version": "0.8.3"})
            write_json(
                root,
                ".specify/init-options.json",
                {
                    "integration": "copilot",
                    "ai": "copilot",
                    "script": "ps",
                    "context_file": ".github/copilot-instructions.md",
                    "speckit_version": "0.8.3",
                },
            )
            write_file(root, ".specify/memory/constitution.md", "# Constitution\n")
            write_file(root, ".specify/extensions/git/README.md", "# Git extension\n")
            write_file(root, ".github/prompts/speckit.plan.prompt.md", "# Plan\n")
            write_file(root, ".github/prompts/speckit.implement.prompt.md", "# Implement\n")
            write_file(root, ".github/agents/speckit.tasks.agent.md", "# Tasks\n")
            write_file(root, ".github/copilot-instructions.md", "<!-- context -->\n")

            detection = detect_spec_kit(root)

            self.assertTrue(detection.detected)
            self.assertEqual(detection.integration, "copilot")
            self.assertEqual(detection.command_surface, "github-prompts-agents")
            self.assertEqual(detection.command_label, ".github/prompts and .github/agents")
            self.assertEqual(detection.script_type, "ps")
            self.assertEqual(detection.version, "0.8.3")
            self.assertEqual(detection.paths.context_file, ".github/copilot-instructions.md")
            self.assertEqual(detection.paths.constitution, ".specify/memory/constitution.md")
            self.assertEqual(detection.commands, ("plan", "tasks", "implement"))
            self.assertTrue(detection.has_git_extension)
            self.assertIn("found .specify/", detection.evidence)
            self.assertIn("found Spec Kit prompt files under .github/prompts/", detection.evidence)
            self.assertIn("git extension hooks configured", detection.evidence)
            self.assertIn(
                "Spec Kit bridge is attached to an existing official install.",
                render_spec_kit_bridge_summary(detection),
            )

    def test_detect_spec_kit_reads_codex_skill_surface(self) -> None:
        with repo_fixture("spec_kit_codex") as root:
            write_json(root, ".specify/integration.json", {"integration": "codex", "version": "0.8.3"})
            write_json(root, ".specify/init-options.json", {"integration": "codex", "script": "ps"})
            write_file(root, ".agents/skills/speckit-plan/SKILL.md", "# Plan\n")
            write_file(root, ".agents/skills/speckit-implement/SKILL.md", "# Implement\n")

            detection = detect_spec_kit(root)

            self.assertTrue(detection.detected)
            self.assertEqual(detection.integration, "codex")
            self.assertEqual(detection.command_surface, "codex-skills")
            self.assertEqual(detection.command_label, "$speckit-<command>")
            self.assertEqual(detection.commands, ("plan", "implement"))
            self.assertEqual(detection.paths.codex_skills_root, ".agents/skills")
            lines = render_spec_kit_detection_lines(detection)
            self.assertTrue(any("$speckit-<command>" in line for line in lines))

    def test_detect_spec_kit_marks_mixed_surfaces_as_ambiguous(self) -> None:
        with repo_fixture("spec_kit_mixed") as root:
            write_json(root, ".specify/integration.json", {"integration": "codex", "version": "0.8.3"})
            write_file(root, ".agents/skills/speckit-plan/SKILL.md", "# Plan\n")
            write_file(root, ".github/prompts/speckit.plan.prompt.md", "# Plan prompt\n")

            detection = detect_spec_kit(root)

            self.assertTrue(detection.detected)
            self.assertEqual(detection.command_surface, "mixed")
            self.assertEqual(detection.command_label, "multiple official Spec Kit surfaces detected")
            self.assertEqual(detection.commands, ("plan",))

    def test_resolve_spec_kit_bridge_attach_uses_detected_install(self) -> None:
        with repo_fixture("spec_kit_attach") as root:
            write_json(root, ".specify/integration.json", {"integration": "codex", "version": "0.8.3"})
            write_json(root, ".specify/init-options.json", {"integration": "codex", "script": "ps"})
            write_file(root, ".agents/skills/speckit-plan/SKILL.md", "# Plan\n")

            bridge = resolve_spec_kit_bridge(root, mode="attach")

            self.assertTrue(bridge.enabled)
            self.assertEqual(bridge.mode, "attach")
            self.assertEqual(bridge.state, "attached")
            self.assertEqual(bridge.integration_key, "codex")
            self.assertEqual(bridge.command_surface, "dollar")
            self.assertEqual(bridge.command_label, "$speckit-<command>")

    def test_resolve_spec_kit_bridge_bootstrap_prepares_external_command(self) -> None:
        with repo_fixture("spec_kit_bootstrap") as root:
            bridge = resolve_spec_kit_bridge(
                root,
                mode="bootstrap",
                script_type="ps",
                version="v0.8.3",
            )

            self.assertTrue(bridge.enabled)
            self.assertEqual(bridge.mode, "bootstrap")
            self.assertEqual(bridge.state, "bootstrapped")
            self.assertEqual(
                bridge.bootstrap_command,
                (
                    "uvx",
                    "--from",
                    "git+https://github.com/github/spec-kit.git@v0.8.3",
                    "specify",
                    "init",
                    "--here",
                    "--integration",
                    "codex",
                    "--script",
                    "ps",
                ),
            )

    def test_resolve_spec_kit_bridge_bootstrap_uses_pinned_default_version(self) -> None:
        with repo_fixture("spec_kit_bootstrap_default") as root:
            bridge = resolve_spec_kit_bridge(root, mode="bootstrap", script_type="sh")

            self.assertEqual(bridge.cli_version, "v0.8.3")
            self.assertIn("git+https://github.com/github/spec-kit.git@v0.8.3", bridge.bootstrap_command)

    def test_feature_report_summarizes_artifacts_and_task_state(self) -> None:
        with repo_fixture("spec_kit_features") as root:
            write_file(root, ".specify/memory/constitution.md", "# Constitution\n")
            write_file(root, "specs/001-login/spec.md", "# Login spec\n")
            write_file(root, "specs/001-login/plan.md", "# Login plan\n")
            write_file(
                root,
                "specs/001-login/tasks.md",
                """
                # Tasks
                - [x] T001 Build auth form
                - [ ] T002 Add validation
                """,
            )
            write_file(root, "specs/001-login/contracts/openapi.yaml", "openapi: 3.1.0\n")
            write_file(root, "specs/002-search/spec.md", "# Search spec\n")

            summaries = discover_spec_kit_features(root)
            report = render_spec_kit_feature_report(root, feature="001")

            self.assertEqual([summary.name for summary in summaries], ["001-login", "002-search"])
            self.assertEqual(summaries[0].task_total, 2)
            self.assertEqual(summaries[0].task_done, 1)
            self.assertEqual(summaries[0].task_open, 1)
            self.assertIn("`001-login` at `specs/001-login`", report)
            self.assertIn("`contracts/ (1 file)`", report)
            self.assertIn("Tasks: 2 total, 1 done, 1 open", report)
            self.assertNotIn("002-search", report)

    def test_feature_report_handles_missing_specs_directory(self) -> None:
        with repo_fixture("spec_kit_no_specs") as root:
            report = render_spec_kit_feature_report(root)

            self.assertIn("Official Spec Kit not detected", report)
            self.assertIn("No `specs/` directory was found.", report)

    def test_sync_report_links_changed_paths_to_feature_artifacts(self) -> None:
        with repo_fixture("spec_kit_sync") as root:
            write_file(root, ".specify/integration.json", '{"integration": "codex"}\n')
            write_file(root, "specs/001-login/spec.md", "# Login spec\n")
            write_file(root, "specs/001-login/plan.md", "# Login plan\n")
            write_file(
                root,
                "specs/001-login/tasks.md",
                """
                # Tasks
                - [x] T001 Build auth form
                - [ ] T002 Add validation
                """,
            )
            write_file(root, "specs/001-login/quickstart.md", "# Quickstart\n")
            write_file(root, "specs/001-login/contracts/openapi.yaml", "openapi: 3.1.0\n")

            sync = build_spec_kit_sync_report(
                root,
                feature="001",
                changed_paths=("src/auth.py", "tests/test_auth.py"),
            )
            rendered = render_spec_kit_sync_report(
                root,
                feature="001",
                changed_paths=("src/auth.py", "tests/test_auth.py"),
            )

            self.assertEqual(sync.changed_paths, ("src/auth.py", "tests/test_auth.py"))
            self.assertIn("specs/001-login/spec.md", sync.artifact_paths)
            self.assertIn("`001-login` still has 1 open task(s).", sync.notes)
            self.assertIn("Spec Kit sync report", rendered)
            self.assertIn("Artifacts to re-read:", rendered)
            self.assertIn("`src/auth.py`", rendered)
            self.assertIn("Changed path categories: source: 1, tests: 1.", rendered)

    def test_sync_report_reports_missing_changed_paths_and_git_errors(self) -> None:
        with repo_fixture("spec_kit_sync_git_error") as root:
            write_file(root, "specs/001-login/spec.md", "# Login spec\n")

            report = render_spec_kit_sync_report(
                root,
                feature="001",
                git_base="definitely-not-a-ref",
            )

            self.assertIn("Spec Kit sync report", report)
            self.assertIn("Git base: `definitely-not-a-ref`", report)
            self.assertIn("Git diff unavailable:", report)
            self.assertIn("No changed paths were supplied", report)


if __name__ == "__main__":
    unittest.main()
