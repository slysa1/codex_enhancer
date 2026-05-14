---
name: repo-security-audit
description: Audit security-sensitive repository surfaces during a full repo audit. Use when the audit needs evidence about auth, authorization, input handling, secrets, dependency boundaries, filesystem or network access, and risky command execution.
---

# Repository Security Audit

Run as a no-implementation specialist sub-pass inside `full-repo-improvement-audit`.

1. Identify whether the repo actually contains security-sensitive flows before making security claims.
2. Inspect authentication, authorization, input validation, secret handling, dependency loading, filesystem access, network access, subprocess use, and installer or CI command execution.
3. Tie every concern to specific files, call paths, configs, commands, or tests.
4. Classify unconfirmed concerns as hypotheses and state what evidence would validate or dismiss them.
5. Report only evidence-backed findings and return control to `full-repo-improvement-audit`.

Output contract:
- Security-sensitive surface map
- Confirmed findings with evidence
- Hypotheses and missing evidence
- Severity and confidence
- Safe verification idea for each recommendation

## Do not use

- Do not perform exploit attempts, credential access, secret scanning outside repo files, or external scanning without explicit authorization.
- Do not claim vulnerabilities from dependency names or framework conventions alone.
- Do not edit files, stage changes, install packages, or change security configuration.
