from __future__ import annotations

import shutil
import textwrap
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from scripts.enhancer_spec import ENHANCER_VERSION
from scripts.stack_packs import (
    detect_stack_packs,
    load_enhancer_install_state,
    load_selected_packs_from_manifest,
    load_stack_packs,
    render_agents_summary,
    render_install_follow_up_lines,
    render_pack_fragment,
    render_stack_pack_manifest,
    resolve_manifest_pack_selection,
    resolve_stack_pack_selection,
)


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


class StackPackTests(unittest.TestCase):
    def test_load_stack_packs_returns_expected_pack_names(self) -> None:
        packs = load_stack_packs()

        self.assertEqual(
            tuple(pack.name for pack in packs),
            (
                "monorepo-workspace",
                "javascript-typescript-app",
                "frontend-ui",
                "python-service",
                "node-api-service",
            ),
        )

    def test_detects_monorepo_pack_from_workspace_file(self) -> None:
        with repo_fixture("pack_monorepo") as root:
            write_file(root, "pnpm-workspace.yaml", "packages:\n  - packages/*\n")

            detections = detect_stack_packs(root)
            detected_names = {item.pack.name for item in detections if item.detected}

            self.assertIn("monorepo-workspace", detected_names)

    def test_detects_javascript_pack_from_manifest_and_tooling(self) -> None:
        with repo_fixture("pack_js") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "tsconfig.json", "{}\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}

            self.assertTrue(detected["javascript-typescript-app"].detected)
            self.assertTrue(detected["javascript-typescript-app"].recommended)
            self.assertIn("package.json", "; ".join(detected["javascript-typescript-app"].reasons))

    def test_detects_python_pack_from_pyproject(self) -> None:
        with repo_fixture("pack_python") as root:
            write_file(
                root,
                "pyproject.toml",
                """
                [project]
                name = "demo"
                version = "0.1.0"
                """,
            )

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}

            self.assertTrue(detected["python-service"].detected)
            self.assertTrue(detected["python-service"].recommended)

    def test_detects_frontend_ui_pack_from_component_source(self) -> None:
        with repo_fixture("pack_frontend") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "src/App.tsx", "export function App() { return <main />; }\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}

            self.assertTrue(detected["frontend-ui"].detected)
            self.assertTrue(detected["frontend-ui"].recommended)
            self.assertIn("src/App.tsx", "; ".join(detected["frontend-ui"].reasons))

    def test_detects_node_api_pack_from_server_entrypoint(self) -> None:
        with repo_fixture("pack_node_api") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "src/server.ts", "export const server = {};\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}

            self.assertTrue(detected["node-api-service"].detected)
            self.assertTrue(detected["node-api-service"].recommended)
            self.assertIn("src/server.ts", "; ".join(detected["node-api-service"].reasons))

    def test_render_pack_fragment_includes_pack_label(self) -> None:
        pack = next(pack for pack in load_stack_packs() if pack.name == "python-service")

        rendered = render_pack_fragment(pack, "stack_guidance")

        self.assertIn("## Python service", rendered)
        self.assertIn("pyproject.toml", rendered)

    def test_render_stack_pack_manifest_records_detection_and_selection(self) -> None:
        with repo_fixture("pack_manifest") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "tsconfig.json", "{}\n")

            detections = detect_stack_packs(root)
            manifest = render_stack_pack_manifest(
                detections,
                selected_packs=("javascript-typescript-app",),
                safe_to_regenerate=(
                    Path("docs/ai/stack-guidance.md"),
                    Path(".codex/enhancer/manifest.toml"),
                ),
                adapt_manually=(Path("AGENTS.md"),),
            )

            self.assertIn('selected_packs = ["javascript-typescript-app"]', manifest)
            self.assertIn(f'enhancer_version = "{ENHANCER_VERSION}"', manifest)
            self.assertIn('name = "javascript-typescript-app"', manifest)
            self.assertIn("selected = true", manifest)
            self.assertIn('stack_guidance = "docs/ai/stack-guidance.md"', manifest)
            self.assertIn(
                'safe_to_regenerate = ["docs/ai/stack-guidance.md", ".codex/enhancer/manifest.toml"]',
                manifest,
            )
            self.assertIn('adapt_manually = ["AGENTS.md"]', manifest)

    def test_render_agents_summary_compacts_selected_pack_guidance(self) -> None:
        with repo_fixture("pack_agents_summary") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "tsconfig.json", "{}\n")

            detections = detect_stack_packs(root)
            selections = resolve_stack_pack_selection(detections, use_recommended_packs=True)
            summary = render_agents_summary(selections)

            self.assertIn("Selected packs: `javascript-typescript-app`", summary)
            self.assertIn("`javascript-typescript-app` (JavaScript / TypeScript app):", summary)
            self.assertIn("Respect the repo's actual package manager and lockfile", summary)

    def test_render_agents_summary_supports_multiple_selected_packs(self) -> None:
        with repo_fixture("pack_agents_summary_multi") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "tsconfig.json", "{}\n")
            write_file(root, "src/App.tsx", "export function App() { return <main />; }\n")

            detections = detect_stack_packs(root)
            selections = resolve_stack_pack_selection(detections, use_recommended_packs=True)
            summary = render_agents_summary(selections)

            self.assertIn("Selected packs: `javascript-typescript-app`, `frontend-ui`", summary)
            self.assertIn("`frontend-ui` (Frontend UI):", summary)
            self.assertIn("Check loading, empty, error, and success states", summary)

    def test_load_selected_packs_from_manifest_reads_existing_selection(self) -> None:
        with repo_fixture("pack_manifest_read") as root:
            write_file(
                root,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = 1
                enhancer_version = "%s"
                selected_packs = ["python-service"]
                """ % ENHANCER_VERSION,
            )

            selected = load_selected_packs_from_manifest(root)

            self.assertEqual(selected, ("python-service",))

    def test_load_enhancer_install_state_reads_version_and_ownership(self) -> None:
        with repo_fixture("pack_install_state") as root:
            write_file(
                root,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = 1
                enhancer_version = "%s"
                selected_packs = ["python-service"]

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md"]
                adapt_manually = ["AGENTS.md"]
                """ % ENHANCER_VERSION,
            )

            state = load_enhancer_install_state(root)

            self.assertEqual(state.enhancer_version, ENHANCER_VERSION)
            self.assertEqual(state.selected_packs, ("python-service",))
            self.assertEqual(state.safe_to_regenerate, ("docs/ai/stack-guidance.md",))
            self.assertEqual(state.adapt_manually, ("AGENTS.md",))

    def test_resolve_manifest_pack_selection_marks_selected_packs(self) -> None:
        with repo_fixture("pack_manifest_selection") as root:
            write_file(
                root,
                "pyproject.toml",
                """
                [project]
                name = "demo"
                version = "0.1.0"
                """,
            )

            detections = detect_stack_packs(root)
            selections = resolve_manifest_pack_selection(
                detections,
                selected_packs=("python-service",),
            )

            selected = next(item for item in selections if item.pack.name == "python-service")
            self.assertTrue(selected.selected)
            self.assertEqual(selected.selection_source, "manifest")

    def test_render_install_follow_up_lines_uses_selected_pack_summaries(self) -> None:
        with repo_fixture("pack_follow_up") as root:
            write_file(
                root,
                "pyproject.toml",
                """
                [project]
                name = "demo"
                version = "0.1.0"
                """,
            )

            detections = detect_stack_packs(root)
            selections = resolve_stack_pack_selection(detections, use_recommended_packs=True)
            lines = render_install_follow_up_lines(selections)

            self.assertIn(
                "- Review `AGENTS.md` and `docs/ai/stack-guidance.md` for selected packs: `python-service`.",
                lines,
            )
            self.assertTrue(any("`python-service`:" in line for line in lines))
            self.assertTrue(any("existing env, test, lint, and type tools" in line for line in lines))

    def test_render_install_follow_up_lines_include_node_api_summary(self) -> None:
        with repo_fixture("pack_follow_up_node_api") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "tsconfig.json", "{}\n")
            write_file(root, "src/server.ts", "export const server = {};\n")

            detections = detect_stack_packs(root)
            selections = resolve_stack_pack_selection(detections, use_recommended_packs=True)
            lines = render_install_follow_up_lines(selections)

            self.assertIn(
                "- Review `AGENTS.md` and `docs/ai/stack-guidance.md` for selected packs: `javascript-typescript-app`, `node-api-service`.",
                lines,
            )
            self.assertTrue(any("`node-api-service`:" in line for line in lines))
            self.assertTrue(any("auth, validation, and error behavior" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
