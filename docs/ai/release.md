# Release Checklist

## Purpose
Use this checklist before publishing or handing off a Codex Enhancer package build. The release should stay as thin as the runtime: source files, package metadata, packaged scaffold assets, and deterministic validation.

## Supported Environment Policy
- Package metadata requires Python `>=3.13`.
- CI must prove Python 3.13 on Ubuntu, Windows, and macOS before a release is treated as cross-platform ready.
- Do not claim support for older Python versions, package-registry publication, or platform-specific installers until the matching build and smoke path exists.
- Source-checkout shims are convenience entrypoints. On POSIX systems, use `python codex-enhancer ...` if executable permissions were not preserved; on Windows, use `codex-enhancer.bat`.

## Required Checks
1. Confirm `ENHANCER_VERSION` in `scripts/enhancer_spec.py` is the intended public version.
2. Run `python scripts/check.py`.
3. Run `python -m unittest discover -s tests -p "test_*.py" -v`.
4. Run `python -m build` from a clean working tree or a deliberate release branch.
5. Install the built wheel into a fresh virtual environment.
6. Run `codex-enhancer list-packs` from that environment.
7. Preview an install with `codex-enhancer init <probe-repo> --new`.
8. Preview the full optional helper bundle with `codex-enhancer init <probe-repo> --new --with-spec-kit --utility-harness`.
9. Confirm CI or a local clean-room run performs the same wheel smoke path on each supported OS: build artifacts, install the wheel into a fresh virtual environment, run `codex-enhancer list-packs`, preview a basic install, and preview the optional helper bundle without `--write`.
10. Confirm the packaged optional helper assets include `requirements-codex.txt`, `requirements-codex-minimal.txt`, `requirements-codex-readers.txt`, `requirements-codex-analysis.txt`, and `requirements-codex-cli.txt`.

## Validation Boundary
- `python scripts/check.py` validates local files, managed markers, local markdown links, and skill metadata.
- It does not verify external URLs, external tool behavior, package-registry publication, or claims from unofficial documentation.
- If a release depends on an external URL or external fact, record the check date, source, and result in the release notes or PR summary. If it was not checked, mark it as unverified.

## Workflow Evaluation Checklist
Use this checklist when testing the enhancer against a real or representative Codex workflow. Record the result in the release notes, PR summary, or a follow-up issue.

- Target shape: repo type, installed packs, and whether the pack evidence matched maintained code rather than examples or generated files.
- First-run outcome: first command used, whether the preview was understandable, and any command a user had to discover manually.
- Codex workflow value: prompts or reminders avoided, validation commands clarified, safer handoff steps added, or hallucinated assumptions prevented.
- Safety outcome: dirty-worktree/source-target guards, proposal files, external bootstrap previews, and adaptation audit findings that changed user behavior.
- Friction: confusing terms, missing docs, false-positive pack recommendations, failed commands, slow checks, or recovery steps that still required maintainer knowledge.
- Evidence: commit or branch tested, date, OS/Python version, and the exact commands run.

## Package Boundary
- Package runtime dependencies must remain empty unless a future release truly needs source-repo runtime libraries.
- Spec Kit remains external; the package may plan an official bootstrap command but must not vendor Spec Kit.
- Utility Harness helper dependencies remain in target `requirements-codex.txt`, not in the package's production dependencies.
- Packaged assets under `codex_enhancer/assets/root/` must mirror source scaffold, repo-local skills, and README inputs used by installed CLI runs.

## Review Notes
- Treat changes to `pyproject.toml`, `MANIFEST.in`, `codex_enhancer/package_assets.py`, scaffold files, or CLI command routing as release-sensitive.
- If build artifacts are generated locally, keep `build/`, `dist/`, and `*.egg-info/` out of commits unless a release process explicitly asks for them.
- When a new CLI subcommand is added, document both the source-checkout invocation and the installed `codex-enhancer` invocation.
- Keep `.github/workflows/validate.yml` aligned with the release smoke path so package regressions are caught before a manual release pass.
