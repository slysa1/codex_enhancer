---
name: repo-test-audit
description: Audit tests and reliability during a full repo audit. Use when the audit needs evidence about test layout, validation commands, CI coverage, fixtures, flaky risks, and missing regression protection.
---

# Repository Test Audit

Run as a no-implementation specialist sub-pass inside `full-repo-improvement-audit`.

1. Identify test directories, test frameworks, validation commands, CI jobs, fixtures, and documented manual checks from repo files.
2. Run only commands that are explicitly present in manifests, CI, scripts, or maintained docs and practical for the audit scope.
3. Record command, exit status, output summary, and the repo files that justify the command.
4. Identify missing coverage, brittle fixtures, slow or flaky risks, unclear setup, and untested high-risk behavior.
5. Report only evidence-backed findings and return control to `full-repo-improvement-audit`.

Output contract:
- Test and CI map
- Commands run or deliberately not run
- Coverage and reliability findings
- Missing regression risks
- Verification plan for roadmap items

## Do not use

- Do not invent test commands from framework conventions.
- Do not install dependencies, create fixtures, update snapshots, or run destructive checks.
- Do not treat an unavailable optional tool as a failed audit.
