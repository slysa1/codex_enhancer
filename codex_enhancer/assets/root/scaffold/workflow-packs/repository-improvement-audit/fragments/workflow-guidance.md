Use this workflow pack when the user wants Codex to inspect an existing repository and produce an improvement roadmap before implementation.

The audit should:
- read repo guidance, docs, package files, CI, tests, scripts, and existing agent instructions first
- map architecture, entry points, validation commands, dependencies, integration points, and unclear areas
- review code quality, tests, reliability, security-sensitive flows, performance-sensitive paths, and developer experience
- separate confirmed findings from hypotheses
- use the finding schema in `docs/ai/repo-audit-finding-schema.md`
- prioritize work with the rubric in `docs/ai/repo-audit-roadmap-rubric.md`
- write suggested changes to root `roadmap.md` when the user wants a durable roadmap
- preserve existing `roadmap.md` content outside the managed audit section, and update only that section when the marker pair already exists
- stop before staging changes, installing packages, editing code/config/tests, or beginning implementation

Do not infer build, lint, test, coverage, architecture, dependencies, deployment, or security posture from common stack conventions alone.

Managed roadmap markers:

```text
<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit start -->
<!-- codex-enhancer:managed-section roadmap.md:repository-improvement-audit end -->
```
