# Codex Utility Harness

## Purpose
The Utility Harness is an optional integration that installs repo-local helper tools for Codex/operator inspection. It gives future Codex sessions repeatable local instruments for large repositories and mixed file formats without making Codex Enhancer a package manager or runtime.

## Contract
- The harness is off by default.
- It is installed only when an operator explicitly passes `--utility-harness-mode install`.
- The installer records state under `[integrations.utility_harness]` in `.codex/enhancer/manifest.toml`.
- Harness files are normal visible repo files and remain reviewable through git diffs.
- `requirements-codex.txt` and the `requirements-codex-*.txt` group files are for Codex/operator helper dependencies only.
- The installer never installs those dependencies automatically.
- The dependency files are split by purpose so operators can install only core helpers, richer readers, code-analysis extras, or CLI/config helpers as needed.

## Installed Surface
- `requirements-codex.txt`
- `requirements-codex-minimal.txt`
- `requirements-codex-readers.txt`
- `requirements-codex-analysis.txt`
- `requirements-codex-cli.txt`
- `tools/ai/inspect_repo.py`
- `tools/ai/read_any.py`
- `tools/ai/summarize_tree.py`
- `tools/ai/run_checks.py`
- `docs/ai/utility-harness.md`

## Ownership
- Enhancer-owned at install time: the scaffolded harness files and manifest state.
- Repo-owned after adaptation: any local tuning to commands, ignore behavior, or helper script output.
- Safe generated outputs remain limited to `docs/ai/stack-guidance.md`, `docs/ai/spec-kit-bridge.md`, and `.codex/enhancer/manifest.toml`.
- Upgrade should propose harness file drift rather than silently overwriting local edits.

## Audit Use
During a repository improvement audit, harness output can support findings only when it is tied back to inspected repo files and explicit commands. Use `tools/ai/run_checks.py --list` before running anything so prose-extracted commands remain visible and inert by default.

Do not install helper dependencies, run `--include-prose`, use `--allow-shell`, or run expensive analysis helpers during audit mode unless the user explicitly authorizes that action. Missing optional helper packages should be recorded as an audit limitation, not silently worked around.

## Non-Goals
- no automatic dependency installation
- no production dependency pollution
- no OCR
- no background indexer
- no daemon, agent runtime, or orchestration layer
- no guessed validation commands

## Review Rule
If the harness changes, reviewers should verify that helper dependencies stay isolated, scripts remain deterministic and bounded, and `run_checks.py` lists prose-extracted commands without running them by default.
