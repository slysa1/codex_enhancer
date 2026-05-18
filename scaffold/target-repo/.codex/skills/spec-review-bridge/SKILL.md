---
name: spec-review-bridge
description: Prepare review notes for Spec Kit-driven work. Use when a branch was implemented from Spec Kit artifacts and the handoff should summarize code, validation, and any remaining drift against the feature artifacts.
---

# Prepare Spec-Aware Review Notes

1. Identify the active feature folder under `specs/`.
2. Summarize the implementation against `spec.md`, `plan.md`, and `tasks.md`.
3. Call out any contract, quickstart, or workflow notes reviewers should verify.
4. Record the exact validation that ran.
5. Separate completed work from remaining drift or follow-up.

## Cross-Agent Review Safety
- If invoking a cross-agent review, share only relevant Spec Kit artifacts, reviewed diffs, implementation notes, and validation evidence for the active feature.
- Exclude secrets, credentials, tokens, raw environment values, unrelated private files, and unrelated repo content from shared context.
- Ask separately before any peer CLI smoke test, network call, package install, or sandbox escalation.

## Boundaries
- Keep the review summary anchored in the actual feature artifacts.
- Use this after implementation and validation, not as a substitute for them.
- Treat official Spec Kit files as separately owned inputs.

## Do not use
- Do not use this when the change was not driven by Spec Kit artifacts.
- Do not rewrite official Spec Kit history inside review notes.
- Do not hide unresolved spec drift; surface it explicitly.
