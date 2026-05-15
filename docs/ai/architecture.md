# Codex Enhancer Architecture

## Why This Repo Is Minimal
This repository contains the enhancer itself, not an application stack. The workflow layer therefore has one job: make future repo changes easier for Codex and humans without pretending the repo already needs package managers, dev servers, or a command zoo.

## Current Layers
1. [README.md](../../README.md): human-facing overview and quick start.
2. [AGENTS.md](../../AGENTS.md): short entrypoint for repo purpose, workflow, commands, and definition of done.
3. [pyproject.toml](../../pyproject.toml) and [MANIFEST.in](../../MANIFEST.in): package metadata for exposing the distributable `codex-enhancer` command.
4. [docs/ai/](../ai/): durable guidance that would bloat `AGENTS.md` if kept inline, including the current architecture notes, review checklist, [v3 migration notes](./migration-v3.md), [release checklist](./release.md), the phased [design roadmap](./roadmap.md), the [repository improvement audit workflow](./repo-improvement-audit.md), the [Spec Kit bridge contract](./spec-kit-bridge.md), and the [Utility Harness contract](./utility-harness.md).
5. [codex_enhancer/package_assets.py](../../codex_enhancer/package_assets.py): package asset lookup for scaffold inputs in both source checkouts and installed wheels.
6. [.codex/skills/](../../.codex/skills/): narrow, repeatable enhancer-owned procedures that are worth reusing.
7. [.agents/skills/](../../.agents/skills/): external compatibility surface for official Spec Kit or other agent-tool skills. The enhancer may detect it, but it is not an enhancer-managed output root.
8. [codex-enhancer](../../codex-enhancer), [codex-enhancer.bat](../../codex-enhancer.bat), and [scripts/codex_enhancer_cli.py](../../scripts/codex_enhancer_cli.py): thin source-checkout command facade over the installer core, including quickstart guidance, concise previews, adaptation audits, diff previews, and JSON output.
9. [install_enhancer.bat](../../install_enhancer.bat) and [scripts/install_enhancer_gui.py](../../scripts/install_enhancer_gui.py): Windows-first installer entrypoint for manual repo selection, overwrite review, pack management, upgrade/reconcile, and guided install or managed-output refresh flow.
10. [scripts/install_enhancer.py](../../scripts/install_enhancer.py): bootstrap installer core for new and existing repos plus pack management, upgrade/reconcile, and safe generated-output refreshes.
11. [scripts/stack_packs.py](../../scripts/stack_packs.py), [scaffold/stack-packs/](../../scaffold/stack-packs/), and [scaffold/workflow-packs/](../../scaffold/workflow-packs/): file-based registry, loader, manifest-evidence collector, and renderer for optional stack packs plus explicit workflow-pack management that reuses the same metadata shape. Selected workflow packs may carry target-facing docs or skills, but unselected workflows stay out of the base scaffold.
12. [scripts/spec_kit_bridge.py](../../scripts/spec_kit_bridge.py): bridge-aware detection, bridge-mode resolution, feature/sync reporting, and summary helpers for optional official Spec Kit installs.
13. [scripts/utility_harness.py](../../scripts/utility_harness.py): mode resolution and summary helpers for the optional Codex Utility Harness.
14. [scripts/enhancer_spec.py](../../scripts/enhancer_spec.py): shared install and validation spec.
15. [scripts/enhancer_validator.py](../../scripts/enhancer_validator.py): reusable validation engine.
16. [scripts/check.py](../../scripts/check.py): deterministic integrity checks for the enhancer source repo.
17. [scaffold/target-repo/](../../scaffold/target-repo/): target-repo files that should not be copied verbatim from the source repo.
18. [tests/](../../tests/): regression protection for the validator, installer core, command facade, GUI-facing helpers, stack-pack loader, Spec Kit bridge detector, and Utility Harness resolver.
19. [.github/workflows/validate.yml](../../.github/workflows/validate.yml): CI that mirrors the local commands.

## Decision Guide

### Essential Now
- A short [README.md](../../README.md)
- A short root [AGENTS.md](../../AGENTS.md)
- One architecture note and one review note under [docs/ai/](../ai/)
- A very small skills subtree with narrow triggers
- A bootstrap installer plus an explicit scaffold
- A thin command facade that delegates to the bootstrap installer
- Minimal distributable package metadata for local CLI installation and wheel/sdist installs
- One deterministic check command plus a small test suite
- CI only because the repo now has stable, zero-dependency validation commands

### Optional Later
- Nested `AGENTS.md` files for subtrees with genuinely different commands or architecture
- Evals or regression fixtures once the repo owns behavior that can actually regress
- Stack-specific helper scripts once real install, build, lint, or test commands exist
- Additional skills only after repeated use proves they remove real prompt repetition
- `.agents/skills/` detection for external tools, without making it an enhancer-owned output root
- Optional stack packs only if they stay file-based, visible, evidence-backed, and conservative as described in [roadmap.md](./roadmap.md)
- Further repository-improvement audit workflow expansion only after selected target docs/skills, generated workflow guidance, and the managed `roadmap.md` audit section prove useful without a background audit runner
- An optional Spec Kit bridge only if it stays repo-local, keeps ownership boundaries explicit, and complements official Spec Kit instead of vendoring or replacing it
- An optional Utility Harness only if it stays explicit, scaffolded, dependency-isolated, and limited to Codex/operator helper tools

### Niche Later
- Domain-specific playbooks for migrations, incidents, releases, or API contracts
- PR templates or generated review artifacts
- MCP setup for concrete external systems that the repo actually depends on

### Not Worth Adding Now
- Slash-command ecosystems or parallel command frameworks
- Standalone packages, daemons, or updater machinery
- Published release automation before artifact smoke tests are routine
- Hidden persistent state
- Browser automation
- MCP without a real external dependency
- Wrappers around guessed build or test commands

## Extension Rules
- Prefer updating [AGENTS.md](../../AGENTS.md) or an existing doc before adding a new file.
- If a new rule applies repo-wide, put the short version in [AGENTS.md](../../AGENTS.md) and the detail in [docs/ai/](../ai/).
- If a new rule applies only to one subtree, add a nested `AGENTS.md` there.
- If a new skill needs more than one narrow procedure, split it or reconsider whether it should be a doc instead.
- Keep enhancer-owned skills under `.codex/skills/`; `.agents/skills/` is external and must not be written by enhancer install flows.
- If a script needs third-party dependencies, justify them in the same change.
- If package metadata changes, keep the console script, README install guidance, source validation requirements, packaged assets, and packaging tests aligned.
- If release expectations change, keep [release.md](./release.md), packaging tests, and README build guidance aligned.
- If the installer changes, keep the launcher, GUI, scaffold, shared spec, source validator, and tests aligned in the same patch.
- If the command facade changes, keep [README.md](../../README.md), source validation requirements, and CLI tests aligned with the installer flags it delegates to.
- If installer output modes change, keep human previews, JSON schema tests, README examples, and GUI-facing preview helpers aligned.
- If a change introduces a new top-level workflow asset, update [AGENTS.md](../../AGENTS.md) so the repo map stays accurate.
- If a lifecycle change affects installed-repo upgrade behavior, update [migration-v3.md](./migration-v3.md) with the operator-facing rule.
- If a scaffold file gains or loses an enhancer-managed section marker, update the manifest renderer and validator expectations in the same patch.
- If pack or workflow management changes, keep CLI flags, GUI mode labels, manifest rendering, managed-output behavior, selected workflow assets, README guidance, and tests aligned in the same patch.
- If pack evidence or package-manager detection changes, keep stack-pack reasons, generated manifests, command discovery, README guidance, and tests aligned in the same patch.
- If the Spec Kit bridge changes, keep [docs/ai/spec-kit-bridge.md](./spec-kit-bridge.md), target scaffold docs, bridge skills, managed-section markers, manifest state, CLI facade behavior, and validator expectations aligned in the same patch.
- If the Utility Harness changes, keep [docs/ai/utility-harness.md](./utility-harness.md), target scaffold docs, helper scripts, manifest state, GUI/CLI flags, and validator expectations aligned in the same patch.
- Keep overlapping stack packs composable but conservative. For example, `library-package` may compose with `javascript-typescript-app`, but it should not be inferred for ordinary frontend or API applications without reusable-package metadata.

## When To Add More Structure
- Add install, build, lint, and test commands to [AGENTS.md](../../AGENTS.md) only after they exist in the repo.
- Expand CI only when the check set grows beyond the current validator and unittest suite.
- Add evals once the repo owns code or artifacts with meaningful regression risk.
- Add domain docs once the repo has multiple packages, services, or UI surfaces.

## Day-To-Day Loop
Inspect -> plan -> edit -> run `python scripts/check.py` -> run `python -m unittest discover -s tests -p "test_*.py" -v` -> review -> ship.
