# Codex Enhancer

Codex Enhancer is a thin, repo-native workflow layer for Codex. It gives Codex a durable operating map, a small set of narrow reusable skills, deterministic validation, and a review loop without turning your repository into an AI framework project.

This repository currently ships the enhancer itself. Installing the enhancer means either:
- using this repository directly as the workflow layer product,
- installing this checkout in editable mode to expose the `codex-enhancer` command locally,
- installing a built wheel or source distribution that includes the scaffold assets, or
- using the included installer to scaffold the enhancer into another repository and then adapting it to that repo's real commands and architecture

Current distribution status: this README documents source-checkout use, editable installs, and locally built wheel or source-distribution artifacts. It does not claim a published package-registry release. If you were not handed a wheel, start from the source-checkout path.

## Start Here
Use Codex Enhancer when you want a visible repo-local operating layer for Codex: concise instructions, narrow repeatable skills, deterministic checks, and review guidance that live in git. Do not use it when a single hand-written `AGENTS.md` is enough or when you want a hidden agent runtime.

### Five-Minute Path
Choose one command lane first:

| Starting point | First read-only command | Then |
| --- | --- | --- |
| Fresh clone, no install yet | `python scripts/codex_enhancer_cli.py doctor .` | Run `python scripts/check.py`, then preview a target repo with `python scripts/codex_enhancer_cli.py init ../target-repo --existing --summary --diff`. |
| Editable local CLI | `python -m pip install -e . --no-deps` | Run `codex-enhancer doctor .`, then `codex-enhancer init ../target-repo --existing --summary --diff`. |
| Built artifact handed to you | `python -m pip install <wheel-or-sdist>` | Run `codex-enhancer list-packs`, then preview a target repo before using `--write`. |
| Windows GUI | `install_enhancer.bat` | Pick a target folder, review the planned creates/proposals/overwrites, then apply only after the preview makes sense. |

First successful target-repo workflow:
1. Orient: run `doctor` on the enhancer checkout and on the target repo so you know whether each path is a source checkout, installed target, or plain repo.
2. Preview: run `init ../target-repo --existing --summary --diff`. Preview is the default; `--dry-run` is accepted when you want to say that explicitly.
3. Inspect detail only when needed: add `--diff-full` for untruncated large diffs or remove `--summary` for the full human preview.
4. Apply only after review: rerun with `--write`. If the target repo already has local git changes or looks like the enhancer source checkout, apply is blocked before any files are touched unless you explicitly pass the relevant override.
5. Adapt: run `audit ../target-repo` and replace inherited generic guidance with the target repo's real commands, layout, and validation rules.
6. Validate in the target repo with the commands shown in its generated `AGENTS.md` and `docs/ai/`.

Concrete before/after workflow:
- Before: a small existing repo has a `README.md` and real test command, but no `AGENTS.md`, no durable Codex review rules, and no checked-in validation habit. Each Codex session needs repeated instructions such as "inspect first", "use this test command", and "summarize risks".
- Preview: from this checkout, `python scripts/codex_enhancer_cli.py init ../small-repo --existing --summary --diff` shows the operation mode, selected or skipped stack packs, Spec Kit and Utility Harness state, planned creates/proposals/overwrites, `.gitignore` additions, and next commands without writing files.
- Apply and adapt: after `--write`, the target repo contains a repo-local `AGENTS.md`, durable `docs/ai/` guidance, validation scaffolding, optional skills, a visible `.codex/enhancer/manifest.toml`, and proposal files for conflicts instead of silent overwrites.
- Verify: `codex-enhancer audit ../small-repo` reports whether generic inherited guidance remains; the target repo validation then proves the workflow files, links, and commands stay coherent.

### Choose The Right Tool
| Situation | Best fit | Why |
| --- | --- | --- |
| One small repo only needs a few standing instructions. | Plain `AGENTS.md` | Less machinery, easier to maintain by hand. |
| You want repo-local Codex guidance, validation, install/upgrade previews, and optional stack guidance. | Codex Enhancer | Visible scaffold plus deterministic checks and proposal-mode safety. |
| You already use official Spec Kit for feature specs and tasks. | Spec Kit plus optional enhancer bridge | Spec Kit owns `.specify/` and `specs/`; the enhancer can add Codex operating guidance around it. |
| Your team already standardizes on Claude Code conventions. | Claude Code conventions, optionally mirrored in enhancer docs | Do not duplicate workflows unless Codex needs the same repo-local guidance. |
| You need a running agent service, background memory, or task orchestration. | Another tool | Codex Enhancer deliberately avoids hidden runtimes and persistent state. |

## What The Enhancer Gives You
- A concise root [AGENTS.md](AGENTS.md) that acts as the main Codex operating layer
- Distributable package metadata in [pyproject.toml](pyproject.toml) and [MANIFEST.in](MANIFEST.in)
- Package asset lookup in [codex_enhancer/package_assets.py](codex_enhancer/package_assets.py)
- Durable supporting guidance in [docs/ai/](docs/ai/)
- Narrow repo-local skills in [.codex/skills/](.codex/skills/)
- Friendly source-checkout command shims in [codex-enhancer](codex-enhancer) and [codex-enhancer.bat](codex-enhancer.bat)
- A Windows launcher in [install_enhancer.bat](install_enhancer.bat)
- A thin command facade in [scripts/codex_enhancer_cli.py](scripts/codex_enhancer_cli.py)
- A bootstrap installer in [scripts/install_enhancer.py](scripts/install_enhancer.py)
- A GUI installer in [scripts/install_enhancer_gui.py](scripts/install_enhancer_gui.py)
- A Spec Kit bridge resolver in [scripts/spec_kit_bridge.py](scripts/spec_kit_bridge.py)
- A Utility Harness resolver in [scripts/utility_harness.py](scripts/utility_harness.py)
- A stack-pack registry in [scaffold/stack-packs/](scaffold/stack-packs/)
- A stack-pack loader in [scripts/stack_packs.py](scripts/stack_packs.py)
- A shared install/validation spec in [scripts/enhancer_spec.py](scripts/enhancer_spec.py)
- A reusable validation engine in [scripts/enhancer_validator.py](scripts/enhancer_validator.py)
- A zero-dependency source-repo validator in [scripts/check.py](scripts/check.py)
- An install scaffold under [scaffold/target-repo/](scaffold/target-repo/)
- A small regression suite in [tests/](tests/)
- GitHub Actions validation in [.github/workflows/validate.yml](.github/workflows/validate.yml)
- An optional Codex Utility Harness for repo-local inspection, mixed-format reading, tree summaries, and recorded validation commands

## Who This Is For
Use Codex Enhancer if you want Codex to work better inside a real repository by default:
- less prompt repetition
- clearer repo conventions
- better plan -> implement -> validate -> review discipline
- more durable project guidance
- lower friction for repeated changes

Do not use it if you want a packaged agent runtime, hidden orchestration layer, or a large command ecosystem.

## Prerequisites
- Git
- Python 3.13 or newer
- Codex or another environment that understands repo-local `AGENTS.md` and skills

Support policy: package metadata requires Python `>=3.13`, and CI proves Python 3.13 on Ubuntu, Windows, and macOS. Do not claim older Python support until the CI matrix tests it.

The current source-repo implementation has no runtime third-party Python dependencies. The optional Utility Harness can scaffold a target-repo `requirements-codex.txt` for Codex/operator helper tooling, but the installer never installs those packages automatically.

Spec Kit bootstrap is the only normal path that expects an external executable. `--with-spec-kit` or `--spec-kit-mode bootstrap` uses `uvx` by default and pins the official bootstrap ref used by this enhancer release. Use `--spec-kit-exe <path>` when you already have a local `specify`-compatible executable or want to avoid `uvx`. Previews show the exact bootstrap command, executable status, pinned ref, network warning, and recovery hint before any `--write` apply.

## Installation

### Option 1: Use This Repository Directly
Clone the repository and run the built-in checks:

```bash
git clone https://github.com/slysa1/codex_enhancer.git
cd codex_enhancer
python scripts/check.py
python -m unittest discover -s tests -p "test_*.py" -v
```

After that, open the repo in Codex and start from [AGENTS.md](AGENTS.md).

To expose the friendly CLI command from this source checkout, use an editable install:

```bash
python -m pip install -e . --no-deps
codex-enhancer doctor .
codex-enhancer list-packs
codex-enhancer init ../my-new-repo --new --with-spec-kit --utility-harness
```

To build distributable artifacts from a prepared packaging environment:

```bash
python -m build
python -m pip install dist/codex_enhancer-4.0.0-py3-none-any.whl
codex-enhancer list-packs
```

The wheel and source distribution include package-owned copies of the scaffold and stack-pack assets so the installed `codex-enhancer` command can plan installs without a source checkout. Packaging still does not vendor Spec Kit, install Utility Harness helper packages, publish releases, or download target-repo dependencies automatically. See [docs/ai/release.md](docs/ai/release.md) before building or publishing release artifacts.

This source checkout may contain official Spec Kit files such as `.specify/`, `.github/prompts/`, and `.github/agents/` for developing the enhancer itself. Those files are not part of the enhancer scaffold copied into target repos; the package only plans or runs official Spec Kit bootstrap when you choose that option.

### Option 2: Install The Enhancer Into Another Repository
Use the installer to scaffold the enhancer into a new or existing repository.

If you want a Windows installer flow with a folder picker, overwrite preview, confirmation step, progress bar, and automatic README handoff, start here:

```bat
install_enhancer.bat
```

The launcher opens [scripts/install_enhancer_gui.py](scripts/install_enhancer_gui.py), which lets you:
- type a target repo path manually
- browse for a target folder
- choose between a full scaffold install, an upgrade/reconcile pass, and a managed-output refresh
- choose whether the Spec Kit bridge should stay off, attach to an existing official install, or bootstrap official Spec Kit for Codex
- review detected stack packs and adjust the selected set before install
- manage stack packs later without reinstalling the scaffold
- review stack packs from the existing target manifest during upgrade and refresh
- preview bridge mode, bridge command surface, and any official bootstrap command before apply
- choose whether to install the optional Codex Utility Harness helper files
- review which files will be created, proposed, or overwritten, with critical conflicts called out separately
- confirm overwrite actions before install
- watch installation progress
- see a completion summary that lists the installed stack packs
- open the product README automatically after completion

If you prefer the CLI or want to script installs, use the commands below.
CLI dry-runs now preview the same pack-aware "after install" guidance that the GUI shows before you rerun with `--write`. Detected pack lines include the exact evidence the installer used, such as matched files, package-manager fields, lockfiles, relevant scripts, dependencies, and Python tool tables.

For a shorter command surface from a source checkout, use [scripts/codex_enhancer_cli.py](scripts/codex_enhancer_cli.py), or put this checkout on `PATH` and run the [codex-enhancer](codex-enhancer) shim. On POSIX systems, run `python codex-enhancer ...` if your checkout did not preserve the shim's executable bit. On Windows, [codex-enhancer.bat](codex-enhancer.bat) exposes the same subcommands:

```bash
python scripts/codex_enhancer_cli.py list-packs
python scripts/codex_enhancer_cli.py doctor .
python scripts/codex_enhancer_cli.py init ../my-new-repo --new --with-spec-kit --utility-harness
python scripts/codex_enhancer_cli.py init ../my-existing-repo --existing --utility-harness
python scripts/codex_enhancer_cli.py init ../my-existing-repo --existing --summary --diff
python scripts/codex_enhancer_cli.py audit ../my-existing-repo
python scripts/codex_enhancer_cli.py init ../my-existing-repo --existing --utility-harness --write
python scripts/codex_enhancer_cli.py spec-report ../my-existing-repo --feature 001-login
python scripts/codex_enhancer_cli.py spec-sync ../my-existing-repo --feature 001-login --changed src/auth.py
python scripts/codex_enhancer_cli.py bridge ../my-existing-repo --attach-spec-kit
```

The facade only translates friendly verbs such as `doctor`, `init`, `install`, `inspect`, `audit`, `packs`, `refresh`, `upgrade`, `spec-report`, `spec-sync`, and `bridge` into the existing installer flags. It does not add a package manager or hidden installer; external setup only happens through an explicit installer bootstrap mode plus `--write`.

Use `--with-spec-kit` when you want Codex Enhancer to bootstrap official Spec Kit for Codex and install the bridge skills/guidance in the same flow. The preview shows the official bootstrap command first, including the executable check, pinned ref, network note, and recovery hint; the external Spec Kit download/setup only runs if you re-run with `--write`.

Useful preview formats:
- `doctor <repo>` or `--doctor --target <repo>` runs a read-only first-run diagnostic and prints the next useful commands for a source checkout, installed target, or plain repo.
- `--summary` prints the shortest install, upgrade, refresh, pack, or bridge plan, including exact external bootstrap commands when any are planned.
- `--dry-run` makes the default preview behavior explicit for scripts and cautious first runs.
- `--diff` adds a unified diff preview for planned text writes, proposals, managed-section refreshes, and `.gitignore` merges. Large per-file diffs are truncated by default; use `--diff-full` when you need the entire diff.
- `--json` emits a versioned machine-readable plan or report for wrappers and CI.
- `--write` checks the target repo's own git worktree first and blocks when `git status --short` already reports local changes or when clean state cannot be verified; use `--allow-dirty` only when applying over that state is deliberate.
- `--write` also blocks when the target looks like the Codex Enhancer source checkout; use `--allow-source-target` only when that unusual target is deliberate.
- If an apply fails while writing files, the error names the failed path, lists enhancer-owned paths likely touched in that run, and gives recovery steps.
- `audit <repo>` or `--audit-adaptation` checks an installed target for inherited generic guidance, placeholders, and unmerged proposal files, then reports an adaptation status and severity summary.

JSON output uses `schema_version: 1`. Plan objects include `kind`, `operation`, `target`, `mode`, `write`, `selected_packs`, `pack_selections`, `spec_kit_bridge`, `spec_kit_detection`, `utility_harness`, `writes`, `write_counts`, `conflicts`, `gitignore`, `diagnostics`, `external_steps`, and `next_steps`. Each `external_steps` item includes the exact command string, argv list, executable status/path when available, pinned ref, network flag, execution order, warnings, and recovery hint. Read-only report objects use operation-specific `kind` values such as `doctor-report`, `install-inspection`, `adaptation-audit`, `spec-kit-report`, `spec-kit-sync-report`, and `pack-catalog`; adaptation audits also include `status` and `severity_counts`. Error output is also JSON when `--json` is set, with `kind: "error"` and a `message`.

List the currently available stack packs:

```bash
python scripts/install_enhancer.py --list-packs
```

Current shipped packs:
- `monorepo-workspace`
- `javascript-typescript-app`
- `frontend-ui`
- `python-service`
- `node-api-service`
- `library-package`

Stack-pack detection now combines conservative file/path signals with narrow manifest evidence from `package.json`, `packageManager` or lockfiles, and `pyproject.toml`. The `library-package` pack is intentionally conservative: it requires explicit reusable-package metadata such as `exports`, `types`, `files`, or `bin`, and it backs away when obvious app or service entrypoints are present.

### Choosing Stack Packs

Stack packs are optional guidance bundles. They do not install dependencies or change application code. They add stack-specific Codex instructions to the installed `AGENTS.md` managed section and `docs/ai/stack-guidance.md` so Codex plans, edits, validates, and reviews work with the right repo assumptions.

Use recommended packs as a starting point, not a commandment. Enable a pack when it describes real maintained code in the target repo. Skip it when the detection evidence is incidental, generated, or only an example.

| Pack | Enable when | What it adds | Usually skip when |
| --- | --- | --- | --- |
| `monorepo-workspace` | The repo coordinates multiple apps or packages from one root with pnpm workspaces, Turborepo, Nx, Rush, or Lerna. | Workspace-aware planning, affected-package checks, and root-vs-package validation discipline. | The repo is a single app or package without shared workspace tooling. |
| `javascript-typescript-app` | `package.json` represents real JS/TS source, scripts, package-manager state, or toolchain config. | Package-manager and lockfile discipline plus build/lint/test/typecheck script guidance. | `package.json` exists only for docs, assets, examples, or incidental formatting helpers. |
| `frontend-ui` | The repo ships browser-facing routes, screens, components, or design-system UI. | UI review prompts for state, layout, accessibility, responsive behavior, and visual checks. | The repo is backend-only, CLI-only, or contains frontend files only as fixtures/examples. |
| `python-service` | The repo has Python application, service, package, or toolchain entrypoints backed by `pyproject.toml`, requirements, or setup metadata. | Python environment discovery and review prompts for config, entrypoints, fixtures, and regression tests. | Python is only present in enhancer scaffold files or one-off maintenance scripts. |
| `node-api-service` | The repo exposes Node.js or TypeScript API routes, controllers, server entrypoints, or OpenAPI contracts. | API review prompts for routing, auth, validation, status codes, error shapes, contracts, and integration tests. | The repo is frontend-only, or API-looking files are mocks, examples, or framework stubs. |
| `library-package` | The repo publishes a reusable package with explicit `exports`, `main`, `module`, `types`, `bin`, `files`, or similar package metadata. | Published-contract review guidance for entrypoints, types, metadata, package contents, compatibility, and release notes. | The repo is an app or service that merely uses `package.json` for tooling. |

Common combinations:
- Use `javascript-typescript-app` with `frontend-ui` for React, Vue, Svelte, Astro, Vite, or Next.js apps.
- Use `javascript-typescript-app` with `node-api-service` for Node or TypeScript backends.
- Use `monorepo-workspace` together with the surface packs that match the actual packages inside the workspace.
- Use `library-package` only when published package behavior matters to downstream consumers.

Preview a new-repo install:

```bash
python scripts/install_enhancer.py --target ../my-new-repo --mode new
```

Apply a new-repo install:

```bash
python scripts/install_enhancer.py --target ../my-new-repo --mode new --write
```

Preview an existing-repo install:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --mode existing
```

Apply an existing-repo install:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --mode existing --write
```

Preview an install while auto-selecting recommended detected packs:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --mode existing --use-recommended-packs
```

Preview an install with explicit pack overrides:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --mode existing --use-recommended-packs --no-pack javascript-typescript-app --pack python-service
```

Preview a stack-pack change for an already installed repo:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --manage-packs --add-pack python-service
```

Apply that stack-pack change:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --manage-packs --add-pack python-service --write
```

Replace the installed pack set exactly:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --manage-packs --set-pack javascript-typescript-app --set-pack frontend-ui
```

Preview a generated-output refresh for an already installed repo:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --refresh-generated
```

Apply that refresh:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --refresh-generated --write
```

Inspect an existing install before planning a later upgrade or reconcile:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --inspect-install
```

If you inspect this Codex Enhancer source checkout itself, it may report "not installed" because source repos and installed target repos are different shapes. The source repo is validated with `python scripts/check.py`; installed targets are identified by `.codex/enhancer/manifest.toml`.

Audit an installed target after apply:

```bash
python scripts/codex_enhancer_cli.py audit ../my-existing-repo
```

Preview an upgrade/reconcile plan for an existing enhancer install:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --upgrade-enhancer
```

Apply that upgrade/reconcile plan:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --upgrade-enhancer --write
```

### Codex Utility Harness

The Utility Harness is optional and separate from stack packs and Spec Kit. It installs visible helper files for Codex/operator use only:

```text
requirements-codex.txt
requirements-codex-minimal.txt
requirements-codex-readers.txt
requirements-codex-analysis.txt
requirements-codex-cli.txt
tools/ai/inspect_repo.py
tools/ai/read_any.py
tools/ai/summarize_tree.py
tools/ai/run_checks.py
docs/ai/utility-harness.md
```

Preview a target install with the harness:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --mode existing --utility-harness-mode install
```

Apply it after reviewing the plan:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --mode existing --utility-harness-mode install --write
```

The harness does not install dependencies, run in the background, index the repo, or add production dependencies. Install helper dependencies manually in a local helper environment and keep them out of runtime, test, and deployment dependency flows. Use `requirements-codex-minimal.txt`, `requirements-codex-readers.txt`, `requirements-codex-analysis.txt`, or `requirements-codex-cli.txt` when you only need one helper group; use `requirements-codex.txt` for the all-in bundle. The resolved state is recorded under `[integrations.utility_harness]` in `.codex/enhancer/manifest.toml`.

For an existing repo with conflicting files:
- by default, conflicting files are written as proposals under `.codex/enhancer-proposals/`
- previews distinguish critical enhancer-owned conflicts from standard ones
- use `--force` only when you explicitly want installer-managed files to overwrite existing ones

For stack-pack selection:
- `--list-packs` prints the currently shipped packs and exits
- `--use-recommended-packs` selects packs that were detected and marked as recommended
- `--pack <name>` explicitly selects a pack even if it was not auto-detected
- `--no-pack <name>` explicitly skips a pack, including a recommended one
- conflicting `--pack` and `--no-pack` selections for the same name are rejected
- `--manage-packs` changes selected packs in an already-installed repo without reinstalling the scaffold
- `--add-pack <name>` and `--remove-pack <name>` apply pack-selection deltas and require `--manage-packs`
- `--set-pack <name>` replaces the installed pack set exactly and cannot be combined with `--add-pack` or `--remove-pack`
- `--refresh-generated` re-renders only enhancer-managed outputs using the target repo's existing `.codex/enhancer/manifest.toml`
- `--refresh-generated` rejects `--force` and pack-selection flags so the refresh stays aligned with the installed manifest
- `--inspect-install` reports source-vs-target enhancer version, selected packs, and managed-output ownership without planning writes
- `--upgrade-enhancer` previews grouped reconcile drift for an existing install, and `--upgrade-enhancer --write` applies that reconcile plan

The CLI and GUI now share the same pack-selection core. The GUI starts with recommended detected packs selected and lets you adjust that set before install. In manage-packs mode, it reads the target repo's existing `.codex/enhancer/manifest.toml`, lets you toggle the selected set, and updates only the managed `AGENTS.md` stack-pack section plus generated pack outputs. In upgrade and refresh mode, the GUI shows the current selected packs as read-only context and keeps that manifest selection fixed while it previews the reconcile or refresh.

Pack interaction rules stay deliberately simple:
- `javascript-typescript-app` can compose with `frontend-ui`, `node-api-service`, or `library-package` when the target repo shows evidence for both.
- `frontend-ui` and `node-api-service` stay surface-specific and should only be selected together for repos that genuinely ship both UI and service code.
- `library-package` should be selected for reusable package contract guidance, not for normal apps that merely happen to have `package.json`.

### Spec Kit Bridge

The Spec Kit bridge is optional and separate from stack packs. It never vendors Spec Kit or rewrites official Spec Kit-owned files.

What the bridge does:
- detects official Spec Kit footprints like `.specify/`, `specs/`, `.github/prompts/`, `.github/agents/`, or `.agents/skills/speckit-*`
- records bridge state under `[integrations.spec_kit]` in `.codex/enhancer/manifest.toml`
- renders a managed Spec Kit summary in the target `AGENTS.md`
- regenerates `docs/ai/spec-kit-bridge.md` as a repo-local operating guide
- optionally installs the narrow bridge skills `spec-implement-bridge`, `spec-sync-check`, and `spec-review-bridge`
- prints read-only feature and sync reports that point Codex back to the relevant `specs/` artifacts

What the bridge does not do:
- it does not vendor Spec Kit into this repo
- it does not rewrite `.specify/`, `specs/`, or official Spec Kit prompts, agents, scripts, templates, or skills
- it does not replace official Spec Kit commands like `specify`, `plan`, or `tasks`

Bridge modes:
- `--spec-kit-mode off`: ignore Spec Kit and keep only passive guidance
- `--spec-kit-mode attach`: require an existing official Spec Kit install and add bridge guidance around it
- `--spec-kit-mode bootstrap`: run the official Codex bootstrap command first, then write enhancer-owned bridge guidance
- `--spec-kit-mode auto`: attach when official Spec Kit is already detected, otherwise stay off

Friendly CLI shortcuts:
- `--with-spec-kit`: same as `--spec-kit-mode bootstrap`, meant for installing Codex Enhancer and official Spec Kit together
- `--attach-spec-kit`: same as `--spec-kit-mode attach`, meant for repos that already have official Spec Kit
- `--no-spec-kit`: same as `--spec-kit-mode off`

Common bridge commands:

```bash
python scripts/codex_enhancer_cli.py init ../my-new-repo --new --with-spec-kit --utility-harness
python scripts/codex_enhancer_cli.py spec-report ../my-existing-repo
python scripts/codex_enhancer_cli.py spec-sync ../my-existing-repo --feature 001-login --changed src/auth.py --changed tests/test_auth.py
python scripts/codex_enhancer_cli.py bridge ../my-existing-repo --attach-spec-kit
python scripts/install_enhancer.py --target ../my-existing-repo --mode existing --spec-kit-mode attach
python scripts/install_enhancer.py --target ../my-existing-repo --spec-kit-sync-report --spec-kit-feature 001-login --spec-kit-changed-path src/auth.py
python scripts/install_enhancer.py --target ../my-new-repo --mode new --spec-kit-mode bootstrap
python scripts/install_enhancer.py --target ../my-existing-repo --upgrade-enhancer --spec-kit-mode attach
python scripts/install_enhancer.py --target ../my-existing-repo --manage-spec-kit-bridge --spec-kit-mode off
```

Use `spec-report` or `--spec-kit-report` to summarize existing `specs/` feature artifacts, core-file gaps, and task checkbox state without editing official Spec Kit files. Use `spec-sync` or `--spec-kit-sync-report` when you have changed paths and want a bounded report of which feature artifacts to re-read, open task state, contract/quickstart cues, and obvious validation gaps. Use `bridge` or `--manage-spec-kit-bridge` when an already-installed target needs bridge mode, script flavor, or command-surface guidance changed without running a full enhancer upgrade.

Bridge-specific flags:
- `--spec-kit-script auto|ps|sh` controls the script flavor used for attach or bootstrap guidance
- `--spec-kit-command-surface auto|dollar|slash` controls whether the bridge points users toward `$speckit-<command>` or `/prompts:speckit.<command>`
- `--spec-kit-version <ref>` pins the official Spec Kit ref for bootstrap
- `--spec-kit-exe <path>` uses a local `specify`-compatible executable instead of `uvx` for bootstrap
- `--spec-kit-changed-path <path>` adds a path to the read-only sync report and can be repeated
- `--spec-kit-base <ref>` asks local `git diff --name-only <ref>...HEAD` for changed paths in the sync report

Bootstrap notes:
- The default bootstrap ref is pinned by this enhancer release rather than silently following a moving branch.
- `--summary`, full previews, GUI previews, and JSON all expose the same command, executable availability, pinned ref, network requirement, and recovery hint.
- If `uvx` is missing during apply, install `uv`/`uvx` or pass `--spec-kit-exe <path>`.
- External Spec Kit bootstrap runs before enhancer-owned files are written. If it fails, inspect any official Spec Kit files it may have created, fix the bootstrap problem, and rerun the same enhancer command.

Use the bridge when:
- the repo already has an official Spec Kit install and you want the enhancer to help Codex use the resulting artifacts well
- you want the installer to bootstrap official Spec Kit for Codex before laying down enhancer guidance

Skip the bridge when:
- the repo does not use Spec Kit
- the repo has speculative or partial Spec Kit files that the team is not actually maintaining
- you want the enhancer to remain completely independent of Spec Kit in that target repo

What gets installed:

```text
AGENTS.md
.codex/skills/
.codex/enhancer/manifest.toml
docs/ai/
docs/ai/stack-guidance.md
docs/ai/spec-kit-bridge.md
scripts/check.py
scripts/enhancer_spec.py
scripts/spec_kit_bridge.py
scripts/utility_harness.py
scripts/enhancer_validator.py
tests/test_check.py
.github/workflows/validate.yml
.gitignore (merged, not overwritten)
```

Selected stack packs are rendered twice on install:
- a compact summary in the target root `AGENTS.md`
- deeper detail in `docs/ai/stack-guidance.md`

When the Spec Kit bridge is active, the target install also adds:
- a managed Spec Kit summary block inside `AGENTS.md`
- the generated bridge guide `docs/ai/spec-kit-bridge.md`
- the bridge skills `spec-implement-bridge`, `spec-sync-check`, and `spec-review-bridge`

When the Utility Harness is active, the target install also adds:
- `requirements-codex.txt`
- `tools/ai/inspect_repo.py`
- `tools/ai/read_any.py`
- `tools/ai/summarize_tree.py`
- `tools/ai/run_checks.py`
- `docs/ai/utility-harness.md`

Installed output ownership is also explicit:
- safe to regenerate later: `docs/ai/stack-guidance.md`, `docs/ai/spec-kit-bridge.md`, and `.codex/enhancer/manifest.toml`
- usually adapted manually after install: the rest of the scaffolded workflow files, including `AGENTS.md`, docs, scripts, skills, tests, and CI

Current installs write manifest schema `3`. The manifest records the enhancer version, selected packs, lifecycle state, pack-selection mode, managed-output ownership, per-pack evidence, resolved Spec Kit bridge state under `[integrations.spec_kit]`, and resolved Utility Harness state under `[integrations.utility_harness]`. Evidence is intentionally human-readable and tied to visible files rather than hidden heuristics. Older manifests remain readable for inspect and upgrade, but current target validation expects the current schema after reconcile. Version inspection normalizes trailing zero segments, so `3.0` and `3.0.0` compare as the same enhancer version.

The target `AGENTS.md` selected-stack-pack summary is wrapped in visible managed-section comments. Keep those markers intact; they let pack management update that one enhancer-owned region without rewriting repo-owned guidance outside the markers.

Use `--manage-packs` when you want to change selected packs after the enhancer is installed. It will:
- read the current selected packs from `.codex/enhancer/manifest.toml`
- apply `--add-pack`, `--remove-pack`, or an exact `--set-pack` replacement
- update only the managed selected-stack-pack section in `AGENTS.md`
- overwrite `docs/ai/stack-guidance.md`, `docs/ai/spec-kit-bridge.md`, and `.codex/enhancer/manifest.toml`
- leave skills, docs, scripts, tests, CI, `.gitignore`, and unmarked `AGENTS.md` content alone

Use `--refresh-generated` when you want to rebuild only the safe outputs above. It will:
- read the current selected packs from the target repo's existing `.codex/enhancer/manifest.toml`
- preserve the target repo's existing Spec Kit bridge state from the manifest
- overwrite `docs/ai/stack-guidance.md`, `docs/ai/spec-kit-bridge.md`, and `.codex/enhancer/manifest.toml`
- leave `AGENTS.md`, skills, docs, scripts, tests, CI, and `.gitignore` alone

Use `--inspect-install` when you want to compare the current source repo to an already-installed target before planning an upgrade or reconcile. It reports:
- the source enhancer version and current manifest schema from this repo
- the target enhancer version and manifest schema recorded in `.codex/enhancer/manifest.toml`
- lifecycle state and pack-selection mode when the target manifest records them
- managed section ids that should match visible markers in scaffold files
- selected stack packs
- the recorded Spec Kit bridge mode or state plus any currently detected official Spec Kit surface
- files marked safe to regenerate vs files usually adapted manually

Use `--upgrade-enhancer` when you want a reconcile preview for an existing install. It groups drift into:
- managed generated outputs that can be re-rendered from the current source
- source-aligned direct-copy files
- repo-owned scaffold files that should be reviewed as proposals

Re-run the same command with `--write` when the grouped reconcile plan looks correct. Upgrade apply will:
- overwrite managed generated outputs and source-aligned direct-copy files in place
- refresh the managed selected-stack-pack section and managed Spec Kit bridge section in `AGENTS.md` in place when the markers are valid
- write repo-owned scaffold drift under `.codex/enhancer-proposals/` for manual review and merge
- preserve existing proposal files by choosing a unique proposal filename when a proposed path already exists
- preserve the installed pack selection from the target manifest
- preserve the installed Spec Kit bridge state from the target manifest unless you explicitly pass new `--spec-kit-*` overrides
- preserve the installed Utility Harness state unless you explicitly pass `--utility-harness-mode install` or `--utility-harness-mode off`
- leave pack selection changes to `--manage-packs` instead of silently changing them during upgrade

Use pack management instead when you need to:
- add or remove selected packs

Use a full install preview instead when you need to:
- bootstrap a repo that does not already have `.codex/enhancer/manifest.toml`
- choose force-based overwrite behavior for a fresh install instead of proposal-based reconcile output

After installation, adapt the repo in this order:
1. Review `AGENTS.md`, `docs/ai/stack-guidance.md`, and `docs/ai/spec-kit-bridge.md` for any selected packs or bridge guidance and confirm that they match the target repo.
2. Update `AGENTS.md` with the target repo's purpose, layout, and real commands.
3. If the bridge is active, verify whether the installed bridge skills are genuinely useful in that repo.
4. If the Utility Harness is active, verify that `requirements-codex.txt` remains Codex/operator-only.
5. Use the `adapt-enhancer` skill to replace inherited generic guidance.
6. Remove or replace any docs that do not apply to the target repo.
7. Keep only the skills that solve repeated procedures in that repo.
8. Update `scripts/check.py` and `scripts/enhancer_spec.py` so the validation rules match the target repo.
9. Update `tests/test_check.py` so the fixture matches the target repo's expected enhancer shape.
10. Update `.github/workflows/validate.yml` so CI runs the same local commands.

Important: do not install this enhancer into another repo unchanged and call it done. The value comes from making it repo specific.

## Quick Start
1. Read [AGENTS.md](AGENTS.md).
2. Read [docs/ai/architecture.md](docs/ai/architecture.md) if you are extending the enhancer itself.
3. Run:

```bash
python scripts/check.py
python -m unittest discover -s tests -p "test_*.py" -v
```

4. Open the repository in Codex and follow the default workflow from `AGENTS.md`.
5. If you are evaluating the installer, dry-run it into a local target first.

## Day-To-Day Use In Codex

### Default Loop
1. Inspect the relevant files first.
2. Keep the plan proportional to the change.
3. Prefer editing an existing file over creating a new one.
4. Validate locally.
5. Prepare the patch for review.

The enhancer is intentionally biased toward a simple loop:

```text
inspect -> plan -> edit -> validate -> review -> ship
```

### When To Use The Included Skills

#### `plan-change`
Use [.codex/skills/plan-change/SKILL.md](.codex/skills/plan-change/SKILL.md) when:
- a change touches multiple workflow assets
- you need explicit tradeoffs or scope control
- you are deciding whether a new file or layer is justified

Do not use it for trivial copy edits or obvious one-file fixes.

#### `adapt-enhancer`
Use [.codex/skills/adapt-enhancer/SKILL.md](.codex/skills/adapt-enhancer/SKILL.md) when:
- you installed this enhancer into a different repository
- you need to replace inherited commands and docs with that repo's real workflow
- you want a narrow checklist for rewriting `AGENTS.md`, docs, skills, checks, tests, and CI in the right order

Do not use it when editing this enhancer repository itself.

#### `review-prep`
Use [.codex/skills/review-prep/SKILL.md](.codex/skills/review-prep/SKILL.md) when:
- a patch is ready for handoff
- you want a concise validation summary
- you need to call out omissions, risks, or future follow-up

Do not use it as a substitute for real testing once the repo contains product code.

#### Spec Kit bridge skills
If the target repo uses the Spec Kit bridge, the installer may also add:
- `spec-implement-bridge` for implementing work from existing `spec.md`, `plan.md`, and `tasks.md`
- `spec-sync-check` for checking code drift against Spec Kit artifacts
- `spec-review-bridge` for preparing review notes from Spec Kit-driven work

These are intentionally narrow. They do not replace official Spec Kit commands and should only be used after official Spec Kit artifacts already exist in the target repo.

### Canonical Commands
These are the maintained commands for this repository today:

```bash
python scripts/check.py
python scripts/check.py --verbose
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/install_enhancer.py --list-packs
python scripts/codex_enhancer_cli.py list-packs
python scripts/codex_enhancer_cli.py doctor .
python scripts/install_enhancer.py --target ../my-existing-repo --inspect-install
python scripts/codex_enhancer_cli.py inspect ../my-existing-repo
python scripts/codex_enhancer_cli.py audit ../my-existing-repo
python scripts/install_enhancer.py --target ../my-existing-repo --spec-kit-report
python scripts/codex_enhancer_cli.py spec-report ../my-existing-repo --feature 001-login
python scripts/install_enhancer.py --target ../my-existing-repo --spec-kit-sync-report --spec-kit-feature 001-login --spec-kit-changed-path src/auth.py
python scripts/codex_enhancer_cli.py spec-sync ../my-existing-repo --feature 001-login --changed src/auth.py
python scripts/install_enhancer.py --target ../my-existing-repo --manage-spec-kit-bridge --spec-kit-mode attach
python scripts/codex_enhancer_cli.py bridge ../my-existing-repo --attach-spec-kit
python scripts/install_enhancer.py --target ../my-existing-repo --manage-packs --add-pack python-service
python scripts/codex_enhancer_cli.py packs ../my-existing-repo --add python-service
python scripts/install_enhancer.py --target ../my-new-repo --mode new
python scripts/codex_enhancer_cli.py init ../my-new-repo --new
python scripts/codex_enhancer_cli.py init ../my-new-repo --new --summary --diff
python scripts/codex_enhancer_cli.py init ../my-new-repo --new --with-spec-kit --utility-harness
python scripts/install_enhancer.py --target ../my-existing-repo --mode existing --utility-harness-mode install
python scripts/codex_enhancer_cli.py init ../my-existing-repo --existing --utility-harness
install_enhancer.bat
```

What they do:
- `python scripts/check.py`: validates required files, markdown links, skill frontmatter, and command alignment
- `python scripts/check.py --verbose`: prints each successful check
- `python -m unittest discover -s tests -p "test_*.py" -v`: tests the validator itself
- `python scripts/codex_enhancer_cli.py ...`: provides short subcommands over the same installer core
- `python scripts/install_enhancer.py --list-packs`: prints the available stack packs
- `python scripts/codex_enhancer_cli.py doctor ...`: reports whether a path looks like the enhancer source checkout, an installed target, or a plain repo, then prints the next useful commands
- `python scripts/codex_enhancer_cli.py audit ...`: reports inherited generic guidance, placeholders, and unreviewed proposal files after install
- `--summary`, `--diff`, and `--json`: switch installer previews between concise human output, text diffs, and machine-readable plans
- `python scripts/install_enhancer.py --target ... --spec-kit-report`: prints a read-only Spec Kit feature-artifact report
- `python scripts/install_enhancer.py --target ... --spec-kit-sync-report`: prints a read-only changed-path sync report for existing Spec Kit artifacts
- `python scripts/install_enhancer.py --target ... --manage-spec-kit-bridge --spec-kit-mode <mode>`: previews a bridge-mode update for an installed target
- `python scripts/install_enhancer.py --target ... --manage-packs --add-pack <name>`: previews a pack-selection change for an installed target
- `python scripts/install_enhancer.py --target ... --utility-harness-mode install`: previews installing optional Codex/operator helper tools
- `python scripts/install_enhancer.py --target ...`: previews or applies a scaffold install into another repo
- `install_enhancer.bat`: opens the Windows GUI installer

## How The Enhancer Is Structured

### `AGENTS.md`
[AGENTS.md](AGENTS.md) is the main operating layer. It should stay concise and answer these questions quickly:
- what this repo is
- how to work in it by default
- what commands are canonical
- what "done" means

It is a map, not a dump of every durable rule.

### `docs/ai/`
[docs/ai/architecture.md](docs/ai/architecture.md), [docs/ai/code-review.md](docs/ai/code-review.md), and [docs/ai/migration-v3.md](docs/ai/migration-v3.md) hold the durable detail that would otherwise bloat `AGENTS.md`.

Use docs when guidance needs more explanation. Use `AGENTS.md` when guidance must be visible immediately.

For the current enhancer evolution record, see the status table at the top of [docs/ai/roadmap.md](docs/ai/roadmap.md). It separates historical `2.x`/`3.x` design notes, the completed `4.0` product-maturity baseline, and the active `4.1` audit-derived follow-up plan for first-run clarity, write safety, release confidence, and trust surfaces.

For upgrading existing installed repos, see [docs/ai/migration-v3.md](docs/ai/migration-v3.md). It gives the operator checklist for inspect, upgrade, pack management, refresh, proposal review, and validation.

For package build and release readiness, see [docs/ai/release.md](docs/ai/release.md). It keeps the wheel/sdist checks, packaged-asset boundary, and no-dependency policy in one place.

### `.codex/skills/`
[.codex/skills/](.codex/skills/) holds narrow, repeatable procedures. The subtree rules live in [.codex/skills/AGENTS.md](.codex/skills/AGENTS.md).

Skills in this repo are intentionally narrow. If a procedure is too broad, too generic, or needs lots of reference material, it probably belongs in `docs/ai/` instead.

### `scripts/install_enhancer.py`
[scripts/install_enhancer.py](scripts/install_enhancer.py) is the bootstrap entrypoint. It:
- scaffolds enhancer files into a target repo
- discovers a small set of likely commands from common manifests, respecting `packageManager` and common JavaScript lockfiles
- lists, detects, and resolves shipped stack packs during install planning with visible evidence
- supports recommended-pack selection plus explicit include/exclude overrides in the CLI
- manages selected packs after install with manifest deltas and managed-section updates
- renders a compact selected-pack summary into the target `AGENTS.md`
- merges `.gitignore` entries instead of overwriting the file
- generates target `docs/ai/stack-guidance.md` and `.codex/enhancer/manifest.toml`
- writes proposal files for conflicts in existing repos unless `--force` is used
- exposes structured install planning so the GUI and CLI share the same overwrite and progress behavior

### `scripts/codex_enhancer_cli.py`
[scripts/codex_enhancer_cli.py](scripts/codex_enhancer_cli.py) is a small command facade over the installer. It adds memorable verbs such as `init`, `inspect`, `packs`, `refresh`, `upgrade`, `spec-report`, `spec-sync`, and `bridge`, then delegates to [scripts/install_enhancer.py](scripts/install_enhancer.py) so planning, previews, writes, and validation stay in one place.

### `pyproject.toml`
[pyproject.toml](pyproject.toml) defines the distributable package metadata for the `codex-enhancer` console script. The package version is read from [scripts/enhancer_spec.py](scripts/enhancer_spec.py) so package metadata and installed enhancer manifests stay aligned. [MANIFEST.in](MANIFEST.in) and [codex_enhancer/package_assets.py](codex_enhancer/package_assets.py) keep scaffold assets available to installed wheels and source distributions.

### `scripts/install_enhancer_gui.py`
[scripts/install_enhancer_gui.py](scripts/install_enhancer_gui.py) is the Windows-first GUI layer over the installer core. It adds:
- manual path entry plus folder browsing
- detected stack-pack selection with recommended defaults for install mode
- editable manifest-based pack selection for manage-packs mode
- read-only manifest-based pack context for upgrade and refresh mode
- a readable preview for install, upgrade, and refresh operations
- an overwrite acknowledgement gate before destructive install actions
- a progress bar tied to real install steps
- a completion dialog that lists the installed stack packs
- automatic opening of the enhancer README when the install finishes

### `install_enhancer.bat`
[install_enhancer.bat](install_enhancer.bat) is the easiest Windows entrypoint. Double-click it or run it from `cmd`/PowerShell to launch the GUI installer without typing the Python command yourself.

### `codex-enhancer`
[codex-enhancer](codex-enhancer) and [codex-enhancer.bat](codex-enhancer.bat) are source-checkout shims for the friendly CLI facade. The POSIX shim has a Python shebang; use `python codex-enhancer ...` as the fallback when a copied checkout loses executable permissions. They are convenience entrypoints only; the installer core remains [scripts/install_enhancer.py](scripts/install_enhancer.py).

### `scripts/enhancer_spec.py`
[scripts/enhancer_spec.py](scripts/enhancer_spec.py) is the shared source of truth for:
- validation profiles
- canonical validation commands
- install asset lists
- `.gitignore` additions

### `scripts/enhancer_validator.py`
[scripts/enhancer_validator.py](scripts/enhancer_validator.py) is the reusable validation engine used by both the source repo and installed target repos.

### `scripts/check.py`
[scripts/check.py](scripts/check.py) keeps the enhancer honest. It currently checks:
- required workflow files exist
- markdown links resolve
- skill frontmatter is valid
- required skills exist
- core docs contain the expected canonical commands

### `scaffold/target-repo/`
[scaffold/target-repo/](scaffold/target-repo/) contains the target-repo versions of files that should not simply be copied from this product repo verbatim.

### `scaffold/stack-packs/`
[scaffold/stack-packs/](scaffold/stack-packs/) stores the file-based stack-pack registry. Each pack lives in its own directory with `pack.toml` plus small markdown fragments that the installer can detect and render into target guidance.

### `scripts/stack_packs.py`
[scripts/stack_packs.py](scripts/stack_packs.py) loads stack-pack metadata, detects matching packs in a target repo, collects narrow manifest evidence from `package.json`, package-manager signals, and `pyproject.toml`, resolves selection state, and renders the target `AGENTS.md` summary, manifest, and stack-guidance outputs.

### `scripts/utility_harness.py`
[scripts/utility_harness.py](scripts/utility_harness.py) resolves the optional Codex Utility Harness state and renders the target `AGENTS.md` summary for that integration.

### `tests/`
[tests/test_check.py](tests/test_check.py) gives you regression coverage for the source-repo validator.
[tests/test_install_enhancer.py](tests/test_install_enhancer.py) verifies dry-run behavior, actual installs, proposal mode, force overwrite on safe paths, and the installed target profile.
[tests/test_stack_packs.py](tests/test_stack_packs.py) covers the pack registry, detection heuristics, manifest evidence, selection rules, and generated pack-aware guidance.
[tests/test_utility_harness.py](tests/test_utility_harness.py) covers the Utility Harness mode resolver and summary text.

### GitHub Actions
[.github/workflows/validate.yml](.github/workflows/validate.yml) mirrors the same local commands. If local commands change, CI should change in the same patch.

## Customizing The Enhancer

### Add A New Skill
Only add a new skill when all of these are true:
- the procedure repeats often
- the procedure is narrow enough to trigger reliably
- the procedure is not already better expressed in `AGENTS.md` or `docs/ai/`

When adding a skill:
1. Read [.codex/skills/AGENTS.md](.codex/skills/AGENTS.md).
2. Keep the frontmatter to `name` and `description`.
3. Put concrete trigger language in `description`.
4. Include a `## Do not use` section.
5. Run the local validation commands.

### Change Repo Commands
If you change the canonical commands:
1. Update [AGENTS.md](AGENTS.md).
2. Update this [README.md](README.md).
3. Update [docs/ai/code-review.md](docs/ai/code-review.md) if the review loop changed.
4. Update [.github/workflows/validate.yml](.github/workflows/validate.yml).
5. Update [scripts/enhancer_spec.py](scripts/enhancer_spec.py) if the shared rule changed.
6. Update tests if the validator's expectations changed.

### Review Or Upgrade A V3 Install
When reviewing lifecycle behavior or upgrading an existing target repo:
1. Read [docs/ai/migration-v3.md](docs/ai/migration-v3.md).
2. Use `--inspect-install` before planning upgrade or reconcile work.
3. Keep pack changes separate from upgrade by using `--manage-packs`.
4. Keep Spec Kit bridge mode changes separate from upgrade by using `--manage-spec-kit-bridge`.
5. Review `.codex/enhancer-proposals/` before manually merging repo-owned scaffold drift.
6. Run the target repo's enhancer validation commands after the upgrade.

### Add More Structure Later
As the repo grows, the best next additions are usually:
- real install/build/lint/test commands in `AGENTS.md`
- stack-specific checks in CI
- nested `AGENTS.md` files only for subtrees with genuinely different rules
- new skills only after repeated usage proves they help

Do not add:
- generic slash-command systems
- hidden persistent state
- speculative packages or daemons
- MCP integrations without a real external dependency

## Typical Usage Examples

### Example: Start A Non-Trivial Change
1. Open the repo in Codex.
2. Read [AGENTS.md](AGENTS.md).
3. Use the `plan-change` skill if the change spans multiple files.
4. Implement the change.
5. Run the validation commands.
6. Use `review-prep` before handing the patch off.

### Example: Adapt The Enhancer To A New Repo
1. Run `python scripts/install_enhancer.py --target ../target-repo --mode existing --write`.
2. Use the `adapt-enhancer` skill to inspect the target repo before editing inherited assets.
3. Rewrite `AGENTS.md` to match the target repo.
4. Remove any guidance that is still generic.
5. Make the validator enforce the target repo's actual workflow layer.
6. Run tests and CI until the target repo's enhancer is self-consistent.

## Troubleshooting

### `python scripts/check.py` fails
Common causes:
- a required file was removed or renamed
- a markdown link points to the wrong path
- a skill is missing required frontmatter or `## Do not use`
- docs and CI commands drifted apart

Run:

```bash
python scripts/check.py --verbose
```

Then fix the reported path, content, or skill issue.
The validator now includes a short hint for common failure modes so the likely fix is visible in the output.

### The installer wrote proposal files
This happens when you install into an existing repo and the installer finds conflicts.

Look under:

```text
.codex/enhancer-proposals/
```

Then:
1. merge the proposal into the live file
2. remove inherited generic guidance
3. run the target repo validation commands

### Tests fail
Run:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

If a test fails after changing the enhancer shape, either:
- fix the implementation, or
- update the fixture expectations in [tests/test_check.py](tests/test_check.py) if the new behavior is intentional

### Local generated files make searches noisy
The repo ignores normal generated artifacts such as `__pycache__/`, `*.py[cod]`, `tests/_tmp/`, `build/`, `dist/`, and `*.egg-info/`. They may still exist in a local checkout after tests, package builds, or smoke runs.

When auditing the tree, prefer normal `rg --files` or explicitly exclude `tests/_tmp/` instead of searching ignored fixture output. Do not commit generated build artifacts unless a future release process explicitly asks for them.

### Codex ignores the intended workflow
Check:
- whether [AGENTS.md](AGENTS.md) still reflects the real repo
- whether the relevant procedure belongs in a skill instead of a large prompt
- whether the repo now needs nested `AGENTS.md` files for divergent subtrees

## Repository Shape
```text
.
|-- AGENTS.md
|-- README.md
|-- MANIFEST.in
|-- pyproject.toml
|-- codex_enhancer/
|-- codex-enhancer
|-- codex-enhancer.bat
|-- install_enhancer.bat
|-- .codex/skills/
|-- docs/ai/
|-- scripts/check.py
|-- scripts/codex_enhancer_cli.py
|-- scripts/install_enhancer.py
|-- scripts/install_enhancer_gui.py
|-- scripts/stack_packs.py
|-- scripts/utility_harness.py
|-- scripts/enhancer_spec.py
|-- scripts/enhancer_validator.py
|-- scaffold/target-repo/
|-- scaffold/stack-packs/
|-- tests/
`-- .github/workflows/validate.yml
```

## Contributing
Use [AGENTS.md](AGENTS.md) as the operational source of truth and [docs/ai/code-review.md](docs/ai/code-review.md) as the review checklist.

For any meaningful change:
1. keep the patch repo-specific
2. avoid new layers unless they clearly earn their keep
3. run the validator and tests
4. keep CI aligned with local commands

## License
This repository is distributed under the terms of the [LICENSE](LICENSE) file.
