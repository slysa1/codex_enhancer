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
