# Repository Improvement Audit

## Purpose
A repository improvement audit is a read-only pass that helps Codex understand an existing repo before proposing changes. It maps the system, identifies high-confidence risks and technical debt, separates evidence from hypotheses, and ends with a prioritized improvement roadmap.

The workflow belongs in Codex Enhancer because it is repo-local guidance, not a hidden runtime. It gives Codex a repeatable way to inspect unfamiliar repositories without adding installer flags, static-analysis integrations, or implementation automation before the need is proven.

## When To Use
Use this workflow when the user asks to:
- audit a whole repository before implementation
- map architecture or ownership boundaries
- analyze code quality, maintainability, or technical debt
- review tests, reliability, security, performance, or developer experience
- produce a prioritized improvement roadmap

## When Not To Use
Do not use this workflow for:
- single-file fixes
- normal PR review of a bounded diff
- feature implementation that already has a clear plan
- target-repo adaptation after installing Codex Enhancer, unless the user asks for a broader repository-improvement audit
- any task where Codex should edit files during the same pass

## Audit Order
1. Read repo guidance first: root `AGENTS.md`, README files, `docs/ai/`, AI guidance, and any nested instructions.
2. Inspect the repository shape: top-level directories, package files, entry points, generated folders, tests, docs, scripts, and CI.
3. Identify real commands from files such as package manifests, task runners, CI workflows, and documented validation steps.
4. Build a system map before judging quality.
5. Audit each area with evidence.
6. Separate confirmed findings from hypotheses.
7. Prioritize findings into a roadmap.
8. Stop before implementation.

## Evidence Standards
Every confirmed claim needs evidence from inspected repo files, commands, tests, configs, or documented behavior. Prefer exact paths and named functions, classes, scripts, workflows, or configuration keys. If the audit cannot confirm a claim, record it as a hypothesis with the evidence still needed.

Do not infer build, lint, test, coverage, architecture, dependencies, deployment, or security posture from common stack conventions alone. If a command is not present in files or docs, say that it was not found.

## Audit Areas

### Architecture
Map the repo purpose, top-level directories, major components, entry points, ownership boundaries, integration points, and unclear areas. Look for circular dependencies, misplaced responsibilities, unowned generated output, or guidance that no longer matches the repo.

### Code Quality
Review complexity, duplication, naming, type boundaries, error handling, configuration handling, dependency usage, and local conventions. Prefer specific examples over general style commentary.

### Tests And Reliability
Map the test layout, known validation commands, fixture strategy, CI coverage, flaky or slow areas, missing regression coverage, and behavior that appears hard to verify. Distinguish missing tests from tests that exist but were not run.

### Security
Inspect authentication, authorization, input validation, secret handling, dependency surfaces, file/network boundaries, and risky command execution only where the repo has those flows. Avoid security claims without traceable evidence.

### Performance
Look for performance-sensitive paths such as startup, build time, hot loops, database queries, network calls, asset pipelines, and large-file processing. Treat performance risk as a hypothesis unless code or measured output supports it.

### Developer Experience
Review onboarding docs, command discoverability, local setup, error messages, generated artifacts, CI feedback, repo-local AI guidance, and the clarity of review or release procedures.

## Expected Output Structure
An audit report should use these sections:
- Executive Summary
- System Map
- High-Confidence Findings
- Hypotheses / Needs Confirmation
- Improvement Roadmap
- Testing and Verification Plan
- Open Questions

Confirmed findings should follow the schema in [repo-audit-finding-schema.md](repo-audit-finding-schema.md). The roadmap should use the prioritization rubric in [repo-audit-roadmap-rubric.md](repo-audit-roadmap-rubric.md).

## Stopping Condition
The audit stops after producing the report and roadmap. Codex should not modify files, stage changes, run formatters that rewrite files, add scripts, install packages, or begin implementation during audit mode. Implementation starts only after the user chooses a follow-up item.

## Future Direction
This first pass is intentionally limited to docs, one orchestrator skill, and a render-only workflow-pack asset foundation. Future work may add workflow-pack installer support, target-repo scaffold integration, specialist audit skills, or static-analysis-assisted inputs when those tools are discovered from actual repo files. It should not add a command ecosystem or hidden audit runtime.
