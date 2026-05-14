---
name: full-repo-improvement-audit
description: Audit a whole repository before implementation. Use when the user asks to map architecture, analyse code quality, find technical debt, review tests, security, performance, developer experience, or produce a prioritized improvement roadmap.
---

# Full repository improvement audit

Run a no-implementation repository audit before follow-up work.

1. Read repo guidance first:
   - `AGENTS.md`
   - README files
   - `docs/ai/`
   - build, test, lint, CI, and package config
   - existing AI guidance such as `.codex/skills`, `.agents/skills`, `CLAUDE.md`, Cursor rules, or Copilot instructions
2. Build a system map:
   - repo purpose
   - top-level directories
   - major components
   - entry points
   - build, test, and lint commands
   - CI/CD setup
   - dependencies and integrations
   - unclear areas
3. Audit architecture, maintainability, code quality, complexity, tests, reliability, security-sensitive flows, performance-sensitive paths, developer experience, and onboarding.
4. Use evidence from actual files, folders, functions, configs, tests, or commands before making claims.
5. Use existing tool output only as supporting evidence:
   - prefer commands discovered from repo files, CI, manifests, or maintained docs
   - record the exact command, exit status when available, relevant output summary, and supporting repo files
   - do not install packages, run formatters/generators/migrations, run prose-extracted commands, or run external scanners during audit mode without explicit user authorization
6. For every finding, include severity, confidence, area, evidence, problem, recommended fix, acceptance test, and effort estimate.
7. Separate confirmed findings from hypotheses that need more evidence. Keep low-confidence items under hypotheses.
8. Include useful non-issues checked and dismissed when they prevent repeated investigation.
9. Produce these sections:
   - Executive Summary
   - System Map
   - High-Confidence Findings
   - Hypotheses / Needs Confirmation
   - Improvement Roadmap
   - Testing and Verification Plan
   - Open Questions
10. When the user asks for a durable roadmap, write or update root `roadmap.md`:
   - create it if missing
   - append a managed audit section if no audit markers exist
   - update only the managed audit section if the marker pair already exists
   - preserve all content outside the managed audit section
11. Stop after the audit. Do not make implementation changes during audit mode.

Use these exact markers for the managed `roadmap.md` section:

```text
<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit start -->
<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit end -->
```

## Do not use

- Do not use for single-file edits or narrow implementation tasks.
- Do not use for normal PR review unless the user asks for a repo-wide audit.
- Do not make implementation changes during audit mode.
- Do not modify files during audit mode except the requested root `roadmap.md` audit artifact.
- Do not invent commands, architecture, coverage, dependencies, or risks not supported by inspected files.
