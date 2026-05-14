# Repository Audit Roadmap Rubric

## Purpose
Use this rubric to turn full-repository audit findings into a prioritized roadmap. The roadmap should help maintainers choose the next change without pretending every finding belongs in one implementation pass.

## Prioritization Factors
- `Impact`: prefer work that protects correctness, user trust, security, release safety, or frequent developer workflows.
- `Confidence`: prioritize high-confidence findings before speculative work unless the speculative item blocks understanding the system.
- `Effort`: prefer smaller fixes when impact and confidence are comparable.
- `Risk Reduction`: value work that reduces blast radius, improves validation, removes unsafe defaults, or clarifies ownership.
- `Dependency Order`: sequence prerequisites before dependent refactors, broad rewrites, or tool changes.

## Roadmap Buckets

### Quick Wins
Small, high-confidence improvements with low effort and low coordination cost. These should usually have clear acceptance tests and little architectural risk.

### Phase 1 Stabilization
Work that improves correctness, safety, validation, onboarding, or operational trust before larger refactors. Include test hardening and documentation fixes when they unblock future work.

### Phase 2 Maintainability/Test Hardening
Medium-sized improvements that reduce technical debt, simplify ownership boundaries, improve regression coverage, or make future changes easier to review.

### Phase 3 Larger Architecture Work
Broad changes that require sequencing, design review, migration steps, or coordination across components. Include these only when the audit evidence shows that smaller work is not enough.

### Optional/Nice-To-Have
Low-severity, low-confidence, cosmetic, or opportunistic work. Keep these visible but separate from work that protects correctness or delivery.

## Roadmap Rules
- Put each finding in one primary bucket.
- Explain why each Phase 3 item cannot be solved by a smaller earlier step.
- Do not schedule implementation during the audit.
- Keep hypotheses out of the committed roadmap unless the first roadmap item is an investigation.
- Include validation ideas for each bucket so future implementation work can prove progress.
