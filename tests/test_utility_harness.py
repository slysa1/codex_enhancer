from __future__ import annotations

import unittest

from scripts.utility_harness import (
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
        self.assertIn("tools/ai/run_checks.py", summary)
        self.assertIn("Codex/operator", config.dependency_policy)
        self.assertIn("docs/ai/utility-harness.md", {path.as_posix() for path in UTILITY_HARNESS_REQUIRED_FILES})

    def test_resolve_utility_harness_preserves_existing_when_mode_is_none(self) -> None:
        existing = resolve_utility_harness(mode="install")

        self.assertIs(resolve_utility_harness(mode=None, existing=existing), existing)

    def test_resolve_utility_harness_rejects_unknown_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown Utility Harness mode"):
            resolve_utility_harness(mode="auto")


if __name__ == "__main__":
    unittest.main()
