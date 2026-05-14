# Repository Improvement Audit

## Purpose
Use this workflow for a no-implementation audit of this repository before choosing follow-up changes. The audit should map the system, identify evidence-backed risks and technical debt, separate confirmed findings from hypotheses, and produce a prioritized improvement roadmap.

This workflow is selected explicitly through Codex Enhancer workflow-pack management. It does not run automatically, install dependencies, stage changes, or modify application code.

## When To Use
Use this workflow when the user asks Codex to:
- audit the whole repository before implementation
- map architecture, ownership boundaries, or entry points
- analyze code quality, maintainability, or technical debt
- review tests, reliability, security-sensitive flows, performance-sensitive paths, or developer experience
- produce or refresh a prioritized improvement roadmap

## When Not To Use
Do not use this workflow for:
- single-file edits
- direct implementation tasks
- normal bounded PR review
- target-repo adaptation after installing Codex Enhancer, unless the user asks for a broader repository-improvement audit
- any pass where Codex should edit code, configuration, dependencies, tests, or product documentation during the same audit

## Audit Order
1. Read repo guidance first: root `AGENTS.md`, README files, `docs/ai/`, nested instructions, and existing agent guidance.
2. Inspect repository shape: top-level directories, package files, entry points, scripts, tests, docs, generated folders, and CI.
3. Identify real commands from manifests, task runners, CI workflows, and documented validation steps.
4. Build a system map before judging quality.
5. Audit architecture, code quality, tests/reliability, security, performance, and developer experience with evidence.
6. Separate confirmed findings from hypotheses.
7. Prioritize findings into a roadmap.
8. Write or update the audit roadmap artifact when the user requests a durable roadmap.
9. Stop before implementation.

## Evidence Standards
Every confirmed claim needs evidence from inspected repo files, commands, tests, configs, or documented behavior. Prefer exact paths and named functions, classes, scripts, workflows, or configuration keys. If the audit cannot confirm a claim, record it as a hypothesis with the evidence still needed.

Do not infer build, lint, test, coverage, architecture, dependencies, deployment, or security posture from common stack conventions alone. If a command is not present in files or docs, say that it was not found.

## Specialist Skills
The `full-repo-improvement-audit` skill remains the orchestrator. Use specialist skills only for bounded audit sub-passes:
- `repo-map`
- `repo-quality-audit`
- `repo-test-audit`
- `repo-security-audit`
- `repo-performance-audit`
- `repo-dx-audit`

Specialist output feeds the final audit report; it does not replace the orchestrator or start implementation.

## Tool-Assisted Evidence
Existing repo tools can support an audit when they are discovered from inspected files, CI, manifests, or maintained docs. Examples include listed test commands, lint commands, type checks, coverage reports, dependency audit commands, and optional Utility Harness helpers such as `tools/ai/audit_inputs.py` and `tools/ai/run_checks.py --list`.

Treat tool output as supporting evidence, not authority. Tie every tool-backed claim to the exact command, exit status when available, relevant output summary, and the repo files that explain why the command is legitimate for this project. If a tool is unavailable, too slow, needs credentials, needs network access, or depends on packages that are not installed, record that as a limitation or hypothesis input rather than installing dependencies during the audit.

Do not run prose-extracted commands, shell-control-heavy commands, dependency installs, formatters, generators, migrations, or external scanners during audit mode unless the user explicitly authorizes that exact action. Missing optional static-analysis inputs should never block the audit; they should only affect confidence.

## Expected Output
Use these sections:
- Executive Summary
- System Map
- High-Confidence Findings
- Hypotheses / Needs Confirmation
- Improvement Roadmap
- Testing and Verification Plan
- Open Questions

Confirmed findings should follow [repo-audit-finding-schema.md](repo-audit-finding-schema.md). Prioritized roadmap items should follow [repo-audit-roadmap-rubric.md](repo-audit-roadmap-rubric.md).

## Roadmap Artifact
When the user asks for durable suggested changes, write them to this repository's root `roadmap.md`.

If `roadmap.md` does not exist, create it with a concise title plus the managed audit section. If it already exists without Codex Enhancer audit markers, append the managed audit section and preserve existing content. If it already contains the marker pair, update only the content between those markers and preserve everything outside the section.

Use these exact markers:

```text
<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit start -->
<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit end -->
```

The managed section should contain prioritized suggestions, evidence summary, and validation ideas from the latest audit. It should not mark implementation tasks complete, rewrite unrelated roadmap sections, or delete repo-owned planning history.

## Stopping Condition
The audit stops after producing the report and requested `roadmap.md` audit artifact. Codex should not stage changes, run formatters that rewrite files, add scripts, install packages, or begin implementation during audit mode. Implementation starts only after the user chooses a follow-up item.
