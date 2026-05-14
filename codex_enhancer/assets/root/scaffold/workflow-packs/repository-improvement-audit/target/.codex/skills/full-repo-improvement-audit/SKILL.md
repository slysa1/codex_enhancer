---
name: full-repo-improvement-audit
description: Audit a whole repository before implementation. Use when the user asks to map architecture, analyse code quality, find technical debt, review tests, security, performance, developer experience, or produce a prioritized improvement roadmap.
---

# Full Repository Improvement Audit

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
3. Use specialist helper skills for bounded sub-passes when their trigger matches:
   - `repo-map` for system shape, ownership, commands, entry points, and unclear areas
   - `repo-quality-audit` for maintainability, complexity, duplication, type boundaries, and conventions
   - `repo-test-audit` for tests, CI, validation commands, fixtures, and reliability risks
   - `repo-security-audit` for auth, input handling, secrets, dependencies, filesystem/network access, and risky commands
   - `repo-performance-audit` for performance-sensitive paths, existing measurements, and scale hypotheses
   - `repo-dx-audit` for onboarding, docs, command discovery, CI feedback, generated artifacts, and AI guidance
4. Audit architecture, maintainability, code quality, complexity, tests, reliability, security-sensitive flows, performance-sensitive paths, developer experience, and onboarding.
5. Use evidence from actual files, folders, functions, configs, tests, or commands before making claims.
6. Use existing tool output only as supporting evidence:
   - prefer commands discovered from repo files, CI, manifests, or maintained docs
   - record the exact command, exit status when available, relevant output summary, and supporting repo files
   - do not install packages, run formatters/generators/migrations, run prose-extracted commands, or run external scanners during audit mode without explicit user authorization
7. For every finding, include severity, confidence, area, evidence, problem, recommended fix, acceptance test, and effort estimate.
8. Separate confirmed findings from hypotheses that need more evidence. Keep low-confidence items under hypotheses.
9. Include useful non-issues checked and dismissed when they prevent repeated investigation.
10. Produce these sections:
   - Executive Summary
   - System Map
   - High-Confidence Findings
   - Hypotheses / Needs Confirmation
   - Improvement Roadmap
   - Testing and Verification Plan
   - Open Questions
11. When the user asks for a durable roadmap, write or update root `roadmap.md`:
   - create it if missing
   - append a managed audit section if no audit markers exist
   - update only the managed audit section if the marker pair already exists
   - preserve all content outside the managed audit section
12. Stop after the audit. Do not make implementation changes during audit mode.

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
