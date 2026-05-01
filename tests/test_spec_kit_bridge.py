from __future__ import annotations

import json
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from scripts.spec_kit_bridge import (
    detect_spec_kit,
    render_spec_kit_bridge_summary,
    render_spec_kit_detection_lines,
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


if __name__ == "__main__":
    unittest.main()
