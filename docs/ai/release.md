# Release Checklist

## Purpose
Use this checklist before publishing or handing off a Codex Enhancer package build. The release should stay as thin as the runtime: source files, package metadata, packaged scaffold assets, and deterministic validation.

## Required Checks
1. Confirm `ENHANCER_VERSION` in `scripts/enhancer_spec.py` is the intended public version.
2. Run `python scripts/check.py`.
3. Run `python -m unittest discover -s tests -p "test_*.py" -v`.
4. Run `python -m build` from a clean working tree or a deliberate release branch.
5. Install the built wheel into a fresh virtual environment.
6. Run `codex-enhancer list-packs` from that environment.
7. Preview an install with `codex-enhancer init <probe-repo> --new`.
8. Preview the full optional helper bundle with `codex-enhancer init <probe-repo> --new --with-spec-kit --utility-harness`.

## Package Boundary
- Package runtime dependencies must remain empty unless a future release truly needs source-repo runtime libraries.
- Spec Kit remains external; the package may plan an official bootstrap command but must not vendor Spec Kit.
- Utility Harness helper dependencies remain in target `requirements-codex.txt`, not in the package's production dependencies.
- Packaged assets under `codex_enhancer/assets/root/` must mirror source scaffold, repo-local skills, and README inputs used by installed CLI runs.

## Review Notes
- Treat changes to `pyproject.toml`, `MANIFEST.in`, `codex_enhancer/package_assets.py`, scaffold files, or CLI command routing as release-sensitive.
- If build artifacts are generated locally, keep `build/`, `dist/`, and `*.egg-info/` out of commits unless a release process explicitly asks for them.
- When a new CLI subcommand is added, document both the source-checkout invocation and the installed `codex-enhancer` invocation.
