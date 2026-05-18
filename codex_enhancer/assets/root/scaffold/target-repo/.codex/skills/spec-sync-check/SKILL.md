---
name: spec-sync-check
description: Compare changed code against existing Spec Kit artifacts. Use when code already changed and you need to check for drift against `spec.md`, tasks, contracts, quickstart notes, or other feature artifacts.
---

# Check Spec Drift

1. Identify the active feature folder under `specs/`.
2. Re-read `spec.md`, `tasks.md`, and any relevant `contracts/`, `quickstart.md`, `research.md`, or `data-model.md` files.
3. Compare the implemented code and validation evidence against those artifacts.
4. List concrete mismatches, omissions, or follow-up work.
5. Prefer deterministic checks and file references over broad prose.

## Cross-Agent Review Safety
- If invoking a cross-agent review, share only relevant Spec Kit artifacts, reviewed diffs, implementation notes, and validation evidence for the active feature.
- Exclude secrets, credentials, tokens, raw environment values, unrelated private files, and unrelated repo content from shared context.
- Ask separately before any peer CLI smoke test, network call, package install, or sandbox escalation.

## Boundaries
- Use this for drift detection, not for authoring new specs.
- Keep the output reviewable and artifact-backed.
- Treat official Spec Kit files as separately owned.

## Do not use
- Do not use this when no active Spec Kit artifacts exist.
- Do not silently edit specs to fit the code; report the mismatch first.
- Do not replace normal repo tests or review with this skill alone.
