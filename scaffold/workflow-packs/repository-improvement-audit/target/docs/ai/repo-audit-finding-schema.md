# Repository Audit Finding Schema

## Purpose
Use this schema for findings produced by the full repository improvement audit. It keeps audit output evidence-backed, comparable, and ready to turn into implementation work after the audit stops.

## Finding Fields
- `ID`: stable identifier for the audit report, such as `AUD-001`.
- `Title`: short description of the issue.
- `Area`: architecture, code quality, tests/reliability, security, performance, developer experience, or another repo-specific area.
- `Severity`: Critical, High, Medium, or Low.
- `Confidence`: High, Medium, or Low.
- `Evidence`: inspected files, folders, functions, configs, tests, commands, or CI entries that support the finding.
- `Problem`: what is wrong or risky.
- `Impact`: why the issue matters to users, maintainers, correctness, safety, cost, or delivery.
- `Recommendation`: the smallest useful fix or investigation path.
- `Acceptance Test`: how a reviewer can tell the fix worked.
- `Effort`: rough estimate such as S, M, L, or XL.
- `Dependencies/Blockers`: prerequisite decisions, missing context, sequencing constraints, or external ownership.

## Severity Rubric
- `Critical`: likely active correctness, data-loss, security, release-blocking, or severe operational risk.
- `High`: likely user-visible failure, major maintainability drag, security exposure, or unreliable delivery path.
- `Medium`: meaningful improvement with bounded risk, moderate technical debt, or missing coverage around important behavior.
- `Low`: cleanup, clarity, consistency, or minor hardening that is useful but not urgent.

## Confidence Rubric
- `High`: directly supported by inspected code, tests, configs, docs, or command output.
- `Medium`: supported by multiple repo signals, but the exact failure mode or impact needs confirmation.
- `Low`: plausible concern with limited evidence.

Low-confidence items must go under `Hypotheses / Needs Confirmation`, not `High-Confidence Findings`.

## Evidence Rules
Evidence should name concrete repo artifacts. Use paths, functions, scripts, config keys, workflows, test names, or command results when available. If evidence is indirect, say what would confirm or disprove it.

Do not present missing information as a confirmed finding. For example, "no test command found in inspected docs or CI" is a confirmed observation; "the repo has no tests" is only confirmed if the test tree and tooling were inspected.
