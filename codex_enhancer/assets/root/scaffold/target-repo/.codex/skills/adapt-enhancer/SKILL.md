---
name: adapt-enhancer
description: Adapt this workflow layer into a real repository. Use when this repo still contains inherited Codex Enhancer bootstrap guidance and you need to replace it with the repo's real commands, docs, skills, and validation rules.
---

# Adapt the installed enhancer into this repo

1. Read [AGENTS.md](../../../AGENTS.md) and [docs/ai/architecture.md](../../../docs/ai/architecture.md) to understand which assets are meant to stay minimal.
2. Inspect this repository before editing:
   - real build, lint, test, and dev commands
   - manifest files and CI workflows
   - any pre-existing AI guidance such as `AGENTS.md`, `CLAUDE.md`, Cursor rules, or Copilot instructions
   - repo areas that genuinely need reusable skills
3. Adapt the inherited assets in this order:
   - root `AGENTS.md`
   - durable docs under `docs/ai/`
   - repo-local skills under `.codex/skills/`
   - `scripts/check.py`
   - `tests/test_check.py`
   - `.github/workflows/validate.yml`
4. Replace guessed or inherited commands with commands confirmed from this repo. If a command does not exist, remove the reference instead of leaving a placeholder.
5. Delete skills, docs, or checks that do not solve a real problem here. Prefer fewer assets that are accurate over a larger inherited set.
6. If this repo needs a repeated procedure, choose the smallest durable home:
   - `AGENTS.md` for the short repo-wide rule
   - `docs/ai/` for durable detail
   - `.codex/skills/` for a narrow repeated workflow
   - `scripts/check.py` only for deterministic validation
7. Run this repo's validation commands and fix drift before calling the adaptation complete.
8. Summarize what was intentionally omitted so this repo does not inherit speculative workflow machinery.

## Guardrails
- Keep this repo specific. Do not leave inherited enhancer commands, paths, or file maps in place after adaptation.
- Prefer deleting a generic section over trying to make it universal.
- Keep local validation, tests, and CI aligned in the same patch.
- Add new skills only when the repo has a repeated, narrow procedure with clear trigger language.

## Do not use
- Do not use once this repo's guidance is already repo specific and the inherited bootstrap text is gone.
- Do not use when you have not inspected the repo's real commands and structure yet.
- Do not use to justify leaving the enhancer installed but unadapted.
