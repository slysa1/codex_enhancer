from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
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
                "tools/ai/inspect_repo.py",
                "tools/ai/read_any.py",
                "tools/ai/summarize_tree.py",
                "tools/ai/run_checks.py",
            },
        )
        summary = render_utility_harness_summary(config)
        self.assertIn("requirements-codex.txt", summary)
        self.assertIn("requirements-codex-*.txt", summary)
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


if __name__ == "__main__":
    unittest.main()
