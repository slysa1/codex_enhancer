---
name: repo-dx-audit
description: Audit developer experience during a full repo audit. Use when the audit needs evidence about onboarding, command discoverability, docs, CI feedback, generated artifacts, local helper scripts, and repo-local AI guidance.
---

# Repository Developer Experience Audit

Run as a no-implementation specialist sub-pass inside `full-repo-improvement-audit`.

1. Inspect onboarding docs, setup instructions, command lists, CI feedback paths, helper scripts, generated outputs, release notes, and AI guidance.
2. Check whether documented commands match real scripts, manifests, workflows, and validation files.
3. Look for stale guidance, missing recovery hints, unclear ownership, noisy generated files, and gaps that slow a new contributor.
4. Separate confirmed friction from taste preferences and hypotheses.
5. Report only evidence-backed findings and return control to `full-repo-improvement-audit`.

Output contract:
- Onboarding and command map
- Documentation and workflow friction
- Generated-output ownership risks
- AI guidance clarity issues
- Suggested DX improvements and acceptance checks

## Do not use

- Do not rewrite docs, scripts, or generated files during audit mode.
- Do not treat personal workflow preferences as findings without repo evidence.
- Do not add new helper tools or commands from this sub-pass.
