---
name: repo-performance-audit
description: Audit performance-sensitive repository paths during a full repo audit. Use when the audit needs evidence about startup, build time, hot loops, large-file processing, database or network calls, asset pipelines, and measurement gaps.
---

# Repository Performance Audit

Run as a no-implementation specialist sub-pass inside `full-repo-improvement-audit`.

1. Identify performance-sensitive paths from repo purpose, entry points, scripts, tests, configs, and docs.
2. Prefer existing benchmark, profiling, build, or test output when commands are present and practical.
3. Inspect code paths for obvious scale risks such as repeated full-tree scans, unbounded loops, large-file reads, synchronous network calls, or expensive startup work.
4. Treat performance risk as a hypothesis unless code, config, command output, or documented behavior supports it.
5. Report only evidence-backed findings and return control to `full-repo-improvement-audit`.

Output contract:
- Performance-sensitive path map
- Existing measurement commands or gaps
- Confirmed risks and hypotheses
- Expected impact
- Verification idea for each recommendation

## Do not use

- Do not invent benchmark numbers or run expensive load tests without explicit authorization.
- Do not optimize code during audit mode.
- Do not install profilers, start services, or run external monitoring tools.
