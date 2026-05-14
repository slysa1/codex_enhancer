---
name: repo-quality-audit
description: Audit maintainability and code quality during a full repo audit. Use when the audit needs evidence about complexity, duplication, naming, type boundaries, error handling, configuration, and local conventions.
---

# Repository Quality Audit

Run as a no-implementation specialist sub-pass inside `full-repo-improvement-audit`.

1. Start from the repo map and inspect representative code paths before judging style.
2. Look for complexity, duplication, unclear naming, leaky abstractions, type-boundary gaps, fragile error handling, configuration drift, and convention mismatches.
3. Tie every concern to specific files, symbols, tests, configs, or command output.
4. Separate confirmed maintainability findings from subjective preferences and low-confidence hypotheses.
5. Report only evidence-backed findings and return control to `full-repo-improvement-audit`.

Output contract:
- Maintainability findings
- Evidence and affected paths
- Impact and likely blast radius
- Suggested improvement direction
- Acceptance check for each recommendation

## Do not use

- Do not use for formatting-only review or broad style preferences.
- Do not propose rewrites without showing why a smaller improvement is insufficient.
- Do not edit files, stage changes, install packages, or run formatters.
