# Repo Workflow Architecture

## Purpose
This file explains how the Codex workflow layer should stay minimal inside {{REPO_NAME}}.

## Current Layers
1. [AGENTS.md](../../AGENTS.md): the short repo-wide operating map plus a concise summary of any selected stack packs.
2. [docs/ai/](../ai/): durable detail that would bloat `AGENTS.md` if kept inline.
3. [docs/ai/spec-kit-bridge.md](./spec-kit-bridge.md): enhancer-managed bridge guidance for repos that also use official GitHub Spec Kit; safe to regenerate later.
4. [docs/ai/stack-guidance.md](./stack-guidance.md): selected stack-pack guidance from the enhancer install and safe to regenerate later.
5. [.codex/enhancer/manifest.toml](../../.codex/enhancer/manifest.toml): record of detected and selected stack packs, lifecycle state, visible pack evidence, managed-output ownership, and Spec Kit bridge state; also safe to regenerate later.
6. [.codex/skills/](../../.codex/skills/): narrow, repeatable procedures that are worth reusing.
7. [scripts/check.py](../../scripts/check.py): deterministic integrity checks for this workflow layer.
8. [tests/](../../tests/): regression protection for the validator.
9. [.github/workflows/validate.yml](../../.github/workflows/validate.yml): CI that mirrors the local commands.
10. Optional Utility Harness files, when installed: `requirements-codex.txt`, `tools/ai/`, and `docs/ai/utility-harness.md` for Codex/operator inspection only.

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

## Managed Output Rule
- Treat [docs/ai/stack-guidance.md](./stack-guidance.md), [docs/ai/spec-kit-bridge.md](./spec-kit-bridge.md), and [.codex/enhancer/manifest.toml](../../.codex/enhancer/manifest.toml) as installer-managed outputs that are safe to regenerate later.
- Treat [AGENTS.md](../../AGENTS.md) and the rest of the scaffolded workflow files as repo-owned starting points that should usually be adapted by hand.
- Keep the manifest schema and lifecycle metadata intact when editing by hand; use the enhancer upgrade or refresh flow if schema drift appears.
- Keep the visible managed-section markers around the selected stack-pack summary and the Spec Kit bridge summary in [AGENTS.md](../../AGENTS.md); only the content inside those markers is enhancer-owned and safe for future managed updates.
- Treat official Spec Kit files such as `.specify/`, `specs/`, `.github/prompts/`, and `.github/agents/` as separately owned unless the repo deliberately opts into a deeper bridge workflow later.
- Treat Utility Harness dependencies as Codex/operator-only helper dependencies. Do not mix `requirements-codex.txt` into production dependency files.

## Extension Rules
- Prefer updating [AGENTS.md](../../AGENTS.md) or an existing doc before adding a new file.
- If a new rule applies repo-wide, put the short version in [AGENTS.md](../../AGENTS.md) and the detail in [docs/ai/](../ai/).
- If a new rule applies only to one subtree, add a nested `AGENTS.md` there.
- If a skill needs more than one narrow procedure, split it or move the guidance into `docs/ai/`.
- If a script needs third-party dependencies, justify them in the same patch.

## Working Rule
Inspect -> adapt -> validate -> review -> ship.
