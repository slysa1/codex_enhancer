# {{REPO_NAME}}

## Purpose
This repository uses a Codex-native workflow layer so Codex can understand the repo faster, follow clearer conventions, and validate changes with less prompt repetition.

## Current State
- This workflow layer was bootstrapped by Codex Enhancer.
- Treat inherited generic guidance as a starting point, not final truth.
- Use the `adapt-enhancer` skill until this file, the docs under `docs/ai/`, and the validation rules match this repository's real shape.

## Repo Map
- [AGENTS.md](AGENTS.md): repo-wide operating map and default workflow.
- [docs/ai/architecture.md](docs/ai/architecture.md): what should stay minimal and what should be moved into deeper docs or skills.
- [docs/ai/code-review.md](docs/ai/code-review.md): review and PR-prep checklist for workflow assets and future repo rules.
- [docs/ai/spec-kit-bridge.md](docs/ai/spec-kit-bridge.md): how this repo should coexist with official GitHub Spec Kit if the team uses it.
- [docs/ai/stack-guidance.md](docs/ai/stack-guidance.md): optional stack-pack guidance selected during enhancer install.
- [.codex/skills/](.codex/skills/): repo-local skills for repeated procedures. Read [.codex/skills/AGENTS.md](.codex/skills/AGENTS.md) before editing or adding skills.
- [.codex/enhancer/manifest.toml](.codex/enhancer/manifest.toml): record of detected and selected enhancer stack packs.
- [scripts/check.py](scripts/check.py): deterministic validation for this repo's Codex workflow layer.
- [tests/](tests/): unit tests for the validator.
- [.github/workflows/validate.yml](.github/workflows/validate.yml): CI that mirrors the local validation commands.

## Discovered Commands
{{DISCOVERED_COMMANDS}}

## Existing Repo Guidance To Review
{{EXISTING_GUIDANCE}}

## Selected Stack Packs
<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs start -->
{{PACK_AGENTS_SUMMARY}}
<!-- codex-enhancer:managed-section AGENTS.md:selected-stack-packs end -->

## Spec Kit Bridge
<!-- codex-enhancer:managed-section AGENTS.md:spec-kit-bridge start -->
{{SPEC_KIT_BRIDGE_SUMMARY}}
<!-- codex-enhancer:managed-section AGENTS.md:spec-kit-bridge end -->

## Utility Harness
{{UTILITY_HARNESS_SUMMARY}}

## Default Workflow
1. Inspect the relevant files before editing anything.
2. For non-trivial workflow changes, use the `plan-change` skill in [.codex/skills/plan-change/](.codex/skills/plan-change/).
3. Prefer editing an existing file over creating a new one.
4. Keep AGENTS files short; move durable detail into [docs/ai/](docs/ai/).
5. After changes, run `python scripts/check.py` and `python -m unittest discover -s tests -p "test_*.py" -v`.
6. Before handing a patch off for review, use the `review-prep` skill in [.codex/skills/review-prep/](.codex/skills/review-prep/).
7. If this bootstrap layer still contains inherited generic guidance, use [.codex/skills/adapt-enhancer/](.codex/skills/adapt-enhancer/) to make it repo-specific.

## Engineering Rules
- Replace guessed commands with commands confirmed from the repo.
- Prefer `AGENTS.md`, concise docs, narrow skills, and small scripts over packages, daemons, or hidden state.
- Add nested `AGENTS.md` files only when a subtree has materially different rules.
- Add repo-local skills only for repeated, narrow procedures with clear triggers and explicit non-goals.
- Add scripts only when they provide deterministic validation or remove repeated manual steps.
- Keep local commands and CI in sync. If one changes, update the other in the same patch.
- Delete inherited enhancer assets that do not solve a real problem in this repository.
- Treat official Spec Kit files such as `.specify/`, `specs/`, `.github/prompts/`, and `.github/agents/` as separately owned unless this repo explicitly chooses a deeper bridge later.

## Review Expectations
- Explain why each workflow file exists and why a simpler alternative was not enough.
- Record the exact validation performed.
- Call out what was intentionally omitted so the repo does not accumulate speculative workflow machinery.
- Flag any inherited generic guidance that still needs repo-specific replacement.

## Definition Of Done
- The requested change is implemented with the smallest useful file set.
- `python scripts/check.py` passes.
- `python -m unittest discover -s tests -p "test_*.py" -v` passes.
- Paths, commands, and links in docs resolve correctly.
- Any remaining inherited generic guidance is called out explicitly, not left implied.
- If validation commands changed, [.github/workflows/validate.yml](.github/workflows/validate.yml) changed with them.

## Subagents
Use subagents only when parallel exploration or an independent review materially speeds up a large change.
Do not use subagents for small doc edits, single-skill changes, or work blocked on one local file.

## Immediate Follow-up
1. Inspect the repo's real build, lint, test, and dev commands.
2. Replace any inherited generic sections with repo-specific guidance.
3. Remove skills, docs, or checks that do not solve a real problem here.
