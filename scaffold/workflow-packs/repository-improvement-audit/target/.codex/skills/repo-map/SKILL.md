---
name: repo-map
description: Map repository architecture during a full repo audit. Use when the audit needs purpose, top-level directories, entry points, commands, integrations, ownership boundaries, and unclear areas before judging quality.
---

# Repository Map

Run as a no-implementation specialist sub-pass inside `full-repo-improvement-audit`.

1. Read root guidance, README files, docs, package/config files, scripts, tests, and CI before drawing conclusions.
2. Identify the repo purpose, major directories, generated folders, entry points, command surfaces, dependency manifests, integrations, and deployment cues.
3. Map ownership boundaries between product code, tests, docs, workflow assets, generated outputs, and external tool surfaces.
4. Record unclear or conflicting areas as hypotheses with the evidence needed to confirm them.
5. Report only evidence-backed findings and return control to `full-repo-improvement-audit`.

Output contract:
- System map
- Entry points and command evidence
- Component or ownership boundaries
- Integration and dependency surfaces
- Unclear areas and confirmation needs

## Do not use

- Do not use for implementation planning after an audit item has already been chosen.
- Do not invent architecture from framework conventions or directory names alone.
- Do not edit files, stage changes, install packages, or run generated commands.
