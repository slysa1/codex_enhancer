# Repo Workflow Architecture

## Purpose
This file explains how the Codex workflow layer should stay minimal inside {{REPO_NAME}}.

## Current Layers
1. [AGENTS.md](../../AGENTS.md): the short repo-wide operating map plus a concise summary of any selected stack packs.
2. [docs/ai/](../ai/): durable detail that would bloat `AGENTS.md` if kept inline.
3. [docs/ai/stack-guidance.md](./stack-guidance.md): selected stack-pack guidance from the enhancer install.
4. [.codex/enhancer/manifest.toml](../../.codex/enhancer/manifest.toml): record of detected and selected stack packs.
5. [.codex/skills/](../../.codex/skills/): narrow, repeatable procedures that are worth reusing.
6. [scripts/check.py](../../scripts/check.py): deterministic integrity checks for this workflow layer.
7. [tests/](../../tests/): regression protection for the validator.
8. [.github/workflows/validate.yml](../../.github/workflows/validate.yml): CI that mirrors the local commands.

## What To Keep
- rules that Codex should see immediately
- narrow repeated procedures with clear triggers
- deterministic validation
- short docs that match the repo's real architecture

## What To Remove Or Rewrite
- inherited commands that are not confirmed from this repo
- generic sections that no longer add value
- skills that do not solve a repeated workflow here
- checks that enforce a shape this repo does not actually want

## Extension Rules
- Prefer updating [AGENTS.md](../../AGENTS.md) or an existing doc before adding a new file.
- If a new rule applies repo-wide, put the short version in [AGENTS.md](../../AGENTS.md) and the detail in [docs/ai/](../ai/).
- If a new rule applies only to one subtree, add a nested `AGENTS.md` there.
- If a skill needs more than one narrow procedure, split it or move the guidance into `docs/ai/`.
- If a script needs third-party dependencies, justify them in the same patch.

## Working Rule
Inspect -> adapt -> validate -> review -> ship.
