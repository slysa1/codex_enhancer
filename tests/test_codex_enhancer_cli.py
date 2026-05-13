from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from scripts import codex_enhancer_cli


class CodexEnhancerCliTests(unittest.TestCase):
    def translate(self, argv: list[str]) -> list[str]:
        parser = codex_enhancer_cli.build_parser()
        return codex_enhancer_cli.translate_to_installer_args(parser.parse_args(argv))

    def test_init_alias_translates_to_install_preview(self) -> None:
        self.assertEqual(
            self.translate(
                [
                    "init",
                    "../target",
                    "--existing",
                    "--recommended",
                    "--pack",
                    "python-service",
                    "--summary",
                    "--diff",
                    "--json",
                    "--utility-harness",
                ]
            ),
            [
                "--target",
                "../target",
                "--mode",
                "existing",
                "--use-recommended-packs",
                "--pack",
                "python-service",
                "--summary",
                "--diff",
                "--json",
                "--utility-harness-mode",
                "install",
            ],
        )

    def test_init_alias_translates_explicit_dry_run_and_full_diff(self) -> None:
        self.assertEqual(
            self.translate(
                [
                    "init",
                    "../target",
                    "--existing",
                    "--dry-run",
                    "--summary",
                    "--diff",
                    "--diff-full",
                ]
            ),
            [
                "--target",
                "../target",
                "--mode",
                "existing",
                "--summary",
                "--diff",
                "--diff-full",
            ],
        )

    def test_audit_translates_to_adaptation_audit(self) -> None:
        self.assertEqual(
            self.translate(["audit", "../target", "--json"]),
            [
                "--target",
                "../target",
                "--audit-adaptation",
                "--json",
            ],
        )

    def test_doctor_defaults_to_current_directory(self) -> None:
        self.assertEqual(
            self.translate(["doctor", "--json"]),
            [
                "--target",
                ".",
                "--doctor",
                "--json",
            ],
        )

    def test_doctor_translates_target_path(self) -> None:
        self.assertEqual(
            self.translate(["doctor", "../target"]),
            [
                "--target",
                "../target",
                "--doctor",
            ],
        )

    def test_install_translates_write_and_spec_kit_options(self) -> None:
        self.assertEqual(
            self.translate(
                [
                    "install",
                    "../target",
                    "--new",
                    "--write",
                    "--force",
                    "--allow-dirty",
                    "--allow-source-target",
                    "--spec-kit",
                    "attach",
                    "--spec-kit-script",
                    "ps",
                    "--spec-kit-command-surface",
                    "slash",
                ]
            ),
            [
                "--target",
                "../target",
                "--mode",
                "new",
                "--write",
                "--force",
                "--allow-dirty",
                "--allow-source-target",
                "--spec-kit-mode",
                "attach",
                "--spec-kit-script",
                "ps",
                "--spec-kit-command-surface",
                "slash",
            ],
        )

    def test_init_can_bundle_spec_kit_and_utility_harness(self) -> None:
        self.assertEqual(
            self.translate(
                [
                    "init",
                    "../target",
                    "--new",
                    "--with-spec-kit",
                    "--utility-harness",
                ]
            ),
            [
                "--target",
                "../target",
                "--mode",
                "new",
                "--spec-kit-mode",
                "bootstrap",
                "--utility-harness-mode",
                "install",
            ],
        )

    def test_upgrade_can_attach_existing_spec_kit(self) -> None:
        self.assertEqual(
            self.translate(["upgrade", "../target", "--attach-spec-kit", "--write"]),
            [
                "--target",
                "../target",
                "--upgrade-enhancer",
                "--write",
                "--spec-kit-mode",
                "attach",
            ],
        )

    def test_pack_management_translates_short_flags(self) -> None:
        self.assertEqual(
            self.translate(
                [
                    "packs",
                    "../target",
                    "--add",
                    "frontend-ui",
                    "--remove",
                    "python-service",
                    "--write",
                ]
            ),
            [
                "--target",
                "../target",
                "--manage-packs",
                "--write",
                "--add-pack",
                "frontend-ui",
                "--remove-pack",
                "python-service",
            ],
        )

    def test_upgrade_can_disable_utility_harness(self) -> None:
        self.assertEqual(
            self.translate(["upgrade", "../target", "--no-utility-harness"]),
            [
                "--target",
                "../target",
                "--upgrade-enhancer",
                "--utility-harness-mode",
                "off",
            ],
        )

    def test_bridge_management_translates_spec_kit_options(self) -> None:
        self.assertEqual(
            self.translate(
                [
                    "bridge",
                    "../target",
                    "--attach-spec-kit",
                    "--spec-kit-command-surface",
                    "dollar",
                    "--write",
                ]
            ),
            [
                "--target",
                "../target",
                "--manage-spec-kit-bridge",
                "--write",
                "--spec-kit-mode",
                "attach",
                "--spec-kit-command-surface",
                "dollar",
            ],
        )

    def test_spec_report_translates_feature_filter(self) -> None:
        self.assertEqual(
            self.translate(["spec-report", "../target", "--feature", "001-login"]),
            [
                "--target",
                "../target",
                "--spec-kit-report",
                "--spec-kit-feature",
                "001-login",
            ],
        )

    def test_spec_sync_translates_feature_changed_paths_and_base(self) -> None:
        self.assertEqual(
            self.translate(
                [
                    "spec-sync",
                    "../target",
                    "--feature",
                    "001-login",
                    "--changed",
                    "src/auth.py",
                    "--changed",
                    "tests/test_auth.py",
                    "--base",
                    "main",
                ]
            ),
            [
                "--target",
                "../target",
                "--spec-kit-sync-report",
                "--spec-kit-feature",
                "001-login",
                "--spec-kit-changed-path",
                "src/auth.py",
                "--spec-kit-changed-path",
                "tests/test_auth.py",
                "--spec-kit-base",
                "main",
            ],
        )

    def test_main_list_packs_delegates_to_installer(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = codex_enhancer_cli.main(["list-packs"])

        self.assertEqual(exit_code, 0)
        self.assertIn("python-service", output.getvalue())


if __name__ == "__main__":
    unittest.main()
