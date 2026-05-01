# V3 Migration Notes

## Purpose
Use this note when upgrading an existing target repo from a pre-3.0 Codex Enhancer install, or when reviewing a 3.0 lifecycle change in this source repo.

V3 keeps the same thin, repo-local model. The major change is safer lifecycle management for installed repos: selected stack packs, generated guidance, and upgrade state are now visible in the target manifest and managed sections instead of relying on full-file replacement.

## What Changed
- Current installs write `.codex/enhancer/manifest.toml` with manifest schema `3`.
- The manifest records lifecycle state, pack-selection mode, managed section ids, managed output ownership, selected packs, per-pack evidence, and resolved Spec Kit bridge state under `[integrations.spec_kit]`.
- Target `AGENTS.md` now wraps both the selected-stack-pack summary and the Spec Kit bridge summary in visible managed-section comments.
- `--manage-packs` updates the selected-stack-pack managed section plus `docs/ai/stack-guidance.md`, `docs/ai/spec-kit-bridge.md`, and `.codex/enhancer/manifest.toml`.
- `--refresh-generated` rebuilds only generated outputs from the installed manifest selection and bridge state.
- `--upgrade-enhancer` preserves selected packs, preserves installed bridge state unless overridden, refreshes safe generated outputs, updates valid managed sections in place, and writes repo-owned scaffold drift as proposals.
- Proposal files under `.codex/enhancer-proposals/` are collision-safe; existing review work is preserved with numbered filenames.
- Version inspection treats trailing zero segments as equivalent, so `3.0` and `3.0.0` compare as the same installed version.

## Upgrade An Existing Repo
1. Run `python scripts/install_enhancer.py --target <repo> --inspect-install`.
2. If the target is older, run `python scripts/install_enhancer.py --target <repo> --upgrade-enhancer`.
3. Review the grouped reconcile plan before writing anything.
4. Apply with `python scripts/install_enhancer.py --target <repo> --upgrade-enhancer --write`.
5. Review `.codex/enhancer-proposals/` and manually merge any repo-owned scaffold changes you want.
6. Run `python scripts/check.py` in the target repo.
7. Run `python -m unittest discover -s tests -p "test_*.py" -v` in the target repo.

## Change Packs After Upgrade
Use `--manage-packs` after the target reports as current:

```powershell
python scripts/install_enhancer.py --target <repo> --manage-packs --add-pack frontend-ui --write
```

Use `--set-pack` when you want the exact selected pack set. Use `--remove-pack` when removing one pack while keeping the rest.

## Change Spec Kit Bridge State
Use `--upgrade-enhancer` with explicit bridge flags when an installed repo needs to attach to or bootstrap official Spec Kit without doing a full fresh scaffold install:

```powershell
python scripts/install_enhancer.py --target <repo> --upgrade-enhancer --spec-kit-mode attach --write
```

Supported bridge flags:
- `--spec-kit-mode off|auto|attach|bootstrap`
- `--spec-kit-script auto|ps|sh`
- `--spec-kit-command-surface auto|dollar|slash`
- `--spec-kit-version <ref>`
- `--spec-kit-exe <path>`

## Review Checklist
- Confirm `.codex/enhancer/manifest.toml` uses schema `3` and records `lifecycle.state = "active"`.
- Confirm `selected_packs` agrees with the `selected = true` flags in `[[detected_packs]]`.
- Confirm every selected pack has a compact summary inside the managed `AGENTS.md:selected-stack-packs` section.
- Confirm `docs/ai/stack-guidance.md` contains deeper guidance for every selected pack.
- Confirm `.codex/enhancer/manifest.toml` records `[integrations.spec_kit]` and that the bridge mode matches the repo's actual intent.
- Confirm the managed `AGENTS.md:spec-kit-bridge` section and `docs/ai/spec-kit-bridge.md` agree on bridge mode, command surface, and ownership.
- Confirm generated outputs are treated as safe to regenerate, while repo-owned scaffold drift is reviewed from proposal files.
- Confirm existing proposal files were not overwritten during upgrade or install planning.

## Do Not Do
- Do not reinstall over an existing repo just to upgrade it; use `--upgrade-enhancer`.
- Do not hand-edit managed-section markers unless the same patch updates the manifest and validation expectations.
- Do not change selected packs during upgrade; use `--manage-packs` as a separate, reviewable step.
- Do not let the enhancer rewrite `.specify/`, `specs/`, or other official Spec Kit-owned files during upgrade.
- Do not add a migration database, background updater, or hidden state to track installed repos.
