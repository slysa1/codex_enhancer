---
name: plan-change
description: Plan a non-trivial change in this repository before editing. Use when work touches multiple workflow assets such as AGENTS files, docs/ai, repo-local skills, scripts, validation rules, or repo conventions, and the change needs explicit scope, tradeoffs, and validation steps.
---

# Plan the change

1. Read [AGENTS.md](../../../AGENTS.md) and [docs/ai/architecture.md](../../../docs/ai/architecture.md).
2. Inspect every file likely to be touched before proposing structure.
3. State the plan in six short parts:
   - objective
   - files to change
   - files deliberately not added
   - validation commands
   - tooling and consent
   - main risk of getting the change wrong
4. Prefer updating an existing file over creating a new one.
5. Keep the plan proportional. A multi-file architecture change may need more detail; a small cleanup should stay brief.
6. In the tooling and consent note, answer: "What packages, programs, or apps would I need to implement this goal optimally?" Separate already-available repo/local tools from new downloads, and ask for explicit user consent before downloading or installing anything.
7. After planning, execute the change unless the user explicitly asked to stop at planning or the next step requires unapproved software installation.

## Guardrails
- Keep the enhancer legible. Avoid adding layers that only help in theory.
- Use a nested `AGENTS.md` only when a subtree has genuinely different rules.
- Add scripts only when they create deterministic validation or remove repeated manual toil.
- Keep local commands, tests, and CI aligned in the same patch.
- Treat docs as the source of truth for durable guidance; keep root `AGENTS.md` as the map.
- Prefer existing repo tools and installed local programs before proposing new software.
- Never download or install packages, programs, or apps during planning; ask for consent first when new software is genuinely useful.

## Do not use
- Do not use for single-file copy edits or obvious mechanical fixes.
- Do not use to justify speculative packages, apps, MCP servers, or CI workflows.
- Do not stop after writing a plan unless the user explicitly asked for planning only.
