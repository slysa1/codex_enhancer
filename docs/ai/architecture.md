# Codex Enhancer Architecture

## Why This Repo Is Minimal
This repository contains the enhancer itself, not an application stack. The workflow layer therefore has one job: make future repo changes easier for Codex and humans without pretending the repo already needs package managers, dev servers, or a command zoo.

## Current Layers
1. [README.md](../../README.md): human-facing overview and quick start.
2. [AGENTS.md](../../AGENTS.md): short entrypoint for repo purpose, workflow, commands, and definition of done.
3. [docs/ai/](../ai/): durable guidance that would bloat `AGENTS.md` if kept inline, including the current architecture notes, review checklist, [v3 migration notes](./migration-v3.md), and the phased [design roadmap](./roadmap.md).
4. [.codex/skills/](../../.codex/skills/): narrow, repeatable procedures that are worth reusing.
5. [install_enhancer.bat](../../install_enhancer.bat) and [scripts/install_enhancer_gui.py](../../scripts/install_enhancer_gui.py): Windows-first installer entrypoint for manual repo selection, overwrite review, pack management, upgrade/reconcile, and guided install or managed-output refresh flow.
6. [scripts/install_enhancer.py](../../scripts/install_enhancer.py): bootstrap installer core for new and existing repos plus pack management, upgrade/reconcile, and safe generated-output refreshes.
7. [scripts/stack_packs.py](../../scripts/stack_packs.py) and [scaffold/stack-packs/](../../scaffold/stack-packs/): file-based registry, loader, manifest-evidence collector, and renderer for optional stack packs.
8. [scripts/enhancer_spec.py](../../scripts/enhancer_spec.py): shared install and validation spec.
9. [scripts/enhancer_validator.py](../../scripts/enhancer_validator.py): reusable validation engine.
10. [scripts/check.py](../../scripts/check.py): deterministic integrity checks for the enhancer source repo.
11. [scaffold/target-repo/](../../scaffold/target-repo/): target-repo files that should not be copied verbatim from the source repo.
12. [tests/](../../tests/): regression protection for the validator, installer core, GUI-facing helpers, and stack-pack loader.
13. [.github/workflows/validate.yml](../../.github/workflows/validate.yml): CI that mirrors the local commands.

## Decision Guide

### Essential Now
- A short [README.md](../../README.md)
- A short root [AGENTS.md](../../AGENTS.md)
- One architecture note and one review note under [docs/ai/](../ai/)
- A very small skills subtree with narrow triggers
- A bootstrap installer plus an explicit scaffold
- One deterministic check command plus a small test suite
- CI only because the repo now has stable, zero-dependency validation commands

### Optional Later
- Nested `AGENTS.md` files for subtrees with genuinely different commands or architecture
- Evals or regression fixtures once the repo owns behavior that can actually regress
- Stack-specific helper scripts once real install, build, lint, or test commands exist
- Additional skills only after repeated use proves they remove real prompt repetition
- Optional stack packs only if they stay file-based, visible, evidence-backed, and conservative as described in [roadmap.md](./roadmap.md)

### Niche Later
- Domain-specific playbooks for migrations, incidents, releases, or API contracts
- PR templates or generated review artifacts
- MCP setup for concrete external systems that the repo actually depends on

### Not Worth Adding Now
- Slash-command ecosystems
- Standalone packages, daemons, or updater machinery
- Hidden persistent state
- Browser automation
- MCP without a real external dependency
- Wrappers around guessed build or test commands

## Extension Rules
- Prefer updating [AGENTS.md](../../AGENTS.md) or an existing doc before adding a new file.
- If a new rule applies repo-wide, put the short version in [AGENTS.md](../../AGENTS.md) and the detail in [docs/ai/](../ai/).
- If a new rule applies only to one subtree, add a nested `AGENTS.md` there.
- If a new skill needs more than one narrow procedure, split it or reconsider whether it should be a doc instead.
- If a script needs third-party dependencies, justify them in the same change.
- If the installer changes, keep the launcher, GUI, scaffold, shared spec, source validator, and tests aligned in the same patch.
- If a change introduces a new top-level workflow asset, update [AGENTS.md](../../AGENTS.md) so the repo map stays accurate.
- If a lifecycle change affects installed-repo upgrade behavior, update [migration-v3.md](./migration-v3.md) with the operator-facing rule.
- If a scaffold file gains or loses an enhancer-managed section marker, update the manifest renderer and validator expectations in the same patch.
- If pack management changes, keep CLI flags, GUI mode labels, manifest rendering, managed-section behavior, README guidance, and tests aligned in the same patch.
- If pack evidence or package-manager detection changes, keep stack-pack reasons, generated manifests, command discovery, README guidance, and tests aligned in the same patch.
- Keep overlapping stack packs composable but conservative. For example, `library-package` may compose with `javascript-typescript-app`, but it should not be inferred for ordinary frontend or API applications without reusable-package metadata.

## When To Add More Structure
- Add install, build, lint, and test commands to [AGENTS.md](../../AGENTS.md) only after they exist in the repo.
- Expand CI only when the check set grows beyond the current validator and unittest suite.
- Add evals once the repo owns code or artifacts with meaningful regression risk.
- Add domain docs once the repo has multiple packages, services, or UI surfaces.

## Day-To-Day Loop
Inspect -> plan -> edit -> run `python scripts/check.py` -> run `python -m unittest discover -s tests -p "test_*.py" -v` -> review -> ship.
