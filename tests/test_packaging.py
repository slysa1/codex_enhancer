from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from codex_enhancer.package_assets import asset_path
from scripts.enhancer_spec import ENHANCER_VERSION


class PackagingMetadataTests(unittest.TestCase):
    def load_pyproject(self) -> dict[str, object]:
        root = Path(__file__).resolve().parents[1]
        return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def test_console_script_points_to_cli_facade(self) -> None:
        pyproject = self.load_pyproject()
        project = pyproject["project"]

        self.assertEqual(project["name"], "codex-enhancer")
        self.assertEqual(project["license"], "GPL-3.0-or-later")
        self.assertEqual(project["license-files"], ["LICENSE"])
        self.assertEqual(project["requires-python"], ">=3.13")
        self.assertIn("Operating System :: OS Independent", project["classifiers"])
        self.assertIn("Programming Language :: Python :: 3 :: Only", project["classifiers"])
        self.assertIn("Programming Language :: Python :: 3.13", project["classifiers"])
        self.assertEqual(
            project["scripts"]["codex-enhancer"],
            "scripts.codex_enhancer_cli:main",
        )
        self.assertIn("codex_enhancer*", pyproject["tool"]["setuptools"]["packages"]["find"]["include"])

    def test_package_version_comes_from_enhancer_spec(self) -> None:
        pyproject = self.load_pyproject()

        self.assertEqual(pyproject["project"]["dynamic"], ["version"])
        self.assertEqual(
            pyproject["tool"]["setuptools"]["dynamic"]["version"]["attr"],
            "scripts.enhancer_spec.ENHANCER_VERSION",
        )
        self.assertRegex(ENHANCER_VERSION, r"^\d+\.\d+\.\d+$")

    def test_packaged_assets_mirror_runtime_scaffold_inputs(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packaged_root = root / "codex_enhancer/assets/root"
        source_roots = (root / "scaffold", root / ".codex/skills")

        self.assertEqual(asset_path("scaffold/stack-packs").resolve(), (root / "scaffold/stack-packs").resolve())
        self.assertTrue((packaged_root / "README.md").is_file())
        self.assertEqual(
            (packaged_root / "README.md").read_text(encoding="utf-8"),
            (root / "README.md").read_text(encoding="utf-8"),
        )

        for source_root in source_roots:
            for source_path in source_root.rglob("*"):
                if source_path.is_dir() or "__pycache__" in source_path.parts or source_path.suffix == ".pyc":
                    continue
                relative_path = source_path.relative_to(root)
                packaged_path = packaged_root / relative_path
                self.assertTrue(packaged_path.is_file(), relative_path.as_posix())
                self.assertEqual(
                    packaged_path.read_text(encoding="utf-8"),
                    source_path.read_text(encoding="utf-8"),
                    relative_path.as_posix(),
                )

    def test_release_checklist_and_manifest_exclude_generated_build_noise(self) -> None:
        root = self.repo_root()
        release_doc = (root / "docs/ai/release.md").read_text(encoding="utf-8")
        manifest = (root / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertIn("Package metadata requires Python `>=3.13`", release_doc)
        self.assertIn("Ubuntu, Windows, and macOS", release_doc)
        self.assertIn("python codex-enhancer ...", release_doc)
        self.assertIn("python -m build", release_doc)
        self.assertIn("codex-enhancer list-packs", release_doc)
        self.assertIn("requirements-codex.txt", release_doc)
        self.assertIn("global-exclude __pycache__ *.py[cod]", manifest)

    def test_ci_matrix_matches_declared_python_and_platform_support(self) -> None:
        root = self.repo_root()
        workflow = (root / ".github/workflows/validate.yml").read_text(encoding="utf-8")

        self.assertIn("ubuntu-latest", workflow)
        self.assertIn("windows-latest", workflow)
        self.assertIn("macos-latest", workflow)
        self.assertIn('python-version:\n          - "3.13"', workflow)
        self.assertIn("python -m venv .venv-smoke", workflow)
        self.assertIn("$IsWindows", workflow)
        self.assertIn("codex-enhancer.exe", workflow)
        self.assertIn("$codex init tests/_tmp/ci-wheel-smoke-full --new --with-spec-kit --utility-harness", workflow)


if __name__ == "__main__":
    unittest.main()
