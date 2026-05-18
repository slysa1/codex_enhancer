from __future__ import annotations

import shutil
import textwrap
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from scripts import check
from scripts.enhancer_spec import AUDIT_SPECIALIST_SKILL_NAMES, CHECK_COMMAND, TEST_COMMAND


TEMP_ROOT = Path(__file__).resolve().parent / "_tmp"


def write_file(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def build_valid_repo(root: Path, missing: set[str] | None = None) -> None:
    missing = missing or set()
    files = {
        ".gitignore": "__pycache__/\n*.py[cod]\ntests/_tmp/\n",
        "README.md": f"""
        # Codex Enhancer

        See [AGENTS.md](AGENTS.md).

        Run `{CHECK_COMMAND}` and `{TEST_COMMAND}`.
        Use `pip install -e .` for local CLI packaging.
        Build distributable artifacts with `python -m build`.
        Run `python scripts/codex_enhancer_cli.py list-packs` or `codex-enhancer.bat`.
        Run `python scripts/install_enhancer.py --list-workflows`.
        Use `--manage-workflows` to manage selected workflows.
        Manifests record selected_workflows.
        Audit workflow suggestions can update root `roadmap.md`.
        Preview bundled installs with `--with-spec-kit`.
        Use `--summary`, `--diff`, and `--json` for alternate previews.
        Run `python scripts/codex_enhancer_cli.py audit ../repo`.
        Run `python scripts/codex_enhancer_cli.py spec-report ../repo`,
        `python scripts/codex_enhancer_cli.py spec-sync ../repo --changed src/app.py`,
        and `python scripts/codex_enhancer_cli.py bridge ../repo --attach-spec-kit`.
        Launch `install_enhancer.bat` or inspect `scripts/install_enhancer_qt_gui.py`.
        The browser fallback lives in `scripts/install_enhancer_web_gui.py`.
        PowerShell-backed GUI launch lives in `scripts/launch_enhancer_gui.ps1`.
        The legacy Tkinter wrapper remains in `scripts/install_enhancer_gui.py`.
        Workflow packs live in `scaffold/workflow-packs/` and reuse `scripts/stack_packs.py`.
        `.agents/skills/` is an external compatibility surface, not enhancer-managed output.
        Read [docs/ai/migration-v3.md](docs/ai/migration-v3.md) before upgrading existing installs.
        See [docs/ai/roadmap.md](docs/ai/roadmap.md) for the completed product maturity roadmap.
        See [docs/ai/release.md](docs/ai/release.md) before building packages.
        Use `full-repo-improvement-audit` for read-only whole-repo improvement audits.
        Specialist audit helpers include `repo-map`, `repo-quality-audit`, `repo-test-audit`,
        `repo-security-audit`, `repo-performance-audit`, and `repo-dx-audit`.
        See [docs/ai/repo-improvement-audit.md](docs/ai/repo-improvement-audit.md).
        See [docs/ai/repo-audit-finding-schema.md](docs/ai/repo-audit-finding-schema.md).
        See [docs/ai/repo-audit-roadmap-rubric.md](docs/ai/repo-audit-roadmap-rubric.md).
        See [docs/ai/utility-harness.md](docs/ai/utility-harness.md) for the optional harness.
        Use requirements-codex-readers.txt for rich helper readers.
        Preview with `--utility-harness-mode install`.
        """,
        "AGENTS.md": f"""
        # Codex Enhancer

        Run `{CHECK_COMMAND}` and `{TEST_COMMAND}`.
        Local package metadata lives in `pyproject.toml` and package assets live in `codex_enhancer/package_assets.py`.
        Use `scripts/codex_enhancer_cli.py` and `codex-enhancer.bat` for the friendly command facade.
        Use `--list-workflows` and `--manage-workflows` for workflow-pack previews.
        Use `--with-spec-kit` only when the user explicitly wants official Spec Kit bootstrapped.
        Use `audit` for installed target adaptation checks.
        Use `spec-sync` for read-only Spec Kit changed-path sync cues.
        Use `install_enhancer.bat` for the Windows GUI installer.
        The Qt GUI lives in `scripts/install_enhancer_qt_gui.py`.
        The browser GUI lives in `scripts/install_enhancer_web_gui.py`.
        PowerShell Python discovery lives in `scripts/launch_enhancer_gui.ps1`.
        See [docs/ai/roadmap.md](docs/ai/roadmap.md) for the enhancer roadmap.
        See [docs/ai/release.md](docs/ai/release.md) for package release checks.
        See [docs/ai/repo-improvement-audit.md](docs/ai/repo-improvement-audit.md).
        See [docs/ai/repo-audit-finding-schema.md](docs/ai/repo-audit-finding-schema.md).
        See [docs/ai/repo-audit-roadmap-rubric.md](docs/ai/repo-audit-roadmap-rubric.md).
        See [docs/ai/spec-kit-bridge.md](docs/ai/spec-kit-bridge.md) for the optional Spec Kit bridge.
        See [docs/ai/utility-harness.md](docs/ai/utility-harness.md) for the optional Utility Harness.
        The resolver lives in `scripts/utility_harness.py`.
        Workflow pack loading reuses `scripts/stack_packs.py` with `scaffold/workflow-packs/`.

        See [docs/ai/architecture.md](docs/ai/architecture.md),
        [docs/ai/code-review.md](docs/ai/code-review.md),
        [docs/ai/migration-v3.md](docs/ai/migration-v3.md),
        [.codex/skills/](.codex/skills/), [.agents/skills/](.agents/skills/), and [tests/](tests/).
        """,
        "install_enhancer.bat": """
        @echo off
        set "PS_LAUNCHER=%SCRIPT_DIR%scripts\\launch_enhancer_gui.ps1"
        install_enhancer_qt_gui.py
        where pwsh
        pwsh.exe
        powershell.exe
        NoProfile
        WindowStyle Hidden
        """,
        "MANIFEST.in": """
        recursive-include codex_enhancer/assets/root *
        """,
        "pyproject.toml": """
        [build-system]
        requires = ["setuptools>=70"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "codex-enhancer"
        dynamic = ["version"]
        license = "GPL-3.0-or-later"
        license-files = ["LICENSE"]

        [project.optional-dependencies]
        gui = ["PyQt6"]
        pyside = ["PySide6"]

        [project.scripts]
        codex-enhancer = "scripts.codex_enhancer_cli:main"

        [tool.setuptools]
        include-package-data = true

        [tool.setuptools.packages.find]
        include = ["scripts*", "codex_enhancer*"]

        [tool.setuptools.dynamic]
        version = { attr = "scripts.enhancer_spec.ENHANCER_VERSION" }
        """,
        "codex_enhancer/__init__.py": """
        # package marker
        """,
        "codex_enhancer/package_assets.py": """
        # package asset locator
        """,
        "codex-enhancer": """
        #!/usr/bin/env python3
        """,
        "codex-enhancer.bat": """
        @echo off
        where py
        where python3
        where python
        """,
        "docs/ai/architecture.md": """
        # Architecture

        Repo-local workflow guidance only.
        Workflow pack loading reuses scripts/stack_packs.py with scaffold/workflow-packs/.
        workflow-pack management stays explicit.
        .agents/skills/ is not an enhancer-managed output root.
        scripts/install_enhancer_qt_gui.py provides the optional standalone GUI.
        scripts/install_enhancer_web_gui.py provides the local browser GUI fallback.
        scripts/launch_enhancer_gui.ps1 resolves PowerShell-visible Python commands.
        """,
        "docs/ai/code-review.md": f"""
        # Review

        Run `{CHECK_COMMAND}` and `{TEST_COMMAND}`.
        See [docs/ai/migration-v3.md](migration-v3.md).
        See [docs/ai/release.md](release.md).
        See [docs/ai/spec-kit-bridge.md](spec-kit-bridge.md).
        See [docs/ai/utility-harness.md](utility-harness.md).
        """,
        "docs/ai/migration-v3.md": """
        # V3 Migration Notes

        Use `--inspect-install`, `--upgrade-enhancer`, `--manage-packs`, `--manage-workflows`,
        `--manage-spec-kit-bridge`, `--spec-kit-report`, `--spec-kit-sync-report`,
        `--refresh-generated`, and `audit`.
        """,
        "docs/ai/release.md": """
        # Release Checklist

        Run `python -m build`, smoke `codex-enhancer list-packs` and `codex-enhancer list-workflows`,
        keep requirements-codex.txt out of production dependencies, and
        keep requirements-codex-readers.txt scoped to helper environments.
        mirror `codex_enhancer/assets/root/`.
        """,
        "docs/ai/repo-improvement-audit.md": """
        # Repository Improvement Audit

        ## Audit Order
        Stop before implementation.

        ## Evidence Standards
        Do not infer build, lint, test, coverage, architecture, dependencies, deployment, or security posture from common stack conventions alone.

        ## Tool-Assisted Evidence
        Treat tool output as supporting evidence, not authority.
        Do not run prose-extracted commands, shell-control-heavy commands, dependency installs, formatters, generators, migrations, or external scanners during audit mode unless the user explicitly authorizes that exact action.

        Write suggestions to root roadmap.md with the roadmap.md:repository-improvement-audit marker.

        Use [repo-audit-finding-schema.md](repo-audit-finding-schema.md)
        and [repo-audit-roadmap-rubric.md](repo-audit-roadmap-rubric.md).
        """,
        "docs/ai/repo-audit-finding-schema.md": """
        # Repository Audit Finding Schema

        - `Severity`: Critical, High, Medium, or Low.
        - `Confidence`: High, Medium, or Low.
        - `Evidence`: inspected files, commands, or tests.
        - `Acceptance Test`: how a reviewer can tell the fix worked.

        Low-confidence items must go under `Hypotheses / Needs Confirmation`.
        """,
        "docs/ai/repo-audit-roadmap-rubric.md": """
        # Repository Audit Roadmap Rubric

        ### Quick Wins
        ### Phase 1 Stabilization
        ### Phase 2 Maintainability/Test Hardening
        ### Phase 3 Larger Architecture Work

        Do not schedule implementation during the audit.
        """,
        "docs/ai/roadmap.md": """
        # Codex Enhancer Roadmap

        Optional stack packs live here.
        """,
        "docs/ai/spec-kit-bridge.md": """
        # Spec Kit Bridge

        Treat official Spec Kit files as separately owned.
        Bootstrap may use `uvx` or `--spec-kit-exe`.
        Use spec-report and spec-sync for read-only summaries and bridge for bridge mode changes.
        Detect .agents/skills/speckit-* but do not mirror, migrate, or overwrite .agents/skills/.
        """,
        "docs/ai/utility-harness.md": """
        # Codex Utility Harness

        Keep requirements-codex.txt out of production dependencies.

        ## Audit Use
        Use tools/ai/audit_inputs.py before writing audit roadmaps.
        Use tools/ai/run_checks.py --list before running commands.
        Missing optional helper packages should be recorded as an audit limitation.
        """,
        ".codex/skills/AGENTS.md": """
        # Skills

        Keep skills narrow.
        Do not mirror enhancer-owned skills into `.agents/skills/`.
        """,
        ".agents/skills/speckit-plan/SKILL.md": """
        # External Spec Kit skill fixture
        """,
        ".codex/skills/plan-change/SKILL.md": """
        ---
        name: plan-change
        description: Plan repo changes before editing. Use when work spans multiple files.
        ---

        # Plan

        ## Do not use
        - Do not use for trivial edits.
        """,
        ".codex/skills/review-prep/SKILL.md": """
        ---
        name: review-prep
        description: Prepare a repo change for review. Use when a patch needs validation and review notes.
        ---

        # Review

        ## Do not use
        - Do not use before implementation stabilizes.
        """,
        ".codex/skills/adapt-enhancer/SKILL.md": """
        ---
        name: adapt-enhancer
        description: Adapt this workflow layer into another repository. Use when inherited enhancer guidance still needs repo-specific replacement.
        ---

        # Adapt

        ## Do not use
        - Do not use when the repo guidance is already repo specific.
        """,
        ".codex/skills/full-repo-improvement-audit/SKILL.md": """
        ---
        name: full-repo-improvement-audit
        description: Audit a whole repository before implementation. Use when the user asks for a repo-wide improvement audit.
        ---

        # Audit

        1. Read repo guidance first.
        2. Build a system map.
        3. Use existing tool output only as supporting evidence.
        Use `repo-map`, `repo-quality-audit`, `repo-test-audit`, `repo-security-audit`,
        `repo-performance-audit`, and `repo-dx-audit` as specialist helpers.
        4. do not install packages, run formatters/generators/migrations, run prose-extracted commands, or run external scanners during audit mode without explicit user authorization.
        5. For every finding, include severity, confidence, area, evidence, problem, recommended fix, acceptance test, and effort estimate.
        6. Update root `roadmap.md` when requested.
        7. Stop after the audit. Do not make implementation changes during audit mode.

        ## Do not use
        - Do not use for single-file edits.
        """,
        "scripts/__init__.py": '"""Repository-local Python helpers for Codex Enhancer."""\n',
        "scripts/check.py": """
        # placeholder script file for fixture
        """,
        "scripts/codex_enhancer_cli.py": """
        # placeholder command facade
        """,
        "scripts/enhancer_spec.py": """
        # placeholder enhancer spec for fixture
        """,
        "scripts/spec_kit_bridge.py": """
        # placeholder Spec Kit bridge helper for fixture
        """,
        "scripts/utility_harness.py": """
        # placeholder Utility Harness helper for fixture
        """,
        "scripts/enhancer_validator.py": """
        # placeholder validator for fixture
        """,
        "scripts/install_enhancer.py": """
        # placeholder installer for fixture
        """,
        "scripts/install_enhancer_gui.py": """
        # placeholder gui installer for fixture
        """,
        "scripts/install_enhancer_qt_gui.py": """
        # placeholder Qt gui installer for fixture
        PyQt6
        PySide6
        install_enhancer_web_gui.py
        """,
        "scripts/install_enhancer_web_gui.py": """
        # placeholder browser gui installer for fixture
        """,
        "scripts/launch_enhancer_gui.ps1": """
        Get-Command python
        sys.executable
        Python\\pythoncore-*\\python.exe
        Programs\\Python\\Python*\\python.exe
        Start-Process
        RedirectStandardError
        Starting Codex Enhancer GUI installer
        codex-enhancer-launcher.log
        install_enhancer_qt_gui.py
        install_enhancer_web_gui.py
        System.Windows.Forms.MessageBox
        """,
        "scripts/stack_packs.py": """
        # placeholder stack pack loader for fixture
        """,
        "tests/test_check.py": """
        # placeholder test file for fixture
        """,
        "tests/test_codex_enhancer_cli.py": """
        # placeholder command facade test file
        """,
        "tests/test_install_enhancer.py": """
        # placeholder installer test file for fixture
        """,
        "tests/test_packaging.py": """
        # placeholder packaging test file for fixture
        """,
        "tests/test_spec_kit_bridge.py": """
        # placeholder Spec Kit bridge test file for fixture
        """,
        "tests/test_utility_harness.py": """
        # placeholder Utility Harness test file for fixture
        """,
        "tests/test_stack_packs.py": """
        # placeholder stack pack test file for fixture
        """,
        ".github/workflows/validate.yml": f"""
        name: validate
        on:
          push:
          pull_request:
        jobs:
          validate:
            runs-on: ubuntu-latest
            steps:
              - run: {CHECK_COMMAND}
              - run: {TEST_COMMAND}
        """,
        "scaffold/target-repo/AGENTS.md": """
        # {{REPO_NAME}}
        """,
        "scaffold/target-repo/docs/ai/architecture.md": """
        # Architecture template
        """,
        "scaffold/target-repo/docs/ai/code-review.md": """
        # Review template
        """,
        "scaffold/target-repo/docs/ai/spec-kit-bridge.md": """
        # Spec Kit Bridge template

        If `.agents/skills/` exists, do not mirror, migrate, or overwrite files there.
        """,
        "scaffold/target-repo/docs/ai/utility-harness.md": """
        # Utility Harness template

        ## Audit Use
        Use `tools/ai/audit_inputs.py` before writing audit roadmaps.
        Use `tools/ai/run_checks.py --list` before running helpers during audits.
        Missing optional helper packages should lower confidence or become a limitation.
        """,
        "scaffold/target-repo/.codex/skills/adapt-enhancer/SKILL.md": """
        ---
        name: adapt-enhancer
        description: Adapt this workflow layer into a real repository. Use when inherited enhancer guidance still needs repo-specific replacement.
        ---

        # Adapt

        ## Do not use
        - Do not use once adaptation is complete.
        """,
        "scaffold/target-repo/.codex/skills/spec-implement-bridge/SKILL.md": """
        ---
        name: spec-implement-bridge
        description: Implement code from existing Spec Kit feature artifacts. Use when a repo already has spec and plan artifacts for the active feature.
        ---

        ## Do not use
        - Do not use before official Spec Kit artifacts exist.
        """,
        "scaffold/target-repo/.codex/skills/spec-sync-check/SKILL.md": """
        ---
        name: spec-sync-check
        description: Compare changed code against existing Spec Kit artifacts. Use when code changed and you need to check for drift against spec or task artifacts.
        ---

        ## Do not use
        - Do not use when no Spec Kit feature artifacts exist.
        """,
        "scaffold/target-repo/.codex/skills/spec-review-bridge/SKILL.md": """
        ---
        name: spec-review-bridge
        description: Prepare review notes for Spec Kit-driven work. Use when a branch was implemented from Spec Kit artifacts and the handoff should summarize remaining drift.
        ---

        ## Do not use
        - Do not use when the change was not driven by Spec Kit artifacts.
        """,
        "scaffold/target-repo/requirements-codex.txt": """
        -r requirements-codex-minimal.txt
        -r requirements-codex-readers.txt
        """,
        "scaffold/target-repo/requirements-codex-minimal.txt": """
        pathspec
        charset-normalizer
        """,
        "scaffold/target-repo/requirements-codex-readers.txt": """
        pypdf
        python-docx
        """,
        "scaffold/target-repo/requirements-codex-analysis.txt": """
        libcst
        """,
        "scaffold/target-repo/requirements-codex-cli.txt": """
        rich
        """,
        "scaffold/target-repo/tools/ai/audit_inputs.py": """
        # utility harness audit inputs tool
        """,
        "scaffold/target-repo/tools/ai/inspect_repo.py": """
        # utility harness inspect repo tool
        """,
        "scaffold/target-repo/tools/ai/read_any.py": """
        # utility harness read any tool
        """,
        "scaffold/target-repo/tools/ai/summarize_tree.py": """
        # utility harness summarize tree tool
        """,
        "scaffold/target-repo/tools/ai/run_checks.py": """
        # utility harness run checks tool
        """,
        "scaffold/target-repo/scripts/check.py": """
        # template check wrapper
        """,
        "scaffold/target-repo/tests/test_check.py": """
        # template test file
        """,
        "scaffold/target-repo/.github/workflows/validate.yml": """
        name: validate
        """,
        "scaffold/stack-packs/monorepo-workspace/pack.toml": """
        schema_version = 1
        name = "monorepo-workspace"
        label = "Monorepo workspace"
        description = "Monorepo rules."
        version = "0.1.0"

        [discovery]
        any_files = ["pnpm-workspace.yaml"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 10

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/monorepo-workspace/fragments/agents-summary.md": """
        Monorepo summary.
        """,
        "scaffold/stack-packs/monorepo-workspace/fragments/stack-guidance.md": """
        Monorepo guidance.
        """,
        "scaffold/stack-packs/monorepo-workspace/fragments/review-notes.md": """
        Monorepo review notes.
        """,
        "scaffold/stack-packs/javascript-typescript-app/pack.toml": """
        schema_version = 1
        name = "javascript-typescript-app"
        label = "JavaScript / TypeScript app"
        description = "JavaScript or TypeScript app rules."
        version = "0.1.0"

        [discovery]
        all_files = ["package.json"]
        any_globs = ["tsconfig*.json"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 20

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/javascript-typescript-app/fragments/agents-summary.md": """
        JS summary.
        """,
        "scaffold/stack-packs/javascript-typescript-app/fragments/stack-guidance.md": """
        JS guidance.
        """,
        "scaffold/stack-packs/javascript-typescript-app/fragments/review-notes.md": """
        JS review notes.
        """,
        "scaffold/stack-packs/frontend-ui/pack.toml": """
        schema_version = 1
        name = "frontend-ui"
        label = "Frontend UI"
        description = "Frontend UI rules."
        version = "0.1.0"

        [discovery]
        any_globs = ["src/**/*.tsx"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 25

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/frontend-ui/fragments/agents-summary.md": """
        Frontend summary.
        """,
        "scaffold/stack-packs/frontend-ui/fragments/stack-guidance.md": """
        Frontend guidance.
        """,
        "scaffold/stack-packs/frontend-ui/fragments/review-notes.md": """
        Frontend review notes.
        """,
        "scaffold/stack-packs/python-service/pack.toml": """
        schema_version = 1
        name = "python-service"
        label = "Python service"
        description = "Python service rules."
        version = "0.1.0"

        [discovery]
        any_files = ["pyproject.toml"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 30

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/python-service/fragments/agents-summary.md": """
        Python summary.
        """,
        "scaffold/stack-packs/python-service/fragments/stack-guidance.md": """
        Python guidance.
        """,
        "scaffold/stack-packs/python-service/fragments/review-notes.md": """
        Python review notes.
        """,
        "scaffold/stack-packs/node-api-service/pack.toml": """
        schema_version = 1
        name = "node-api-service"
        label = "Node API service"
        description = "Node API service rules."
        version = "0.1.0"

        [discovery]
        all_files = ["package.json"]
        any_globs = ["src/server.*"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 35

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/node-api-service/fragments/agents-summary.md": """
        Node API summary.
        """,
        "scaffold/stack-packs/node-api-service/fragments/stack-guidance.md": """
        Node API guidance.
        """,
        "scaffold/stack-packs/node-api-service/fragments/review-notes.md": """
        Node API review notes.
        """,
        "scaffold/stack-packs/library-package/pack.toml": """
        schema_version = 1
        name = "library-package"
        label = "Library package"
        description = "Library package rules."
        version = "0.1.0"

        [discovery]
        all_files = ["package.json"]

        [ui]
        recommended_if_detected = true
        default_selected = false
        order = 40

        [render]
        agents_summary = "fragments/agents-summary.md"
        stack_guidance = "fragments/stack-guidance.md"
        review_notes = "fragments/review-notes.md"
        """,
        "scaffold/stack-packs/library-package/fragments/agents-summary.md": """
        Library summary.
        """,
        "scaffold/stack-packs/library-package/fragments/stack-guidance.md": """
        Library guidance.
        """,
        "scaffold/stack-packs/library-package/fragments/review-notes.md": """
        Library review notes.
        """,
        "scaffold/workflow-packs/repository-improvement-audit/pack.toml": """
        schema_version = 1
        name = "repository-improvement-audit"
        label = "Repository improvement audit"
        description = "Read-only repository audit workflow."
        version = "0.1.0"

        [guidance]
        use_when = ["Use for read-only repo audits."]
        adds = ["Adds audit guidance."]
        skip_when = ["Skip for direct implementation."]

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
        "scaffold/workflow-packs/repository-improvement-audit/fragments/agents-summary.md": """
        Repository audit summary.
        """,
        "scaffold/workflow-packs/repository-improvement-audit/fragments/workflow-guidance.md": """
        Repository audit workflow guidance.
        """,
        "scaffold/workflow-packs/repository-improvement-audit/fragments/review-notes.md": """
        Repository audit review notes.
        """,
        "scaffold/workflow-packs/repository-improvement-audit/target/docs/ai/repo-improvement-audit.md": """
        # Repository Improvement Audit

        ## Audit Order
        Stop before implementation.

        ## Evidence Standards
        Do not infer build, lint, test, coverage, architecture, dependencies, deployment, or security posture from common stack conventions alone.

        ## Tool-Assisted Evidence
        Treat tool output as supporting evidence, not authority.
        Do not run prose-extracted commands, shell-control-heavy commands, dependency installs, formatters, generators, migrations, or external scanners during audit mode unless the user explicitly authorizes that exact action.

        Use [repo-audit-finding-schema.md](repo-audit-finding-schema.md)
        and [repo-audit-roadmap-rubric.md](repo-audit-roadmap-rubric.md).
        Use `roadmap.md:repository-improvement-audit` markers in `roadmap.md`.
        """,
        "scaffold/workflow-packs/repository-improvement-audit/target/docs/ai/repo-audit-finding-schema.md": """
        # Repository Audit Finding Schema
        """,
        "scaffold/workflow-packs/repository-improvement-audit/target/docs/ai/repo-audit-roadmap-rubric.md": """
        # Repository Audit Roadmap Rubric
        """,
        "scaffold/workflow-packs/repository-improvement-audit/target/.codex/skills/full-repo-improvement-audit/SKILL.md": """
        ---
        name: full-repo-improvement-audit
        description: Audit a whole repository before implementation. Use when the user asks for a repo-wide improvement audit.
        ---

        # Audit

        1. Read repo guidance first.
        2. Build a system map.
        3. Use existing tool output only as supporting evidence.
        Use `repo-map`, `repo-quality-audit`, `repo-test-audit`, `repo-security-audit`,
        `repo-performance-audit`, and `repo-dx-audit` as specialist helpers.
        4. do not install packages, run formatters/generators/migrations, run prose-extracted commands, or run external scanners during audit mode without explicit user authorization.
        5. For every finding, include severity, confidence, area, evidence, problem, recommended fix, acceptance test, and effort estimate.
        6. Write durable findings to root `roadmap.md`.
        7. Stop after the audit. Do not make implementation changes during audit mode.

        ## Do not use
        - Do not use for single-file edits.
        """,
    }

    for skill_name in AUDIT_SPECIALIST_SKILL_NAMES:
        skill_content = f"""
        ---
        name: {skill_name}
        description: Audit a bounded repository area. Use when full-repo-improvement-audit needs {skill_name} evidence.
        ---

        # Specialist Audit

        Run as a no-implementation specialist sub-pass inside `full-repo-improvement-audit`.
        Report only evidence-backed findings and return control to `full-repo-improvement-audit`.

        Output contract:
        - Evidence-backed observations.

        ## Do not use
        - Do not use for implementation.
        """
        files[f".codex/skills/{skill_name}/SKILL.md"] = skill_content
        files[
            "scaffold/workflow-packs/repository-improvement-audit/target/.codex/skills/"
            f"{skill_name}/SKILL.md"
        ] = skill_content

    for relative_path, content in files.items():
        if relative_path in missing:
            continue
        write_file(root, relative_path, content)


@contextmanager
def repo_fixture() -> Path:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TEMP_ROOT / f"fixture_{uuid.uuid4().hex}"
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class ValidateTests(unittest.TestCase):
    def test_validate_passes_for_valid_repo(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)

            errors = check.validate(root)

            self.assertEqual(errors, [])

    def test_missing_required_file_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root, missing={"README.md"})

            errors = check.validate(root)

            self.assertTrue(any("Missing required file: README.md" in error for error in errors))

    def test_broken_markdown_link_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "docs/ai/architecture.md",
                """
                # Architecture

                See [missing](missing.md).
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any("Broken link in docs/ai/architecture.md -> missing.md" in error for error in errors)
            )

    def test_broken_markdown_link_includes_hint(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "docs/ai/architecture.md",
                """
                # Architecture

                See [missing](missing.md).
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "Broken link in docs/ai/architecture.md -> missing.md" in error
                    and "Hint:" in error
                    for error in errors
                )
            )

    def test_required_skill_is_enforced(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root, missing={".codex/skills/adapt-enhancer/SKILL.md"})

            errors = check.validate(root)

            self.assertTrue(
                any("Missing required skill: .codex/skills/adapt-enhancer/SKILL.md" in error for error in errors)
            )

    def test_audit_skill_is_enforced(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root, missing={".codex/skills/full-repo-improvement-audit/SKILL.md"})

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "Missing required skill: .codex/skills/full-repo-improvement-audit/SKILL.md" in error
                    for error in errors
                )
            )

    def test_audit_specialist_skills_are_enforced(self) -> None:
        with repo_fixture() as root:
            missing_skill = ".codex/skills/repo-test-audit/SKILL.md"
            build_valid_repo(root, missing={missing_skill})

            errors = check.validate(root)

            self.assertTrue(
                any(f"Missing required file: {missing_skill}" in error for error in errors)
            )

    def test_audit_workflow_doc_drift_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "docs/ai/repo-improvement-audit.md",
                """
                # Repository Improvement Audit

                Use [repo-audit-finding-schema.md](repo-audit-finding-schema.md)
                and [repo-audit-roadmap-rubric.md](repo-audit-roadmap-rubric.md).
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "docs/ai/repo-improvement-audit.md is missing required text" in error
                    and "## Evidence Standards" in error
                    for error in errors
                )
            )

    def test_target_audit_workflow_doc_drift_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "scaffold/workflow-packs/repository-improvement-audit/target/docs/ai/repo-improvement-audit.md",
                """
                # Repository Improvement Audit

                Use [repo-audit-finding-schema.md](repo-audit-finding-schema.md)
                and [repo-audit-roadmap-rubric.md](repo-audit-roadmap-rubric.md).
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "scaffold/workflow-packs/repository-improvement-audit/target/docs/ai/repo-improvement-audit.md is missing required text"
                    in error
                    and "## Tool-Assisted Evidence" in error
                    for error in errors
                )
            )

    def test_target_audit_workflow_skill_drift_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "scaffold/workflow-packs/repository-improvement-audit/target/.codex/skills/full-repo-improvement-audit/SKILL.md",
                """
                ---
                name: full-repo-improvement-audit
                description: Audit a whole repository before implementation. Use when the user asks for a repo-wide improvement audit.
                ---

                # Audit

                ## Do not use
                - Do not use for single-file edits.
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "scaffold/workflow-packs/repository-improvement-audit/target/.codex/skills/full-repo-improvement-audit/SKILL.md is missing required text"
                    in error
                    and "Use existing tool output only as supporting evidence" in error
                    for error in errors
                )
            )

    def test_target_audit_specialist_skill_drift_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "scaffold/workflow-packs/repository-improvement-audit/target/.codex/skills/repo-test-audit/SKILL.md",
                """
                ---
                name: repo-test-audit
                description: Audit tests and reliability during a full repo audit. Use when the audit needs test evidence.
                ---

                # Repo Test Audit

                ## Do not use
                - Do not use for implementation.
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "scaffold/workflow-packs/repository-improvement-audit/target/.codex/skills/repo-test-audit/SKILL.md is missing required text"
                    in error
                    and "Output contract:" in error
                    for error in errors
                )
            )

    def test_target_utility_harness_audit_guidance_drift_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "scaffold/target-repo/docs/ai/utility-harness.md",
                """
                # Utility Harness template
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "scaffold/target-repo/docs/ai/utility-harness.md is missing required text"
                    in error
                    and "## Audit Use" in error
                    for error in errors
                )
            )

    def test_skill_root_policy_drift_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                "docs/ai/spec-kit-bridge.md",
                """
                # Spec Kit Bridge

                Treat official Spec Kit files as separately owned.
                Bootstrap may use `uvx` or `--spec-kit-exe`.
                Use spec-report and spec-sync for read-only summaries and bridge for bridge mode changes.
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    "docs/ai/spec-kit-bridge.md is missing required text" in error
                    and ".agents/skills/speckit-*" in error
                    for error in errors
                )
            )

    def test_skill_missing_do_not_use_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".codex/skills/review-prep/SKILL.md",
                """
                ---
                name: review-prep
                description: Prepare a repo change for review. Use when a patch needs validation and review notes.
                ---

                # Review
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    ".codex/skills/review-prep/SKILL.md must include a '## Do not use' section"
                    in error
                    for error in errors
                )
            )

    def test_skill_missing_do_not_use_includes_hint(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".codex/skills/review-prep/SKILL.md",
                """
                ---
                name: review-prep
                description: Prepare a repo change for review. Use when a patch needs validation and review notes.
                ---

                # Review
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    ".codex/skills/review-prep/SKILL.md must include a '## Do not use' section"
                    in error
                    and "Hint:" in error
                    for error in errors
                )
            )

    def test_workflow_command_drift_is_reported(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".github/workflows/validate.yml",
                """
                name: validate
                jobs:
                  validate:
                    runs-on: ubuntu-latest
                    steps:
                      - run: python scripts/check.py
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    ".github/workflows/validate.yml is missing required text" in error
                    and TEST_COMMAND in error
                    for error in errors
                )
            )

    def test_workflow_command_drift_includes_hint(self) -> None:
        with repo_fixture() as root:
            build_valid_repo(root)
            write_file(
                root,
                ".github/workflows/validate.yml",
                """
                name: validate
                jobs:
                  validate:
                    runs-on: ubuntu-latest
                    steps:
                      - run: python scripts/check.py
                """,
            )

            errors = check.validate(root)

            self.assertTrue(
                any(
                    ".github/workflows/validate.yml is missing required text" in error
                    and "Hint:" in error
                    for error in errors
                )
            )


if __name__ == "__main__":
    unittest.main()
