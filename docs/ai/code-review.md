# Review And PR Prep

Use this checklist when a change in this repository touches [AGENTS.md](../../AGENTS.md), [docs/ai/](../ai/), [.codex/skills/](../../.codex/skills/), or [scripts/](../../scripts/).

## Before Review
1. Run `python scripts/check.py`.
2. Run `python -m unittest discover -s tests -p "test_*.py" -v`.
3. Re-read changed docs and confirm every path, command, and link is real.
4. Confirm each new file solves a distinct problem not already covered elsewhere.
5. If a skill changed, verify the trigger is narrow and the `## Do not use` section is still accurate.
6. If a script changed, verify it is deterministic and dependency-light.
7. If repo commands changed, confirm [.github/workflows/validate.yml](../../.github/workflows/validate.yml) changed with them.
8. If installer, scaffold, or stack-pack behavior changed, confirm the end-to-end installer tests still pass.
9. If stack-pack generation or management changed, verify target `AGENTS.md`, `docs/ai/stack-guidance.md`, and `.codex/enhancer/manifest.toml` stay aligned with the selected packs.
10. If output ownership rules changed, verify previews and the target manifest still distinguish safe-to-regenerate outputs from scaffold files that should usually be adapted manually.
11. If the GUI installer changed, verify the overwrite preview, pack-selection controls, confirmation gate, progress updates, and README handoff still match the installer core.
12. If roadmap or stack-pack design changed, confirm the phased roadmap in [roadmap.md](./roadmap.md) still matches the intended architecture.

## Review Priorities
1. Wrong or stale instructions
2. Unnecessary new layers or files
3. Skills that are too broad or too generic
4. Scripts that assume a stack the repo does not have
5. Installer/scaffold drift
6. Missing validation notes or unstated risks

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
- If a change adds future-facing guidance, say what event should trigger the next update.
- If a change affects the installer, call out proposal-mode behavior, overwrite semantics, selected-pack defaults, generated target outputs, and any GUI-only behavior.
- If stack-pack selection changed, call out both the managed root `AGENTS.md` summary and the deeper `docs/ai/stack-guidance.md` update.
- If output ownership changed, call out which files are now considered safe to regenerate versus usually adapted manually.
- Prefer one coherent patch over speculative scaffolding.
