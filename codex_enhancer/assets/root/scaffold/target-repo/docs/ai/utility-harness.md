# Codex Utility Harness

## Purpose
The Utility Harness is an optional Codex/operator toolbox for inspecting this repository. It is installed only when the enhancer installer is run with `--utility-harness-mode install`.

## Installed Files
- [requirements-codex.txt](../../requirements-codex.txt): optional helper dependencies for Codex/operator use only.
- [tools/ai/inspect_repo.py](../../tools/ai/inspect_repo.py): compact repository inspection report.
- [tools/ai/read_any.py](../../tools/ai/read_any.py): text extraction for common source, data, document, slide, spreadsheet, and PDF formats.
- [tools/ai/summarize_tree.py](../../tools/ai/summarize_tree.py): bounded project tree printer.
- [tools/ai/run_checks.py](../../tools/ai/run_checks.py): runner for validation commands already recorded in this repo.

## Dependency Rule
Do not add these packages to production dependency files unless the application itself genuinely needs them. `requirements-codex.txt` is for local Codex/operator helper environments, not runtime, test, or deploy environments.

Install helper dependencies manually only when needed:

```bash
python -m pip install -r requirements-codex.txt
```

## Common Commands
```bash
python tools/ai/inspect_repo.py
python tools/ai/summarize_tree.py --max-depth 3 --max-entries 250
python tools/ai/read_any.py <path>
python tools/ai/run_checks.py --list
python tools/ai/run_checks.py --dry-run
```

## Operating Rules
- Prefer these tools for repeatable inspection before falling back to ad hoc shell commands.
- Keep output bounded so it can be pasted into Codex context safely.
- Treat `.gitignore` and common junk directories as first-class ignore signals.
- Use `run_checks.py` only for commands already recorded in repo guidance, manifests, package scripts, or the enhancer validation spec.
- Do not add OCR, background indexing, daemon behavior, or automatic dependency installation.
