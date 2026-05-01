---
name: spec-implement-bridge
description: Implement code from existing Spec Kit feature artifacts. Use when a repo already has `spec.md`, `plan.md`, or `tasks.md` for the active feature and you need repo-aware implementation rather than new spec authoring.
---

# Implement From Existing Spec Kit Artifacts

1. Identify the active feature folder under `specs/`.
2. Read `spec.md`, `plan.md`, and `tasks.md` before editing code.
3. Check for `contracts/`, `quickstart.md`, `research.md`, and `data-model.md` if they exist.
4. Implement the smallest coherent slice that matches the active tasks and repo conventions.
5. Validate the change with the repo's real commands.
6. Call out any code-vs-spec drift explicitly instead of silently guessing.

## Boundaries
- Use this only after official Spec Kit artifacts already exist.
- Keep enhancer guidance focused on implementation, validation, and review.
- Treat `.specify/`, `specs/`, and official Spec Kit prompt, agent, or skill files as separately owned.

## Do not use
- Do not use this skill to replace official Spec Kit commands like `specify`, `plan`, or `tasks`.
- Do not use it when the repo has no active Spec Kit feature artifacts.
- Do not rewrite official Spec Kit templates or historical feature records from this skill.
