# Codex Enhancer

## Purpose
This repository stores a minimal Codex-native workflow layer: instructions, skills, and checks that make future development work in this repository easier to plan, execute, validate, and review.

## Current State
- The repo still has no application stack yet; the product here is the workflow layer itself.
- The maintained execution surface is a thin command facade, a bootstrap installer, optional integration resolvers, a shared validation spec, a reusable validation engine, a source-repo validator, a unittest suite, and a GitHub Actions workflow that runs the same validation commands.
- When real product code lands, update this file and [docs/ai/architecture.md](docs/ai/architecture.md) in the same change.

## Repo Map
- [README.md](README.md): human-facing overview, quick start, and extension guidance.
- [AGENTS.md](AGENTS.md): repo-wide operating map and default workflow.
- [pyproject.toml](pyproject.toml) and [MANIFEST.in](MANIFEST.in): package metadata for exposing the distributable `codex-enhancer` command.
- [codex_enhancer/package_assets.py](codex_enhancer/package_assets.py): asset lookup helper so installed wheels can find scaffold inputs.
- [docs/ai/architecture.md](docs/ai/architecture.md): what belongs in the enhancer, what to defer, and when to add more structure.
- [docs/ai/code-review.md](docs/ai/code-review.md): review and PR-prep checklist for docs, skills, scripts, and future workflow assets.
- [docs/ai/migration-v3.md](docs/ai/migration-v3.md): upgrade and review notes for the v3 managed-section lifecycle.
- [docs/ai/roadmap.md](docs/ai/roadmap.md): phased roadmap for stack packs, installer UX, and planned enhancer evolution.
- [docs/ai/release.md](docs/ai/release.md): package build and release-readiness checklist.
- [docs/ai/repo-improvement-audit.md](docs/ai/repo-improvement-audit.md): full repository improvement audit workflow and managed roadmap artifact rules.
- [docs/ai/repo-audit-finding-schema.md](docs/ai/repo-audit-finding-schema.md): evidence-backed finding fields and severity/confidence rubrics for repo audits.
- [docs/ai/repo-audit-roadmap-rubric.md](docs/ai/repo-audit-roadmap-rubric.md): prioritization rules for turning audit findings into roadmap buckets.
- [docs/ai/spec-kit-bridge.md](docs/ai/spec-kit-bridge.md): ownership rules and phased plan for optional GitHub Spec Kit integration.
- [docs/ai/utility-harness.md](docs/ai/utility-harness.md): contract for the optional Codex Utility Harness helper tools.
- [.codex/skills/](.codex/skills/): repo-local skills for repeated procedures. Read [.codex/skills/AGENTS.md](.codex/skills/AGENTS.md) before editing or adding skills.
- [.agents/skills/](.agents/skills/): external skill-root compatibility surface for checked-in Spec Kit skills; Codex Enhancer detects it but does not manage it.
- [codex-enhancer](codex-enhancer) and [codex-enhancer.bat](codex-enhancer.bat): friendly source-checkout command shims over the installer.
- [install_enhancer.bat](install_enhancer.bat): Windows launcher that opens the GUI installer.
- [scripts/codex_enhancer_cli.py](scripts/codex_enhancer_cli.py): thin `codex-enhancer` subcommand facade over the installer core.
- [scripts/install_enhancer.py](scripts/install_enhancer.py): bootstrap installer, pack and workflow manager, and refresh/reconcile planner for target repos.
- [scripts/install_enhancer_gui.py](scripts/install_enhancer_gui.py): GUI wrapper for previewing, confirming, and applying installs, pack/workflow changes, upgrades, and refreshes.
- [scripts/stack_packs.py](scripts/stack_packs.py): loader, detection layer, and manifest renderer for optional stack packs and workflow packs.
- [scripts/spec_kit_bridge.py](scripts/spec_kit_bridge.py): detection, bridge-mode resolution, feature/sync reporting, and rendering helpers for optional official Spec Kit integration surfaces.
- [scripts/utility_harness.py](scripts/utility_harness.py): mode resolver and summary renderer for the optional Codex Utility Harness.
- [scripts/enhancer_spec.py](scripts/enhancer_spec.py): shared install and validation spec.
- [scripts/enhancer_validator.py](scripts/enhancer_validator.py): reusable validation engine.
- [scripts/check.py](scripts/check.py): deterministic validation for the enhancer source repo.
- [scaffold/target-repo/](scaffold/target-repo/): install scaffold for files that should differ in target repos.
- [scaffold/stack-packs/](scaffold/stack-packs/): file-based registry for optional stack packs and their fragments.
- [scaffold/workflow-packs/](scaffold/workflow-packs/): optional workflow-pack registry and selected target docs/skills that reuse the stack-pack loader shape.
- [tests/](tests/): unit tests for the validator and installer.
- [.github/workflows/validate.yml](.github/workflows/validate.yml): CI that mirrors the local validation commands.

## Default Workflow
1. Inspect the relevant files before editing anything.
2. Keep the plan proportional to the change. For non-trivial changes, use the `plan-change` skill in [.codex/skills/plan-change/](.codex/skills/plan-change/).
3. Prefer editing an existing file over creating a new one.
4. Keep AGENTS files short; move durable detail into [docs/ai/](docs/ai/).
5. After changes, run `python scripts/check.py` and `python -m unittest discover -s tests -p "test_*.py" -v`.
6. If the change affects install behavior, smoke-test `python scripts/install_enhancer.py --target <probe> --mode new` before finalizing it.
7. For review or PR prep, use the `review-prep` skill in [.codex/skills/review-prep/](.codex/skills/review-prep/).

## Canonical Commands
- `python scripts/check.py` - validate required files, markdown links, and skill frontmatter.
- `python -m unittest discover -s tests -p "test_*.py" -v` - run the validator test suite.
- `python scripts/check.py --verbose` - run the same checks with a per-file summary.
- `python -m pip install -e . --no-deps` - install the local `codex-enhancer` command from this checkout.
- `python -m build` - build wheel and source distribution artifacts when packaging tooling is available.
- `python scripts/codex_enhancer_cli.py init <path>` - friendly preview command for installing into a target repo.
- `python scripts/codex_enhancer_cli.py init <path> --summary --diff` - concise preview plus planned text diffs.
- `python scripts/codex_enhancer_cli.py audit <path>` - inspect an installed target for inherited generic guidance and proposal files.
- `python scripts/codex_enhancer_cli.py init <path> --with-spec-kit --utility-harness` - preview the full Codex helper bundle.
- `python scripts/codex_enhancer_cli.py spec-report <path>` - summarize existing Spec Kit feature artifacts without editing them.
- `python scripts/codex_enhancer_cli.py spec-sync <path> --feature <feature> --changed <path>` - compare changed paths against existing Spec Kit feature artifacts without editing them.
- `python scripts/codex_enhancer_cli.py bridge <path> --attach-spec-kit` - preview a Spec Kit bridge mode update for an installed target.
- `python scripts/codex_enhancer_cli.py list-packs` - friendly command for listing available stack packs.
- `python scripts/install_enhancer.py --list-workflows` - list available workflow packs from the installer core.
- `python scripts/codex_enhancer_cli.py list-workflows` - friendly command for listing available workflow packs.
- `python scripts/codex_enhancer_cli.py workflows <path> --add repository-improvement-audit` - preview selecting the audit workflow and managed `roadmap.md` artifact.
- `python scripts/install_enhancer.py --target <path> --mode new` - preview an install into a target repo.
- `python scripts/install_enhancer.py --target <path> --manage-packs --add-pack <name>` - preview a pack-selection change for an installed target.
- `python scripts/install_enhancer.py --target <path> --manage-workflows --add-workflow repository-improvement-audit` - preview a workflow-selection change for an installed target.
- `python scripts/install_enhancer.py --target <path> --mode existing --utility-harness-mode install` - preview installing optional Codex helper tools into a target repo.
- `install_enhancer.bat` - open the Windows GUI installer.

## Engineering Rules
- Build repo-local guidance, not framework machinery.
- Prefer `AGENTS.md`, concise docs, narrow skills, and small scripts over packages, daemons, or hidden state.
- Add nested `AGENTS.md` files only when a subtree has materially different rules.
- Add repo-local skills only for repeated, narrow procedures with clear triggers and explicit "do not use" boundaries.
- Keep enhancer-owned skills under `.codex/skills/`; do not mirror or migrate them into `.agents/skills/`.
- Add scripts only when they provide deterministic validation or remove repeated manual steps.
- Keep the shared spec, source validator, installer, scaffold, and tests aligned in the same patch.
- Keep local commands and CI in sync. If one changes, update the other in the same patch.
- Treat official Spec Kit files as separately owned. The enhancer may detect, document, and bridge `.specify/`, `specs/`, `.github/prompts/`, or `.github/agents/`, but it should not rewrite them.
- Treat Utility Harness dependencies as Codex/operator helper dependencies only. Do not mix `requirements-codex.txt` into production dependency files.
- Add evals or regression fixtures only after the repo has stable code paths or recurring bug classes.
- Add MCP only when the repo needs a real external system that cannot be handled by normal local tools.
- Do not add wrappers around nonexistent build, lint, or test commands.

## Review Expectations
- Explain why each new file exists and why a simpler alternative was not enough.
- Call out what was intentionally omitted.
- Record the exact validation performed.
- Flag instructions likely to go stale as soon as the repo shape changes.

## Definition Of Done
- The requested change is implemented with the smallest useful file set.
- `python scripts/check.py` passes.
- `python -m unittest discover -s tests -p "test_*.py" -v` passes.
- Paths, commands, and links in docs resolve correctly.
- Any new skill has a narrow trigger, bounded scope, and explicit non-goals.
- If installer or scaffold behavior changed, the end-to-end installer tests still pass.
- If validation commands changed, [.github/workflows/validate.yml](.github/workflows/validate.yml) changed with them.
- The final summary states risks, omitted items, and obvious follow-up work.

## Subagents
Use subagents only when parallel exploration or an independent review materially speeds up a large change.
Do not use subagents for small doc edits, single-skill changes, or work blocked on one local file.

## More Detail
- Architecture and scope rules: [docs/ai/architecture.md](docs/ai/architecture.md)
- V3 migration notes: [docs/ai/migration-v3.md](docs/ai/migration-v3.md)
- Review checklist: [docs/ai/code-review.md](docs/ai/code-review.md)
- Design roadmap: [docs/ai/roadmap.md](docs/ai/roadmap.md)
- Release checklist: [docs/ai/release.md](docs/ai/release.md)
- Repository improvement audit workflow: [docs/ai/repo-improvement-audit.md](docs/ai/repo-improvement-audit.md)
- Repo audit finding schema: [docs/ai/repo-audit-finding-schema.md](docs/ai/repo-audit-finding-schema.md)
- Repo audit roadmap rubric: [docs/ai/repo-audit-roadmap-rubric.md](docs/ai/repo-audit-roadmap-rubric.md)
- Spec Kit bridge contract: [docs/ai/spec-kit-bridge.md](docs/ai/spec-kit-bridge.md)
- Utility Harness contract: [docs/ai/utility-harness.md](docs/ai/utility-harness.md)

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
