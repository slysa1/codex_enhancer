# Codex Enhancer

## Purpose
This repository stores a minimal Codex-native workflow layer: instructions, skills, and checks that make future development work in this repository easier to plan, execute, validate, and review.

## Current State
- The repo still has no application stack yet; the product here is the workflow layer itself.
- The maintained execution surface is a bootstrap installer, a shared validation spec, a reusable validation engine, a source-repo validator, a unittest suite, and a GitHub Actions workflow that runs the same validation commands.
- When real product code lands, update this file and [docs/ai/architecture.md](docs/ai/architecture.md) in the same change.

## Repo Map
- [README.md](README.md): human-facing overview, quick start, and extension guidance.
- [AGENTS.md](AGENTS.md): repo-wide operating map and default workflow.
- [docs/ai/architecture.md](docs/ai/architecture.md): what belongs in the enhancer, what to defer, and when to add more structure.
- [docs/ai/code-review.md](docs/ai/code-review.md): review and PR-prep checklist for docs, skills, scripts, and future workflow assets.
- [docs/ai/roadmap.md](docs/ai/roadmap.md): phased roadmap for stack packs, installer UX, and planned enhancer evolution.
- [.codex/skills/](.codex/skills/): repo-local skills for repeated procedures. Read [.codex/skills/AGENTS.md](.codex/skills/AGENTS.md) before editing or adding skills.
- [install_enhancer.bat](install_enhancer.bat): Windows launcher that opens the GUI installer.
- [scripts/install_enhancer.py](scripts/install_enhancer.py): bootstrap installer, pack manager, and refresh/reconcile planner for target repos.
- [scripts/install_enhancer_gui.py](scripts/install_enhancer_gui.py): GUI wrapper for previewing, confirming, and applying installs, pack changes, upgrades, and refreshes.
- [scripts/stack_packs.py](scripts/stack_packs.py): loader, detection layer, and manifest renderer for optional stack packs.
- [scripts/enhancer_spec.py](scripts/enhancer_spec.py): shared install and validation spec.
- [scripts/enhancer_validator.py](scripts/enhancer_validator.py): reusable validation engine.
- [scripts/check.py](scripts/check.py): deterministic validation for the enhancer source repo.
- [scaffold/target-repo/](scaffold/target-repo/): install scaffold for files that should differ in target repos.
- [scaffold/stack-packs/](scaffold/stack-packs/): file-based registry for optional stack packs and their fragments.
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
- `python scripts/install_enhancer.py --target <path> --mode new` - preview an install into a target repo.
- `python scripts/install_enhancer.py --target <path> --manage-packs --add-pack <name>` - preview a pack-selection change for an installed target.
- `install_enhancer.bat` - open the Windows GUI installer.

## Engineering Rules
- Build repo-local guidance, not framework machinery.
- Prefer `AGENTS.md`, concise docs, narrow skills, and small scripts over packages, daemons, or hidden state.
- Add nested `AGENTS.md` files only when a subtree has materially different rules.
- Add repo-local skills only for repeated, narrow procedures with clear triggers and explicit "do not use" boundaries.
- Add scripts only when they provide deterministic validation or remove repeated manual steps.
- Keep the shared spec, source validator, installer, scaffold, and tests aligned in the same patch.
- Keep local commands and CI in sync. If one changes, update the other in the same patch.
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
- Review checklist: [docs/ai/code-review.md](docs/ai/code-review.md)
- Design roadmap: [docs/ai/roadmap.md](docs/ai/roadmap.md)
