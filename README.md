# Codex Enhancer

Codex Enhancer is a thin, repo-native workflow layer for Codex. It gives Codex a durable operating map, a small set of narrow reusable skills, deterministic validation, and a review loop without turning your repository into an AI framework project.

This repository currently ships the enhancer itself. There is no application package to install with `pip` or `npm`. Installing the enhancer means either:
- using this repository directly as the workflow layer product, or
- using the included installer to scaffold the enhancer into another repository and then adapting it to that repo's real commands and architecture

## What The Enhancer Gives You
- A concise root [AGENTS.md](AGENTS.md) that acts as the main Codex operating layer
- Durable supporting guidance in [docs/ai/](docs/ai/)
- Narrow repo-local skills in [.codex/skills/](.codex/skills/)
- A Windows launcher in [install_enhancer.bat](install_enhancer.bat)
- A bootstrap installer in [scripts/install_enhancer.py](scripts/install_enhancer.py)
- A GUI installer in [scripts/install_enhancer_gui.py](scripts/install_enhancer_gui.py)
- A stack-pack registry in [scaffold/stack-packs/](scaffold/stack-packs/)
- A stack-pack loader in [scripts/stack_packs.py](scripts/stack_packs.py)
- A shared install/validation spec in [scripts/enhancer_spec.py](scripts/enhancer_spec.py)
- A reusable validation engine in [scripts/enhancer_validator.py](scripts/enhancer_validator.py)
- A zero-dependency source-repo validator in [scripts/check.py](scripts/check.py)
- An install scaffold under [scaffold/target-repo/](scaffold/target-repo/)
- A small regression suite in [tests/](tests/)
- GitHub Actions validation in [.github/workflows/validate.yml](.github/workflows/validate.yml)

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
- Python 3.13 recommended
- Codex or another environment that understands repo-local `AGENTS.md` and skills

The current implementation has no third-party Python dependencies.

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
- review detected stack packs and adjust the selected set before install
- manage stack packs later without reinstalling the scaffold
- review stack packs from the existing target manifest during upgrade and refresh
- review which files will be created, proposed, or overwritten, with critical conflicts called out separately
- confirm overwrite actions before install
- watch installation progress
- see a completion summary that lists the installed stack packs
- open the product README automatically after completion

If you prefer the CLI or want to script installs, use the commands below.
CLI dry-runs now preview the same pack-aware "after install" guidance that the GUI shows before you rerun with `--write`. Detected pack lines include the exact evidence the installer used, such as matched files, package-manager fields, lockfiles, relevant scripts, dependencies, and Python tool tables.

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

Preview an upgrade/reconcile plan for an existing enhancer install:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --upgrade-enhancer
```

Apply that upgrade/reconcile plan:

```bash
python scripts/install_enhancer.py --target ../my-existing-repo --upgrade-enhancer --write
```

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

What gets installed:

```text
AGENTS.md
.codex/skills/
.codex/enhancer/manifest.toml
docs/ai/
docs/ai/stack-guidance.md
scripts/check.py
scripts/enhancer_spec.py
scripts/enhancer_validator.py
tests/test_check.py
.github/workflows/validate.yml
.gitignore (merged, not overwritten)
```

Selected stack packs are rendered twice on install:
- a compact summary in the target root `AGENTS.md`
- deeper detail in `docs/ai/stack-guidance.md`

Installed output ownership is also explicit:
- safe to regenerate later: `docs/ai/stack-guidance.md` and `.codex/enhancer/manifest.toml`
- usually adapted manually after install: the rest of the scaffolded workflow files, including `AGENTS.md`, docs, scripts, skills, tests, and CI

Current installs write manifest schema `2`. The manifest records the enhancer version, selected packs, lifecycle state, pack-selection mode, managed-output ownership, and per-pack evidence. Evidence is intentionally human-readable and tied to visible files rather than hidden heuristics. Schema `1` manifests remain readable for inspect and upgrade, but current target validation expects schema `2` after reconcile. Version inspection normalizes trailing zero segments, so `3.0` and `3.0.0` compare as the same enhancer version.

The target `AGENTS.md` selected-stack-pack summary is wrapped in visible managed-section comments. Keep those markers intact; they let pack management update that one enhancer-owned region without rewriting repo-owned guidance outside the markers.

Use `--manage-packs` when you want to change selected packs after the enhancer is installed. It will:
- read the current selected packs from `.codex/enhancer/manifest.toml`
- apply `--add-pack`, `--remove-pack`, or an exact `--set-pack` replacement
- update only the managed selected-stack-pack section in `AGENTS.md`
- overwrite `docs/ai/stack-guidance.md` and `.codex/enhancer/manifest.toml`
- leave skills, docs, scripts, tests, CI, `.gitignore`, and unmarked `AGENTS.md` content alone

Use `--refresh-generated` when you want to rebuild only the safe outputs above. It will:
- read the current selected packs from the target repo's existing `.codex/enhancer/manifest.toml`
- overwrite `docs/ai/stack-guidance.md` and `.codex/enhancer/manifest.toml`
- leave `AGENTS.md`, skills, docs, scripts, tests, CI, and `.gitignore` alone

Use `--inspect-install` when you want to compare the current source repo to an already-installed target before planning an upgrade or reconcile. It reports:
- the source enhancer version and current manifest schema from this repo
- the target enhancer version and manifest schema recorded in `.codex/enhancer/manifest.toml`
- lifecycle state and pack-selection mode when the target manifest records them
- managed section ids that should match visible markers in scaffold files
- selected stack packs
- files marked safe to regenerate vs files usually adapted manually

Use `--upgrade-enhancer` when you want a reconcile preview for an existing install. It groups drift into:
- managed generated outputs that can be re-rendered from the current source
- source-aligned direct-copy files
- repo-owned scaffold files that should be reviewed as proposals

Re-run the same command with `--write` when the grouped reconcile plan looks correct. Upgrade apply will:
- overwrite managed generated outputs and source-aligned direct-copy files in place
- refresh the managed selected-stack-pack section in `AGENTS.md` in place when the markers are valid
- write repo-owned scaffold drift under `.codex/enhancer-proposals/` for manual review and merge
- preserve existing proposal files by choosing a unique proposal filename when a proposed path already exists
- preserve the installed pack selection from the target manifest
- leave pack selection changes to `--manage-packs` instead of silently changing them during upgrade

Use pack management instead when you need to:
- add or remove selected packs

Use a full install preview instead when you need to:
- bootstrap a repo that does not already have `.codex/enhancer/manifest.toml`
- choose force-based overwrite behavior for a fresh install instead of proposal-based reconcile output

After installation, adapt the repo in this order:
1. Review `AGENTS.md` and `docs/ai/stack-guidance.md` for any selected stack packs and confirm that guidance matches the target repo.
2. Update `AGENTS.md` with the target repo's purpose, layout, and real commands.
3. Use the `adapt-enhancer` skill to replace inherited generic guidance.
4. Remove or replace any docs that do not apply to the target repo.
5. Keep only the skills that solve repeated procedures in that repo.
6. Update `scripts/check.py` and `scripts/enhancer_spec.py` so the validation rules match the target repo.
7. Update `tests/test_check.py` so the fixture matches the target repo's expected enhancer shape.
8. Update `.github/workflows/validate.yml` so CI runs the same local commands.

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

### Canonical Commands
These are the maintained commands for this repository today:

```bash
python scripts/check.py
python scripts/check.py --verbose
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/install_enhancer.py --list-packs
python scripts/install_enhancer.py --target ../my-existing-repo --inspect-install
python scripts/install_enhancer.py --target ../my-existing-repo --manage-packs --add-pack python-service
python scripts/install_enhancer.py --target ../my-new-repo --mode new
install_enhancer.bat
```

What they do:
- `python scripts/check.py`: validates required files, markdown links, skill frontmatter, and command alignment
- `python scripts/check.py --verbose`: prints each successful check
- `python -m unittest discover -s tests -p "test_*.py" -v`: tests the validator itself
- `python scripts/install_enhancer.py --list-packs`: prints the available stack packs
- `python scripts/install_enhancer.py --target ... --manage-packs --add-pack <name>`: previews a pack-selection change for an installed target
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

For the current planned evolution of the enhancer, see [docs/ai/roadmap.md](docs/ai/roadmap.md). It defines the shipped `2.x` stack-pack model plus the phased `3.0` roadmap for managed sections, pack lifecycle, and stronger evidence-backed recommendations.

For upgrading existing installed repos, see [docs/ai/migration-v3.md](docs/ai/migration-v3.md). It gives the operator checklist for inspect, upgrade, pack management, refresh, proposal review, and validation.

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

### `tests/`
[tests/test_check.py](tests/test_check.py) gives you regression coverage for the source-repo validator.
[tests/test_install_enhancer.py](tests/test_install_enhancer.py) verifies dry-run behavior, actual installs, proposal mode, force overwrite on safe paths, and the installed target profile.
[tests/test_stack_packs.py](tests/test_stack_packs.py) covers the pack registry, detection heuristics, manifest evidence, selection rules, and generated pack-aware guidance.

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
4. Review `.codex/enhancer-proposals/` before manually merging repo-owned scaffold drift.
5. Run the target repo's enhancer validation commands after the upgrade.

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
|-- install_enhancer.bat
|-- .codex/skills/
|-- docs/ai/
|-- scripts/check.py
|-- scripts/install_enhancer.py
|-- scripts/install_enhancer_gui.py
|-- scripts/stack_packs.py
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
