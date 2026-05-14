# Repository Improvement Audit

## Purpose
A repository improvement audit is a no-implementation pass that helps Codex understand an existing repo before proposing changes. It maps the system, identifies high-confidence risks and technical debt, separates evidence from hypotheses, and ends with a prioritized improvement roadmap.

The workflow belongs in Codex Enhancer because it is repo-local guidance, not a hidden runtime. It gives Codex a repeatable way to inspect unfamiliar repositories without adding static-analysis integrations, implementation automation, or background audit execution before the need is proven.

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
- any task where Codex should edit code, configuration, dependencies, tests, or product documentation during the same pass

## Audit Order
1. Read repo guidance first: root `AGENTS.md`, README files, `docs/ai/`, AI guidance, and any nested instructions.
2. Inspect the repository shape: top-level directories, package files, entry points, generated folders, tests, docs, scripts, and CI.
3. Identify real commands from files such as package manifests, task runners, CI workflows, and documented validation steps.
4. Build a system map before judging quality.
5. Audit each area with evidence.
6. Separate confirmed findings from hypotheses.
7. Prioritize findings into a roadmap.
8. Write or update the audit roadmap artifact when the user requested a durable roadmap.
9. Stop before implementation.

## Evidence Standards
Every confirmed claim needs evidence from inspected repo files, commands, tests, configs, or documented behavior. Prefer exact paths and named functions, classes, scripts, workflows, or configuration keys. If the audit cannot confirm a claim, record it as a hypothesis with the evidence still needed.

Do not infer build, lint, test, coverage, architecture, dependencies, deployment, or security posture from common stack conventions alone. If a command is not present in files or docs, say that it was not found.

## Tool-Assisted Evidence
Existing repo tools can support an audit when they are discovered from inspected files, CI, manifests, or maintained docs. Examples include listed test commands, lint commands, type checks, coverage reports, dependency audit commands, and optional Utility Harness helpers such as `tools/ai/run_checks.py --list`.

Treat tool output as supporting evidence, not authority. Tie every tool-backed claim to the exact command, exit status when available, relevant output summary, and the repo files that explain why the command is legitimate for this project. If a tool is unavailable, too slow, needs credentials, needs network access, or depends on packages that are not installed, record that as a limitation or hypothesis input rather than installing dependencies during the audit.

Do not run prose-extracted commands, shell-control-heavy commands, dependency installs, formatters, generators, migrations, or external scanners during audit mode unless the user explicitly authorizes that exact action. Missing optional static-analysis inputs should never block the audit; they should only affect confidence.

## Audit Areas

The `full-repo-improvement-audit` skill remains the orchestrator. Specialist audit skills are now available for bounded sub-passes when the audit needs a sharper lens:
- `repo-map` for system shape, entry points, commands, integrations, and ownership boundaries
- `repo-quality-audit` for maintainability, complexity, duplication, type boundaries, and local conventions
- `repo-test-audit` for tests, CI, validation commands, fixtures, missing coverage, and reliability risks
- `repo-security-audit` for auth, input handling, secrets, dependency boundaries, filesystem/network access, and risky commands
- `repo-performance-audit` for performance-sensitive paths, measurements, scale risks, and hypotheses
- `repo-dx-audit` for onboarding, docs, command discovery, CI feedback, generated artifacts, and AI guidance

Specialist output feeds the final audit report; it does not replace the orchestrator or start implementation.

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

## Roadmap Artifact
When the user asks for durable suggested changes, write them to the target repo's root `roadmap.md`.

If `roadmap.md` does not exist, create it with a concise title plus the managed audit section. If it already exists without Codex Enhancer audit markers, append the managed audit section and preserve all existing content. If it already contains the marker pair, update only the content between those markers and preserve everything outside the section.

Use these exact markers for the managed audit section:

```text
<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit start -->
<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit end -->
```

The managed section should contain the prioritized suggestions, evidence summary, and validation plan from the latest audit. It should not mark implementation tasks complete, rewrite unrelated roadmap sections, or delete repo-owned planning history.

## Stopping Condition
The audit stops after producing the report and roadmap artifact. Codex should not modify files other than the requested `roadmap.md` audit artifact, stage changes, run formatters that rewrite files, add scripts, install packages, or begin implementation during audit mode. Implementation starts only after the user chooses a follow-up item.

## Future Direction
The current workflow-pack support is intentionally explicit and artifact-oriented: selecting the audit workflow generates workflow guidance, installs target audit docs and the audit skills, records manifest state, and manages only the root `roadmap.md` audit section. Future static-analysis tooling should remain bounded, optional, and evidence-oriented. It should not add a command ecosystem, hidden audit runtime, or automatic implementation path.
