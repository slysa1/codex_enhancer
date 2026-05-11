# Review And PR Prep

Use this checklist when a change in this repository touches [AGENTS.md](../../AGENTS.md), [docs/ai/](../ai/), [.codex/skills/](../../.codex/skills/), or [scripts/](../../scripts/).

## Before Review
1. Run `python scripts/check.py`.
2. Run `python -m unittest discover -s tests -p "test_*.py" -v`.
3. Re-read changed docs and confirm every path, command, and link is real.
4. Confirm each workflow file solves a distinct problem not already covered elsewhere.
5. If a skill changed, verify the trigger is narrow and the `## Do not use` section is still accurate.
6. If a script changed, verify it is deterministic and dependency-light.
7. If repo commands changed, confirm [.github/workflows/validate.yml](../../.github/workflows/validate.yml) changed with them.
8. If stack packs are selected, confirm [AGENTS.md](../../AGENTS.md), [docs/ai/stack-guidance.md](./stack-guidance.md), and [.codex/enhancer/manifest.toml](../../.codex/enhancer/manifest.toml) still match.
9. Confirm installer-managed outputs are still treated as such: `docs/ai/stack-guidance.md`, `docs/ai/spec-kit-bridge.md`, and `.codex/enhancer/manifest.toml` can be regenerated together, while the rest of the scaffold should usually be reviewed as manual repo-owned edits.
10. Confirm the manifest schema, lifecycle metadata, and pack evidence still look intentional before merging enhancer lifecycle changes.
11. Confirm visible managed-section markers in `AGENTS.md` still wrap only the selected stack-pack summary.
12. If official Spec Kit is present or bridge guidance changed, confirm [docs/ai/spec-kit-bridge.md](./spec-kit-bridge.md), the managed Spec Kit bridge summary in [AGENTS.md](../../AGENTS.md), and the ownership boundary for `.specify/` or `specs/` still match.
13. If the Utility Harness is installed, confirm `requirements-codex.txt` stays Codex/operator-only and `tools/ai/run_checks.py` runs only recorded validation commands.

## Review Priorities
1. Wrong or stale instructions
2. Unnecessary workflow layers or files
3. Skills that are too broad or too generic
4. Scripts that assume a stack the repo does not have
5. Missing validation notes or unstated risks

## Good Review Output
- Findings first when performing an actual review
- What changed
- Why it belongs in the repo
- Validation performed
- Deliberately omitted additions
- Follow-up only if the repo later grows into needing it

## PR Support Notes
- Local validation and CI should run the same commands.
- Keep summaries high signal; avoid changelog-style file inventories unless reviewers need them.
- If this repo still contains inherited enhancer guidance, call out what still needs adaptation.
- If stack-pack selection changed, call out both the managed root `AGENTS.md` summary and the deeper `docs/ai/stack-guidance.md` update.
- If installer-managed ownership changed, call out which outputs remain safe to regenerate and which files still expect manual adaptation.
- If the repo also uses official Spec Kit, call out what the enhancer owns versus what remains official Spec Kit state.
- If Utility Harness files changed, call out whether the change affects helper tooling only or real repo validation behavior.
