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
8. If package metadata or release expectations changed, confirm [pyproject.toml](../../pyproject.toml), [MANIFEST.in](../../MANIFEST.in), [docs/ai/release.md](./release.md), packaged assets, the `codex-enhancer` console script, README install guidance, and packaging tests agree.
9. If installer, scaffold, or stack-pack behavior changed, confirm the end-to-end installer tests still pass.
10. If stack-pack generation or management changed, verify target `AGENTS.md`, `docs/ai/stack-guidance.md`, and `.codex/enhancer/manifest.toml` stay aligned with the selected packs.
11. If output ownership rules changed, verify previews and the target manifest still distinguish safe-to-regenerate outputs from scaffold files that should usually be adapted manually.
12. If the command facade changed, verify it still delegates to [scripts/install_enhancer.py](../../scripts/install_enhancer.py) and has focused translation tests.
13. If installer output changed, verify full previews, `--summary`, `--diff`, `--json`, and adaptation audits are all covered by tests or documented as intentionally out of scope.
14. If the GUI installer changed, verify the overwrite preview, pack-selection controls, confirmation gate, progress updates, and README handoff still match the installer core.
15. If lifecycle, upgrade, refresh, managed-section, or proposal behavior changed, confirm [docs/ai/migration-v3.md](./migration-v3.md) explains the operator-facing impact.
16. If the Spec Kit bridge changed, verify [docs/ai/spec-kit-bridge.md](./spec-kit-bridge.md), the target scaffold bridge doc, bridge skills, manifest section ids, CLI bridge/report commands, and visible `AGENTS.md` markers changed together.
17. If the Utility Harness changed, verify [docs/ai/utility-harness.md](./utility-harness.md), target scaffold tools, `requirements-codex.txt`, CLI/GUI preview wording, manifest state, and validator expectations changed together.
18. If roadmap or stack-pack design changed, confirm the phased roadmap in [roadmap.md](./roadmap.md) still matches the intended architecture.

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
- If output ownership changed, call out which files are now considered safe to regenerate versus usually adapted manually, especially `docs/ai/spec-kit-bridge.md` and `.codex/enhancer/manifest.toml`.
- If migration behavior changed, call out the exact inspect, upgrade, manage-packs, refresh, and validation commands reviewers should use.
- If the Spec Kit bridge changed, call out what the enhancer owns versus what remains official Spec Kit state.
- If the Utility Harness changed, call out that dependencies remain Codex/operator-only and no automatic install path was added.
- If packaging changed, call out the wheel/sdist smoke path from [docs/ai/release.md](./release.md).
- Prefer one coherent patch over speculative scaffolding.
