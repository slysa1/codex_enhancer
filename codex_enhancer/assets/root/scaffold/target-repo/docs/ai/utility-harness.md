# Codex Utility Harness

## Purpose
The Utility Harness is an optional Codex/operator toolbox for inspecting this repository. It is installed only when the enhancer installer is run with `--utility-harness-mode install`.

## Installed Files
- [requirements-codex.txt](../../requirements-codex.txt): all-in optional helper dependency bundle for Codex/operator use only.
- [requirements-codex-minimal.txt](../../requirements-codex-minimal.txt): minimal inspection helpers.
- [requirements-codex-readers.txt](../../requirements-codex-readers.txt): PDF, Office, spreadsheet, HTML, Markdown, YAML, and TOML reader helpers.
- [requirements-codex-analysis.txt](../../requirements-codex-analysis.txt): optional code-analysis helpers.
- [requirements-codex-cli.txt](../../requirements-codex-cli.txt): optional richer CLI/config helpers.
- [tools/ai/audit_inputs.py](../../tools/ai/audit_inputs.py): no-execution inventory of audit evidence inputs, roadmap targets, and recorded validation commands.
- [tools/ai/inspect_repo.py](../../tools/ai/inspect_repo.py): compact repository inspection report.
- [tools/ai/read_any.py](../../tools/ai/read_any.py): text extraction for common source, data, document, slide, spreadsheet, and PDF formats.
- [tools/ai/summarize_tree.py](../../tools/ai/summarize_tree.py): bounded project tree printer.
- [tools/ai/run_checks.py](../../tools/ai/run_checks.py): runner for validation commands already recorded in this repo.

## Dependency Rule
Do not add these packages to production dependency files unless the application itself genuinely needs them. `requirements-codex.txt` is for local Codex/operator helper environments, not runtime, test, or deploy environments.

The dependency files are grouped by purpose:
- `requirements-codex-minimal.txt` for core inspection helpers
- `requirements-codex-readers.txt` for richer readers used by `tools/ai/read_any.py`
- `requirements-codex-analysis.txt` for optional code-analysis helpers
- `requirements-codex-cli.txt` for optional richer CLI/config helpers
- `requirements-codex.txt` as the all-in helper environment

Install helper dependencies manually only when needed. For a full local helper environment:

```bash
python -m pip install -r requirements-codex.txt
```

For a narrower environment:

```bash
python -m pip install -r requirements-codex-minimal.txt
python -m pip install -r requirements-codex-readers.txt
python -m pip install -r requirements-codex-analysis.txt
python -m pip install -r requirements-codex-cli.txt
```

## Common Commands
```bash
python tools/ai/inspect_repo.py
python tools/ai/audit_inputs.py
python tools/ai/summarize_tree.py --max-depth 3 --max-entries 250
python tools/ai/read_any.py <path>
python tools/ai/run_checks.py --list
python tools/ai/run_checks.py --dry-run
```

## Operating Rules
- Prefer these tools for repeatable inspection before falling back to ad hoc shell commands.
- Keep output bounded so it can be pasted into Codex context safely.
- Treat `.gitignore` and common junk directories as first-class ignore signals.
- Use `run_checks.py --list` first. By default, prose-extracted commands are listed but not run; use `--include-prose` only after reviewing them.
- Use `run_checks.py --allow-shell` only after reviewing commands that contain shell control operators.
- Do not add OCR, background indexing, daemon behavior, or automatic dependency installation.

## Audit Use
During a repository improvement audit, treat helper output as supporting evidence only. Use `tools/ai/audit_inputs.py` to find candidate evidence files and the roadmap target before writing recommendations. Tie any tool-backed claim to inspected repo files, the exact command, exit status when available, and a concise output summary.

Do not install helper dependencies, run prose-extracted commands, enable shell-control execution, or run expensive analysis helpers during audit mode unless the user explicitly authorizes that action. Missing optional helper packages should lower confidence or become a limitation, not block the audit.
