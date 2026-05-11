---
name: adapt-enhancer
description: Adapt this workflow layer into another repository. Use when copying Codex Enhancer into a target repo and you need to replace generic leftovers with that repo's real commands, docs, skills, and validation rules.
---

# Adapt the enhancer into a real repo

1. Read [README.md](../../../README.md), [AGENTS.md](../../../AGENTS.md), and [docs/ai/architecture.md](../../../docs/ai/architecture.md) to understand which assets are meant to stay minimal.
2. Inspect the target repository before editing:
   - real build, lint, test, and dev commands
   - manifest files and CI workflows
   - existing AI guidance such as `AGENTS.md`, `CLAUDE.md`, Cursor rules, or Copilot instructions
   - repo areas that genuinely need reusable skills
3. Adapt the copied assets in this order:
   - root `AGENTS.md`
   - durable docs under `docs/ai/`
   - repo-local skills under `.codex/skills/`
   - `scripts/check.py`
   - `tests/test_check.py`
   - `.github/workflows/validate.yml`
4. Replace guessed or inherited commands with commands confirmed from the target repo. If a command does not exist, remove the reference instead of leaving a placeholder.
5. Delete skills, docs, or checks that do not solve a real problem in the target repo. Prefer fewer assets that are accurate over a larger copied set.
6. If the target repo needs a repeated procedure, choose the smallest durable home:
   - `AGENTS.md` for the short repo-wide rule
   - `docs/ai/` for durable detail
   - `.codex/skills/` for a narrow repeated workflow
   - `scripts/check.py` only for deterministic validation
7. Run the target repo's adapted validation commands and fix drift before calling the install complete.
8. Summarize what was intentionally omitted so the target repo does not inherit speculative workflow machinery.

## Guardrails
- Keep the target repo specific. Do not leave this enhancer's commands, paths, or file map in place after copying.
- Prefer deleting a generic section over trying to make it universal.
- Keep local validation, tests, and CI aligned in the same patch.
- Add new skills only when the target repo has a repeated, narrow procedure with clear trigger language.

## Do not use
- Do not use when editing this enhancer repository itself; use `plan-change` or `review-prep` instead.
- Do not use when you have not inspected the target repo's real commands and structure yet.
- Do not use to justify copying the enhancer unchanged into another repo.
