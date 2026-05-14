from __future__ import annotations

import shutil
import textwrap
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from scripts.enhancer_spec import ENHANCER_MANIFEST_SCHEMA_VERSION, ENHANCER_VERSION
from scripts.stack_packs import (
    detect_stack_packs,
    load_enhancer_install_state,
    load_selected_packs_from_manifest,
    load_stack_pack,
    load_stack_packs,
    render_agents_summary,
    render_install_follow_up_lines,
    render_pack_fragment,
    render_stack_pack_manifest,
    resolve_manifest_pack_selection,
    resolve_managed_pack_selection,
    resolve_stack_pack_selection,
)
from scripts.utility_harness import resolve_utility_harness


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
                "library-package",
            ),
        )
        for pack in packs:
            self.assertTrue(pack.guidance.use_when)
            self.assertTrue(pack.guidance.adds)
            self.assertTrue(pack.guidance.skip_when)

    def test_repository_improvement_workflow_pack_uses_stack_pack_loader(self) -> None:
        workflow_root = Path(__file__).resolve().parents[1] / "scaffold/workflow-packs"

        packs = load_stack_packs(workflow_root)

        self.assertEqual(tuple(pack.name for pack in packs), ("repository-improvement-audit",))
        pack = packs[0]
        self.assertEqual(pack.label, "Repository improvement audit")
        self.assertEqual(pack.render.stack_guidance, Path("fragments/workflow-guidance.md"))
        self.assertTrue(pack.guidance.use_when)
        self.assertTrue(pack.guidance.adds)
        self.assertTrue(pack.guidance.skip_when)

    def test_repository_improvement_workflow_pack_renders_with_stack_pack_fragment(self) -> None:
        workflow_root = Path(__file__).resolve().parents[1] / "scaffold/workflow-packs"
        pack = load_stack_packs(workflow_root)[0]

        rendered = render_pack_fragment(pack, "stack_guidance")

        self.assertIn("## Repository improvement audit", rendered)
        self.assertIn("repo-audit-finding-schema.md", rendered)

    def test_repository_improvement_workflow_pack_is_manual_by_default(self) -> None:
        workflow_root = Path(__file__).resolve().parents[1] / "scaffold/workflow-packs"
        packs = load_stack_packs(workflow_root)
        with repo_fixture("workflow_pack_detection") as root:
            write_file(root, "AGENTS.md", "# Demo\n")

            detection = detect_stack_packs(root, packs=packs)[0]

            self.assertFalse(detection.detected)
            self.assertFalse(detection.recommended)
            self.assertIn("missing detection signal", "; ".join(detection.reasons))

    def test_repository_improvement_workflow_pack_can_use_manual_marker(self) -> None:
        workflow_root = Path(__file__).resolve().parents[1] / "scaffold/workflow-packs"
        packs = load_stack_packs(workflow_root)
        with repo_fixture("workflow_pack_manual_marker") as root:
            write_file(root, ".codex/enhancer/workflows/repository-improvement-audit.toml", "selected = true\n")

            detection = detect_stack_packs(root, packs=packs)[0]

            self.assertTrue(detection.detected)
            self.assertFalse(detection.recommended)
            self.assertIn(".codex/enhancer/workflows/repository-improvement-audit.toml", "; ".join(detection.reasons))

    def test_invalid_workflow_pack_metadata_is_rejected_by_stack_pack_loader(self) -> None:
        with repo_fixture("workflow_pack_bad_metadata") as root:
            pack_root = root / "repository-improvement-audit"
            write_file(
                pack_root,
                "pack.toml",
                """
                schema_version = 99
                name = "repository-improvement-audit"
                label = "Repository improvement audit"
                description = "Read-only repository audit workflow."
                version = "0.1.0"

                [discovery]
                any_files = [".codex/enhancer/workflows/repository-improvement-audit.toml"]

                [ui]
                recommended_if_detected = false
                default_selected = false
                order = 10

                [guidance]
                use_when = ["Use for read-only repo audits."]
                adds = ["Adds audit guidance."]
                skip_when = ["Skip for direct implementation."]

                [render]
                agents_summary = "fragments/agents-summary.md"
                stack_guidance = "fragments/workflow-guidance.md"
                review_notes = "fragments/review-notes.md"
                """,
            )
            write_file(pack_root, "fragments/agents-summary.md", "Summary.\n")
            write_file(pack_root, "fragments/workflow-guidance.md", "Guidance.\n")
            write_file(pack_root, "fragments/review-notes.md", "Review notes.\n")

            with self.assertRaisesRegex(ValueError, "Unsupported stack pack schema_version"):
                load_stack_pack(pack_root)

    def test_missing_workflow_pack_guidance_metadata_is_rejected_by_stack_pack_loader(self) -> None:
        with repo_fixture("workflow_pack_missing_guidance_metadata") as root:
            pack_root = root / "repository-improvement-audit"
            write_file(
                pack_root,
                "pack.toml",
                """
                schema_version = 1
                name = "repository-improvement-audit"
                label = "Repository improvement audit"
                description = "Read-only repository audit workflow."
                version = "0.1.0"

                [discovery]
                any_files = [".codex/enhancer/workflows/repository-improvement-audit.toml"]

                [ui]
                recommended_if_detected = false
                default_selected = false
                order = 10

                [render]
                agents_summary = "fragments/agents-summary.md"
                stack_guidance = "fragments/workflow-guidance.md"
                review_notes = "fragments/review-notes.md"
                """,
            )
            write_file(pack_root, "fragments/agents-summary.md", "Summary.\n")
            write_file(pack_root, "fragments/workflow-guidance.md", "Guidance.\n")
            write_file(pack_root, "fragments/review-notes.md", "Review notes.\n")

            with self.assertRaisesRegex(ValueError, "Expected table section 'guidance'"):
                load_stack_pack(pack_root)

    def test_missing_workflow_pack_fragment_is_rejected_by_stack_pack_loader(self) -> None:
        with repo_fixture("workflow_pack_missing_fragment") as root:
            pack_root = root / "repository-improvement-audit"
            write_file(
                pack_root,
                "pack.toml",
                """
                schema_version = 1
                name = "repository-improvement-audit"
                label = "Repository improvement audit"
                description = "Read-only repository audit workflow."
                version = "0.1.0"

                [discovery]
                any_files = [".codex/enhancer/workflows/repository-improvement-audit.toml"]

                [ui]
                recommended_if_detected = false
                default_selected = false
                order = 10

                [guidance]
                use_when = ["Use for read-only repo audits."]
                adds = ["Adds audit guidance."]
                skip_when = ["Skip for direct implementation."]

                [render]
                agents_summary = "fragments/agents-summary.md"
                stack_guidance = "fragments/workflow-guidance.md"
                review_notes = "fragments/review-notes.md"
                """,
            )
            write_file(pack_root, "fragments/agents-summary.md", "Summary.\n")
            write_file(pack_root, "fragments/workflow-guidance.md", "Guidance.\n")

            with self.assertRaisesRegex(ValueError, "missing fragment fragments/review-notes.md"):
                load_stack_pack(pack_root)

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

    def test_javascript_pack_records_manifest_evidence(self) -> None:
        with repo_fixture("pack_js_evidence") as root:
            write_file(
                root,
                "package.json",
                """
                {
                  "name": "demo",
                  "packageManager": "pnpm@9.0.0",
                  "scripts": {
                    "build": "vite build",
                    "test": "vitest run",
                    "dev": "vite"
                  },
                  "dependencies": {
                    "react": "latest"
                  },
                  "devDependencies": {
                    "typescript": "latest",
                    "vite": "latest"
                  }
                }
                """,
            )
            write_file(root, "tsconfig.json", "{}\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}
            reasons = detected["javascript-typescript-app"].reasons

            self.assertIn("package manager: pnpm from package.json packageManager", reasons)
            self.assertIn("package.json scripts: build, test, dev", reasons)
            self.assertIn("package.json packages: typescript, vite, react", reasons)

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

    def test_python_pack_records_pyproject_evidence(self) -> None:
        with repo_fixture("pack_python_evidence") as root:
            write_file(
                root,
                "pyproject.toml",
                """
                [build-system]
                requires = ["hatchling"]
                build-backend = "hatchling.build"

                [project]
                name = "demo"
                version = "0.1.0"

                [tool.pytest.ini_options]
                testpaths = ["tests"]

                [tool.ruff]
                line-length = 100
                """,
            )

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}
            reasons = detected["python-service"].reasons

            self.assertIn("pyproject build backend: hatchling.build", reasons)
            self.assertIn("pyproject tool tables: pytest, ruff", reasons)

    def test_detects_frontend_ui_pack_from_component_source(self) -> None:
        with repo_fixture("pack_frontend") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "src/App.tsx", "export function App() { return <main />; }\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}

            self.assertTrue(detected["frontend-ui"].detected)
            self.assertTrue(detected["frontend-ui"].recommended)
            self.assertIn("src/App.tsx", "; ".join(detected["frontend-ui"].reasons))

    def test_frontend_ui_pack_records_package_evidence(self) -> None:
        with repo_fixture("pack_frontend_evidence") as root:
            write_file(
                root,
                "package.json",
                """
                {
                  "name": "demo",
                  "packageManager": "bun@1.1.0",
                  "scripts": {
                    "build": "vite build",
                    "dev": "vite",
                    "preview": "vite preview"
                  },
                  "dependencies": {
                    "react": "latest"
                  },
                  "devDependencies": {
                    "@vitejs/plugin-react": "latest",
                    "vite": "latest"
                  }
                }
                """,
            )
            write_file(root, "src/App.tsx", "export function App() { return <main />; }\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}
            reasons = detected["frontend-ui"].reasons

            self.assertIn("package manager: bun from package.json packageManager", reasons)
            self.assertIn("package.json scripts: build, dev, preview", reasons)
            self.assertIn("package.json packages: react, @vitejs/plugin-react, vite", reasons)

    def test_detects_node_api_pack_from_server_entrypoint(self) -> None:
        with repo_fixture("pack_node_api") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "src/server.ts", "export const server = {};\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}

            self.assertTrue(detected["node-api-service"].detected)
            self.assertTrue(detected["node-api-service"].recommended)
            self.assertIn("src/server.ts", "; ".join(detected["node-api-service"].reasons))

    def test_node_api_pack_records_package_evidence(self) -> None:
        with repo_fixture("pack_node_api_evidence") as root:
            write_file(
                root,
                "package.json",
                """
                {
                  "name": "demo",
                  "scripts": {
                    "start": "node dist/server.js",
                    "dev": "tsx src/server.ts",
                    "test": "vitest run"
                  },
                  "dependencies": {
                    "express": "latest",
                    "zod": "latest"
                  }
                }
                """,
            )
            write_file(root, "yarn.lock", "# yarn lock\n")
            write_file(root, "src/server.ts", "export const server = {};\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}
            reasons = detected["node-api-service"].reasons

            self.assertIn("package manager: yarn from yarn.lock", reasons)
            self.assertIn("package.json scripts: start, dev, test", reasons)
            self.assertIn("package.json packages: express, zod", reasons)

    def test_detects_library_package_from_explicit_package_metadata(self) -> None:
        with repo_fixture("pack_library") as root:
            write_file(
                root,
                "package.json",
                """
                {
                  "name": "@scope/demo-library",
                  "packageManager": "pnpm@9.0.0",
                  "exports": {
                    ".": {
                      "types": "./dist/index.d.ts",
                      "import": "./dist/index.js"
                    }
                  },
                  "types": "./dist/index.d.ts",
                  "files": ["dist"],
                  "scripts": {
                    "build": "tsup src/index.ts",
                    "test": "vitest run",
                    "typecheck": "tsc --noEmit"
                  },
                  "devDependencies": {
                    "typescript": "latest",
                    "tsup": "latest"
                  }
                }
                """,
            )
            write_file(root, "tsconfig.json", "{}\n")
            write_file(root, "src/index.ts", "export const value = 1;\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}
            reasons = detected["library-package"].reasons

            self.assertTrue(detected["library-package"].detected)
            self.assertTrue(detected["library-package"].recommended)
            self.assertIn("package.json library fields: exports, types, files", reasons)
            self.assertIn("package manager: pnpm from package.json packageManager", reasons)
            self.assertIn("package.json scripts: build, test, typecheck", reasons)
            self.assertIn("package.json packages: typescript, tsup", reasons)

    def test_library_package_is_not_detected_for_normal_app_manifest(self) -> None:
        with repo_fixture("pack_library_app") as root:
            write_file(
                root,
                "package.json",
                """
                {
                  "name": "demo-app",
                  "scripts": {
                    "build": "vite build",
                    "dev": "vite"
                  },
                  "dependencies": {
                    "react": "latest"
                  }
                }
                """,
            )
            write_file(root, "tsconfig.json", "{}\n")
            write_file(root, "src/App.tsx", "export function App() { return <main />; }\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}

            self.assertFalse(detected["library-package"].detected)
            self.assertIn(
                "missing library package metadata",
                "; ".join(detected["library-package"].reasons),
            )

    def test_library_package_is_suppressed_by_service_entrypoints(self) -> None:
        with repo_fixture("pack_library_service_signal") as root:
            write_file(
                root,
                "package.json",
                """
                {
                  "name": "demo-service",
                  "main": "./dist/server.js",
                  "types": "./dist/server.d.ts",
                  "scripts": {
                    "build": "tsc",
                    "start": "node dist/server.js"
                  }
                }
                """,
            )
            write_file(root, "src/server.ts", "export const server = {};\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}

            self.assertFalse(detected["library-package"].detected)
            self.assertIn(
                "app or service signals suppress library-package",
                "; ".join(detected["library-package"].reasons),
            )

    def test_manifest_evidence_tolerates_invalid_package_json(self) -> None:
        with repo_fixture("pack_invalid_package_json") as root:
            write_file(root, "package.json", "{not json\n")
            write_file(root, "tsconfig.json", "{}\n")

            detections = detect_stack_packs(root)
            detected = {item.pack.name: item for item in detections}

            self.assertTrue(detected["javascript-typescript-app"].detected)
            self.assertNotIn(
                "package.json scripts:",
                "; ".join(detected["javascript-typescript-app"].reasons),
            )

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
            self.assertIn(f"schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}", manifest)
            self.assertIn(f'enhancer_version = "{ENHANCER_VERSION}"', manifest)
            self.assertIn("[lifecycle]", manifest)
            self.assertIn('state = "active"', manifest)
            self.assertIn('pack_selection = "manifest"', manifest)
            self.assertIn(MANAGED_SECTION_LIST, manifest)
            self.assertIn('name = "javascript-typescript-app"', manifest)
            self.assertIn("selected = true", manifest)
            self.assertIn('evidence = ["found package.json", "matched tsconfig.json"]', manifest)
            self.assertIn('stack_guidance = "docs/ai/stack-guidance.md"', manifest)
            self.assertIn(
                'safe_to_regenerate = ["docs/ai/stack-guidance.md", ".codex/enhancer/manifest.toml"]',
                manifest,
            )
            self.assertIn('adapt_manually = ["AGENTS.md"]', manifest)

    def test_render_stack_pack_manifest_records_manifest_evidence(self) -> None:
        with repo_fixture("pack_manifest_evidence") as root:
            write_file(
                root,
                "package.json",
                """
                {
                  "name": "demo",
                  "packageManager": "pnpm@9.0.0",
                  "scripts": {
                    "build": "vite build"
                  },
                  "devDependencies": {
                    "typescript": "latest",
                    "vite": "latest"
                  }
                }
                """,
            )
            write_file(root, "tsconfig.json", "{}\n")

            detections = detect_stack_packs(root)
            manifest = render_stack_pack_manifest(
                detections,
                selected_packs=("javascript-typescript-app",),
            )

            self.assertIn("package manager: pnpm from package.json packageManager", manifest)
            self.assertIn("package.json scripts: build", manifest)
            self.assertIn("package.json packages: typescript, vite", manifest)

    def test_render_stack_pack_manifest_records_utility_harness_state(self) -> None:
        with repo_fixture("pack_manifest_utility") as root:
            detections = detect_stack_packs(root)
            manifest = render_stack_pack_manifest(
                detections,
                utility_harness=resolve_utility_harness(mode="install"),
            )

            self.assertIn("[integrations.utility_harness]", manifest)
            self.assertIn('mode = "install"', manifest)
            self.assertIn('state = "installed"', manifest)
            self.assertIn('requirements_file = "requirements-codex.txt"', manifest)
            self.assertIn('"requirements-codex-readers.txt"', manifest)
            self.assertIn('"tools/ai/run_checks.py"', manifest)

    def test_render_agents_summary_supports_library_package_with_javascript_pack(self) -> None:
        with repo_fixture("pack_agents_summary_library") as root:
            write_file(
                root,
                "package.json",
                """
                {
                  "name": "@scope/demo-library",
                  "exports": "./dist/index.js",
                  "types": "./dist/index.d.ts",
                  "files": ["dist"],
                  "scripts": {
                    "build": "tsup src/index.ts",
                    "test": "vitest run"
                  },
                  "devDependencies": {
                    "typescript": "latest",
                    "tsup": "latest"
                  }
                }
                """,
            )
            write_file(root, "tsconfig.json", "{}\n")

            detections = detect_stack_packs(root)
            selections = resolve_stack_pack_selection(detections, use_recommended_packs=True)
            summary = render_agents_summary(selections)

            self.assertIn("Selected packs: `javascript-typescript-app`, `library-package`", summary)
            self.assertIn("`library-package` (Library package):", summary)
            self.assertIn("Treat exported entrypoints, generated types, and package metadata", summary)

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

    def test_load_enhancer_install_state_reads_version_ownership_and_lifecycle(self) -> None:
        with repo_fixture("pack_install_state") as root:
            write_file(
                root,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = %s
                enhancer_version = "%s"
                selected_packs = ["python-service"]

                [lifecycle]
                state = "active"
                pack_selection = "manifest"
                managed_sections = ["AGENTS.md:stack-packs"]

                [[detected_packs]]
                name = "python-service"
                selected = true
                recommended = true
                detected = true
                reason = "found pyproject.toml"
                evidence = ["found pyproject.toml"]

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md"]
                adapt_manually = ["AGENTS.md"]
                """ % (ENHANCER_MANIFEST_SCHEMA_VERSION, ENHANCER_VERSION),
            )

            state = load_enhancer_install_state(root)

            self.assertEqual(state.schema_version, ENHANCER_MANIFEST_SCHEMA_VERSION)
            self.assertEqual(state.enhancer_version, ENHANCER_VERSION)
            self.assertEqual(state.selected_packs, ("python-service",))
            self.assertEqual(state.safe_to_regenerate, ("docs/ai/stack-guidance.md",))
            self.assertEqual(state.adapt_manually, ("AGENTS.md",))
            self.assertEqual(state.lifecycle_state, "active")
            self.assertEqual(state.pack_selection_mode, "manifest")
            self.assertEqual(state.managed_sections, ("AGENTS.md:stack-packs",))
            self.assertEqual(state.pack_evidence[0].name, "python-service")
            self.assertEqual(state.pack_evidence[0].evidence, ("found pyproject.toml",))

    def test_load_enhancer_install_state_accepts_legacy_schema_one(self) -> None:
        with repo_fixture("pack_install_state_legacy_schema") as root:
            write_file(
                root,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = 1
                enhancer_version = "2.1"
                selected_packs = ["python-service"]

                [managed_outputs]
                safe_to_regenerate = ["docs/ai/stack-guidance.md"]
                adapt_manually = ["AGENTS.md"]
                """,
            )

            state = load_enhancer_install_state(root)

            self.assertEqual(state.schema_version, 1)
            self.assertEqual(state.enhancer_version, "2.1")
            self.assertEqual(state.lifecycle_state, None)

    def test_load_enhancer_install_state_rejects_unsupported_schema(self) -> None:
        with repo_fixture("pack_install_state_bad_schema") as root:
            write_file(
                root,
                ".codex/enhancer/manifest.toml",
                """
                schema_version = 99
                enhancer_version = "99.0"
                selected_packs = []
                """,
            )

            with self.assertRaisesRegex(ValueError, "unsupported .*schema_version 99"):
                load_enhancer_install_state(root)

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

    def test_resolve_managed_pack_selection_adds_and_removes_packs(self) -> None:
        with repo_fixture("pack_manage_add_remove") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "tsconfig.json", "{}\n")

            detections = detect_stack_packs(root)
            selections = resolve_managed_pack_selection(
                detections,
                current_selected_packs=("javascript-typescript-app",),
                add_packs=("python-service",),
                remove_packs=("javascript-typescript-app",),
            )

            selected_names = tuple(item.pack.name for item in selections if item.selected)
            removed = next(item for item in selections if item.pack.name == "javascript-typescript-app")
            added = next(item for item in selections if item.pack.name == "python-service")

            self.assertEqual(selected_names, ("python-service",))
            self.assertFalse(removed.selected)
            self.assertEqual(removed.selection_source, "manage-remove")
            self.assertTrue(added.selected)
            self.assertEqual(added.selection_source, "manage-add")

    def test_resolve_managed_pack_selection_replaces_pack_set(self) -> None:
        with repo_fixture("pack_manage_set") as root:
            write_file(root, "package.json", '{"name": "demo"}\n')
            write_file(root, "tsconfig.json", "{}\n")
            write_file(root, "src/App.tsx", "export function App() { return <main />; }\n")

            detections = detect_stack_packs(root)
            selections = resolve_managed_pack_selection(
                detections,
                current_selected_packs=("javascript-typescript-app", "frontend-ui"),
                set_packs=("python-service",),
            )

            selected_names = tuple(item.pack.name for item in selections if item.selected)
            removed = next(item for item in selections if item.pack.name == "frontend-ui")
            replacement = next(item for item in selections if item.pack.name == "python-service")

            self.assertEqual(selected_names, ("python-service",))
            self.assertEqual(removed.selection_source, "manage-set-remove")
            self.assertEqual(replacement.selection_source, "manage-set")

    def test_resolve_managed_pack_selection_rejects_conflicts(self) -> None:
        with repo_fixture("pack_manage_conflict") as root:
            detections = detect_stack_packs(root)

            with self.assertRaisesRegex(ValueError, "Conflicting stack-pack management"):
                resolve_managed_pack_selection(
                    detections,
                    current_selected_packs=(),
                    add_packs=("python-service",),
                    remove_packs=("python-service",),
                )

            with self.assertRaisesRegex(ValueError, "--set-pack cannot be combined"):
                resolve_managed_pack_selection(
                    detections,
                    current_selected_packs=(),
                    add_packs=("python-service",),
                    set_packs=("python-service",),
                )

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
