from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import unittest
import uuid
from pathlib import Path

from scripts.utility_harness import (
    UTILITY_HARNESS_DEPENDENCY_FILES,
    UTILITY_HARNESS_REQUIRED_FILES,
    render_utility_harness_summary,
    resolve_utility_harness,
)


class UtilityHarnessTests(unittest.TestCase):
    def test_resolve_utility_harness_defaults_to_off(self) -> None:
        config = resolve_utility_harness()

        self.assertFalse(config.enabled)
        self.assertEqual(config.mode, "off")
        self.assertEqual(config.state, "absent")
        self.assertEqual(config.tool_files, ())
        self.assertIn("not installed", render_utility_harness_summary(config))

    def test_resolve_utility_harness_install_records_files(self) -> None:
        config = resolve_utility_harness(mode="install")

        self.assertTrue(config.enabled)
        self.assertEqual(config.mode, "install")
        self.assertEqual(config.state, "installed")
        self.assertEqual(config.requirements_file, "requirements-codex.txt")
        self.assertEqual(
            set(config.dependency_files),
            {
                "requirements-codex.txt",
                "requirements-codex-minimal.txt",
                "requirements-codex-readers.txt",
                "requirements-codex-analysis.txt",
                "requirements-codex-cli.txt",
            },
        )
        self.assertEqual(config.docs_file, "docs/ai/utility-harness.md")
        self.assertEqual(
            set(config.tool_files),
            {
                "tools/ai/audit_inputs.py",
                "tools/ai/inspect_repo.py",
                "tools/ai/read_any.py",
                "tools/ai/summarize_tree.py",
                "tools/ai/run_checks.py",
            },
        )
        summary = render_utility_harness_summary(config)
        self.assertIn("requirements-codex.txt", summary)
        self.assertIn("requirements-codex-*.txt", summary)
        self.assertIn("tools/ai/audit_inputs.py", summary)
        self.assertIn("tools/ai/run_checks.py", summary)
        self.assertIn("Codex/operator", config.dependency_policy)
        self.assertIn("docs/ai/utility-harness.md", {path.as_posix() for path in UTILITY_HARNESS_REQUIRED_FILES})
        self.assertIn("requirements-codex-readers.txt", {path.as_posix() for path in UTILITY_HARNESS_DEPENDENCY_FILES})

    def test_resolve_utility_harness_preserves_existing_when_mode_is_none(self) -> None:
        existing = resolve_utility_harness(mode="install")

        self.assertIs(resolve_utility_harness(mode=None, existing=existing), existing)

    def test_resolve_utility_harness_rejects_unknown_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown Utility Harness mode"):
            resolve_utility_harness(mode="auto")

    def test_read_any_missing_dependency_points_to_group_file(self) -> None:
        root = Path(__file__).resolve().parents[1]
        module_path = root / "scaffold/target-repo/tools/ai/read_any.py"
        spec = importlib.util.spec_from_file_location("target_read_any", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.dependency_message("python-docx", "DOCX files")

        self.assertIn("requirements-codex-readers.txt", output.getvalue())
        self.assertIn("requirements-codex.txt", output.getvalue())

    def test_audit_inputs_inventory_collects_audit_surfaces_without_running_commands(self) -> None:
        root = Path(__file__).resolve().parents[1]
        module_path = root / "scaffold/target-repo/tools/ai/audit_inputs.py"
        spec = importlib.util.spec_from_file_location("target_audit_inputs", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        fixture_root = Path(__file__).resolve().parent / "_tmp"
        fixture_root.mkdir(parents=True, exist_ok=True)
        repo = fixture_root / f"audit_inputs_{uuid.uuid4().hex}"
        repo.mkdir()
        try:
            write_fixture(repo, "AGENTS.md", "# Repo guidance\n")
            write_fixture(repo, "docs/ai/architecture.md", "# Architecture\n")
            write_fixture(repo, "roadmap.md", "# Roadmap\n")
            write_fixture(repo, "tests/test_app.py", "def test_app():\n    assert True\n")
            write_fixture(repo, ".github/workflows/validate.yml", "name: validate\n")
            write_fixture(repo, ".github/dependabot.yml", "version: 2\n")
            write_fixture(repo, "benchmarks/perf.md", "# Benchmarks\n")
            write_fixture(
                repo,
                "package.json",
                """
                {
                  "scripts": {
                    "check": "node check.js",
                    "test": "node test.js"
                  }
                }
                """,
            )

            inventory = module.build_inventory(
                repo,
                max_files=100,
                max_entries=20,
                include_binary=False,
            )
            self.assertEqual(inventory["roadmap_target"], {"status": "existing", "path": "roadmap.md"})
            self.assertIn("AGENTS.md", inventory["guidance_inputs"])
            self.assertIn("docs/ai/architecture.md", inventory["system_map_inputs"])
            self.assertIn("package.json", inventory["manifest_inputs"])
            self.assertIn("tests/test_app.py", inventory["test_inputs"])
            self.assertIn(".github/workflows/validate.yml", inventory["ci_inputs"])
            self.assertIn(".github/dependabot.yml", inventory["security_inputs"])
            self.assertIn("benchmarks/perf.md", inventory["performance_inputs"])

            commands = inventory["validation_commands"]
            self.assertTrue(any(command["label"] == "package:check" for command in commands))
            self.assertTrue(all("returncode" not in command for command in commands))

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = module.main([str(repo), "--json"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(output.getvalue())["roadmap_target"]["path"], "roadmap.md")
        finally:
            shutil.rmtree(repo, ignore_errors=True)


def write_fixture(root: Path, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
