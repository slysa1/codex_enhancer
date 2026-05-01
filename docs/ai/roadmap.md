# Codex Enhancer Roadmap

## Purpose
This roadmap records the phased enhancer design from the shipped `2.x` stack-pack work through the planned `3.0` managed-section and lifecycle model. The core idea remains optional stack packs: small, visible, repo-local overlays that add durable guidance for common app shapes while preserving the current thin enhancer model.

## V2 Goals
- Keep the root enhancer simple and readable.
- Add optional stack-aware guidance only when the repo shows real evidence for it.
- Reduce repeated adaptation work in common JavaScript, Python, and monorepo targets.
- Keep all installer decisions visible in source files, generated docs, and a repo-local manifest.
- Keep pack logic deterministic, testable, and removable.

## V2 Non-Goals
- No hidden persistent state.
- No auto-generated command zoo.
- No framework-specific packs for every ecosystem at launch.
- No package manager switching or guessed commands.
- No always-on pack enforcement for repos that did not select packs.

## Proposed File Layout

### Source Repo Layout
```text
.
|-- AGENTS.md
|-- README.md
|-- install_enhancer.bat
|-- docs/ai/
|   |-- architecture.md
|   |-- code-review.md
|   `-- roadmap.md
|-- scaffold/
|   |-- target-repo/
|   `-- stack-packs/
|       |-- monorepo-workspace/
|       |   |-- pack.toml
|       |   `-- fragments/
|       |       |-- agents-summary.md
|       |       |-- stack-guidance.md
|       |       `-- review-notes.md
|       |-- javascript-typescript-app/
|       |   |-- pack.toml
|       |   `-- fragments/
|       `-- python-service/
|           |-- pack.toml
|           `-- fragments/
|-- scripts/
|   |-- check.py
|   |-- enhancer_spec.py
|   |-- enhancer_validator.py
|   |-- install_enhancer.py
|   |-- install_enhancer_gui.py
|   `-- stack_packs.py
`-- tests/
    |-- test_check.py
    |-- test_install_enhancer.py
    `-- test_stack_packs.py
```

### Installed Target Repo Layout
```text
.
|-- AGENTS.md
|-- docs/ai/
|   |-- architecture.md
|   |-- code-review.md
|   `-- stack-guidance.md
|-- .codex/
|   |-- skills/
|   `-- enhancer/
|       `-- manifest.toml
|-- scripts/
|   |-- check.py
|   |-- enhancer_spec.py
|   `-- enhancer_validator.py
|-- tests/
|   `-- test_check.py
`-- .github/workflows/validate.yml
```

## Why These Files Exist
- `scaffold/stack-packs/`: visible source of truth for shipped stack packs.
- `scripts/stack_packs.py`: one small loader and renderer for pack metadata plus fragment resolution.
- `docs/ai/stack-guidance.md`: target-facing durable guidance generated from the selected packs.
- `.codex/enhancer/manifest.toml`: visible record of which packs were selected, why they were recommended, and which generated docs should be kept in sync.
- `tests/test_stack_packs.py`: regression coverage for pack loading, detection, and rendering.

## Pack Metadata Shape
Use `pack.toml` so the implementation stays dependency-free with Python's `tomllib`.

### Required Fields
- `schema_version`
- `name`
- `label`
- `description`
- `version`

### Discovery Fields
- `all_files`
- `any_files`
- `any_globs`
- `all_dirs`
- `exclude_files`

### UI Fields
- `recommended_if_detected`
- `default_selected`
- `order`

### Render Fields
- `agents_summary`
- `stack_guidance`
- `review_notes`

### Example `pack.toml`
```toml
schema_version = 1
name = "javascript-typescript-app"
label = "JavaScript / TypeScript app"
description = "Rules for repos with package.json plus JavaScript or TypeScript build/test tooling."
version = "0.1.0"

[discovery]
all_files = ["package.json"]
any_globs = ["tsconfig*.json", "eslint.config.*", "vite.config.*", "next.config.*"]
exclude_files = ["pom.xml"]

[ui]
recommended_if_detected = true
default_selected = false
order = 20

[render]
agents_summary = "fragments/agents-summary.md"
stack_guidance = "fragments/stack-guidance.md"
review_notes = "fragments/review-notes.md"
```

## Manifest Shape
The installed target repo should record the chosen packs in a visible manifest.

### Proposed `.codex/enhancer/manifest.toml`
```toml
schema_version = 3
enhancer_version = "3.1"
selected_packs = ["monorepo-workspace", "javascript-typescript-app"]

[lifecycle]
state = "active"
pack_selection = "manifest"
managed_sections = ["AGENTS.md:selected-stack-packs", "AGENTS.md:spec-kit-bridge"]

[[detected_packs]]
name = "monorepo-workspace"
selected = true
recommended = true
detected = true
reason = "Found pnpm-workspace.yaml"
evidence = ["Found pnpm-workspace.yaml"]

[[detected_packs]]
name = "python-service"
selected = false
recommended = false
detected = false
reason = "No pyproject.toml or requirements.txt found"
evidence = ["No pyproject.toml or requirements.txt found"]

[generated_files]
stack_guidance = "docs/ai/stack-guidance.md"

[managed_outputs]
safe_to_regenerate = ["docs/ai/stack-guidance.md", ".codex/enhancer/manifest.toml"]
adapt_manually = ["AGENTS.md"]
```

## Installer UX

### CLI UX
The CLI remains scriptable and should gain pack-aware flags:
- `--list-packs`
- `--use-recommended-packs`
- `--pack <name>` repeatable
- `--no-pack <name>` repeatable

Expected flow:
1. Detect likely packs from the target repo.
2. Print recommended packs with evidence.
3. Show which packs will be installed, skipped, or explicitly overridden.
4. Include pack-generated files in the dry-run preview.
5. Apply the same plan with `--write`.

### GUI UX
The Windows GUI should keep the current repo-picker and overwrite flow, then add a stack-pack selection panel.

Expected flow:
1. User chooses the target repo path by typing or browsing.
2. Installer detects likely packs and shows why each one was recommended.
3. GUI lists packs as checkboxes with concise descriptions.
4. Preview pane groups:
   - base enhancer files
   - generated stack guidance
   - overwrites
   - proposals
5. Overwrite confirmation remains required before installation.
6. Completion message lists the installed packs and opens the README.

## Exact First Three Packs

### 1. `monorepo-workspace`
Why first:
- useful across JavaScript, TypeScript, mixed-service, and tools repos
- changes developer behavior in a high-value way without assuming a framework

Detect when:
- `pnpm-workspace.yaml`
- `turbo.json`
- `nx.json`
- `rush.json`
- multiple package roots such as `apps/` plus `packages/`

Rules to ship:
- Resolve the correct workspace or package before running commands.
- Prefer package-scoped or affected checks before repo-wide checks.
- If shared config or contracts changed, expand validation scope deliberately.
- Do not move or rename workspace tooling unless the task explicitly requires it.

Do not use as:
- a reason to invent workspace commands that are not already defined in the repo

### 2. `javascript-typescript-app`
Why first:
- very common target shape
- gives immediate value around package manager discipline and type-aware validation

Detect when:
- `package.json`
- one or more of `tsconfig*.json`, `vite.config.*`, `next.config.*`, `eslint.config.*`

Rules to ship:
- Respect the repo's actual package manager and lockfile.
- Treat typechecking as first-class validation when the repo exposes it.
- Run the narrowest real lint/test/build commands first.
- Keep config changes aligned with the existing toolchain instead of swapping tools casually.

Do not use as:
- permission to assume React, Next.js, Vite, or Vitest unless the repo actually uses them

### 3. `python-service`
Why first:
- common service/tooling target
- pairs well with the current Python-based enhancer implementation

Detect when:
- `pyproject.toml`
- `requirements.txt`
- `setup.cfg`
- `src/` or service-style Python package layout

Rules to ship:
- Use commands discovered from real Python project files, not guessed defaults.
- Prefer the repo's existing env, test, lint, and type tools.
- When behavior changes, add or update the smallest meaningful regression test.
- Treat config and entrypoint changes as review-sensitive even when the code diff is small.

Do not use as:
- a reason to assume `pytest`, `ruff`, or `mypy` if the repo has not adopted them

## Proposed V2 Implementation Steps

### Step 1: Pack Registry And Manifest
Objective:
- add visible pack source files and a loader that can detect and render them

Files to change:
- `scaffold/stack-packs/`
- `scripts/stack_packs.py`
- `scripts/install_enhancer.py`
- `tests/test_stack_packs.py`

Files deliberately not added:
- no package downloader
- no dynamic plugin system

Validation:
- pack loader unit tests
- install dry-run includes detected packs

Main risk:
- metadata becomes too clever; keep the schema small and file-based

### Step 2: CLI Pack Selection
Objective:
- let users accept recommendations or override packs explicitly in the CLI

Files to change:
- `scripts/install_enhancer.py`
- `README.md`
- `tests/test_install_enhancer.py`

Files deliberately not added:
- no interactive terminal wizard

Validation:
- dry-run and write tests for `--use-recommended-packs`, `--pack`, and `--no-pack`

Main risk:
- conflicting flags confuse the output; keep resolution rules explicit

### Step 3: GUI Pack Selection
Objective:
- make pack choice visible and easy in the Windows installer

Files to change:
- `scripts/install_enhancer_gui.py`
- `tests/test_install_enhancer.py`

Files deliberately not added:
- no custom widget toolkit
- no persistent installer preferences

Validation:
- helper-level tests for pack preview and selection resolution

Main risk:
- UI drift from CLI behavior; share one plan builder

### Step 4: Render Target Guidance
Objective:
- write `docs/ai/stack-guidance.md` and `.codex/enhancer/manifest.toml` in target repos

Files to change:
- `scaffold/target-repo/`
- `scripts/install_enhancer.py`
- `scripts/enhancer_spec.py`
- `scripts/enhancer_validator.py`
- `tests/test_install_enhancer.py`
- `tests/test_check.py`

Files deliberately not added:
- no hidden cache
- no generated nested `AGENTS.md` files by default

Validation:
- installed target passes validation with and without selected packs

Main risk:
- generated docs become too verbose; keep AGENTS summary short and move detail into `stack-guidance.md`

### Step 5: Ship The First Three Packs
Objective:
- author and test the initial `monorepo-workspace`, `javascript-typescript-app`, and `python-service` packs

Files to change:
- `scaffold/stack-packs/monorepo-workspace/`
- `scaffold/stack-packs/javascript-typescript-app/`
- `scaffold/stack-packs/python-service/`
- tests and docs

Files deliberately not added:
- no frontend-ui or node-api-service pack in the initial v2 launch
- no database pack yet

Validation:
- detection tests for each pack
- render tests for each pack

Main risk:
- the first three packs overreach; keep each one conservative and command-agnostic

### Step 6: Pack-Aware Review And Validation
Objective:
- make the validator and review loop aware of selected packs without enforcing unused ones

Files to change:
- `scripts/enhancer_spec.py`
- `scripts/enhancer_validator.py`
- `docs/ai/code-review.md`
- tests

Files deliberately not added:
- no separate validation executable per pack

Validation:
- source repo still passes
- target repo validation changes based on selected manifest packs only

Main risk:
- accidental false positives in repos that intentionally skip packs

## Recommended V2 Success Bar
- A target repo can install the enhancer with zero packs, recommended packs, or explicit pack choices.
- Installed output stays readable to a human without hidden context.
- Pack rules improve guidance without forcing fake commands.
- Removing a pack remains a normal git diff, not a tooling migration.

## Proposed 2.2 Upgrade And Reconcile Existing Installs

### Goal
Make already-installed target repos easier to inspect, compare, and reconcile as Codex Enhancer evolves, without replacing normal git review or hiding state in a separate upgrader database.

### Scope
- inspect source-vs-target enhancer version and selected-pack state
- plan upgrades for enhancer-owned files in existing repos
- keep proposal-mode safety for repo-owned scaffold files
- support targeted refresh of managed outputs plus deliberate reconciliation of manual scaffold files

### Non-Goals
- no background updater
- no hidden migration history
- no automatic merging of user-authored `AGENTS.md` content
- no silent in-place overwrite of repo-owned workflow files

### 2.2 Step 1: Install State And Inspection
Objective:
- add a visible source-vs-target inspection layer so upgrade planning has a deterministic baseline

Files to change:
- `scripts/enhancer_spec.py`
- `scripts/stack_packs.py`
- `scripts/install_enhancer.py`
- validator and tests

Files deliberately not added:
- no upgrade apply mode yet
- no GUI upgrade flow yet

Validation:
- manifest render/load tests
- CLI inspection tests

Main risk:
- overfitting manifest rules before the upgrade flow is implemented

### 2.2 Step 2: CLI Upgrade Planning
Objective:
- add `--upgrade-enhancer` as a dry-run planner for existing installs

Files to change:
- `scripts/install_enhancer.py`
- `README.md`
- tests

Files deliberately not added:
- no one-shot auto-merge engine

Validation:
- dry-run tests for current, older, and partially missing installs

Main risk:
- upgrade plans become too noisy; keep them grouped by generated outputs, direct copies, and repo-owned proposals

### 2.2 Step 3: Apply Upgrade And Reconcile
Objective:
- apply upgrade plans with the same proposal and overwrite discipline used by install mode

Files to change:
- installer core
- manifest rendering
- tests

Files deliberately not added:
- no custom diff store

Validation:
- end-to-end upgrade tests from older fixture installs into current source state

Main risk:
- clobbering repo-specific scaffold edits instead of proposing them

### 2.2 Step 4: GUI Upgrade Parity
Objective:
- add upgrade inspection and apply flow to the Windows GUI

Files to change:
- `scripts/install_enhancer_gui.py`
- tests
- `README.md`

Files deliberately not added:
- no second GUI app

Validation:
- helper-level GUI preview tests for upgrade messaging and plan state

Main risk:
- GUI state drifts from CLI behavior; reuse one core planner

### 2.2 Success Bar
- a user can inspect an installed repo and see whether it is current, older, legacy, or ahead of source
- upgrade plans distinguish safe regenerated outputs from repo-owned scaffold proposals
- applying an upgrade remains reviewable in git
- old installs can move forward without reinstalling blindly

## Proposed 2.3 Evidence-Based Pack Expansion

### Goal
Expand the shipped stack-pack catalog without adding new installer machinery, hidden state, or content-parsing heuristics that would make recommendations harder to trust.

### Scope
- add two new optional packs that fit the current file-based detector
- keep the packs composable with the existing `javascript-typescript-app` and `monorepo-workspace` packs
- update pack tests, required-file validation, and docs in the same change

### Non-Goals
- no pack dependency graph
- no nested `AGENTS.md` generation
- no package-content parser for `package.json` or `pyproject.toml`
- no `library-package` pack yet

### Exact 2.3 Packs

#### `frontend-ui`
Why now:
- browser-facing UI repos are common enough to justify first-class guidance
- the guidance is useful across React, Next, Vue, Svelte, Astro, and similar layouts
- detection can stay conservative and visible through file paths alone

Detect when:
- UI-oriented source files such as `src/**/*.tsx`, `src/**/*.jsx`, `src/**/*.vue`, or `src/**/*.svelte` exist
- or common frontend entry/config files such as `vite.config.*`, `next.config.*`, `astro.config.*`, or `svelte.config.*` exist
- or common UI folders such as `app/**`, `pages/**`, or `components/**` contain browser-facing files

Rules to ship:
- verify loading, empty, error, and success states when the surface has them
- preserve accessibility basics such as labels, keyboard reachability, focus behavior, and semantic structure
- keep changes aligned with the existing design system or visual language
- avoid adding browser automation unless the repo already has it or the task explicitly calls for it

#### `node-api-service`
Why now:
- API/service repos are another common JavaScript/TypeScript target shape
- the guidance is high-signal and review-oriented without inventing commands
- it layers cleanly with the existing JS/TS pack

Detect when:
- `package.json` exists and service-oriented paths such as `src/server.*`, `src/routes/**`, `src/controllers/**`, `server/**`, `api/**`, or `openapi*.{json,yaml,yml}` exist
- or Node service indicators such as `nest-cli.json` exist

Rules to ship:
- treat request/response or schema changes as contract changes that need paired updates
- check auth, validation, and error behavior, not just happy paths
- call out backward-compatibility risk when routes, payloads, or error shapes change
- keep API docs, shared types, or fixtures aligned when the repo already has them

### Deferred Pack

#### `library-package`
Why defer:
- a good `library-package` recommendation likely needs stronger evidence than raw file paths
- with the current detector it would be too easy to misclassify normal apps as libraries
- it is a better fit for a later release if the pack system gains a narrow, reviewable way to inspect manifest metadata

### 2.3 Step 1: Roadmap And Scope Lock
Objective:
- record the exact 2.3 pack scope, shipped candidates, and deferred pack in durable docs

Files to change:
- `docs/ai/roadmap.md`

Files deliberately not added:
- no runtime changes yet

Validation:
- source docs stay aligned with the current architecture guidance

Main risk:
- roadmap drift between docs and implementation; keep the follow-on patch small and direct

### 2.3 Step 2: Add `frontend-ui`
Objective:
- ship the `frontend-ui` pack with conservative detection, summary guidance, stack guidance, and review notes

Files to change:
- `scaffold/stack-packs/frontend-ui/`
- source validation spec
- pack tests and installer-facing tests as needed

Files deliberately not added:
- no UI-specific script wrappers

Validation:
- pack detection tests
- stack-guidance and agents-summary render tests

Main risk:
- false positives in repos that happen to contain a small UI surface; keep detection signals visible and path-based

### 2.3 Step 3: Add `node-api-service`
Objective:
- ship the `node-api-service` pack with service-focused guidance and review notes

Files to change:
- `scaffold/stack-packs/node-api-service/`
- source validation spec
- pack tests and installer-facing tests as needed

Files deliberately not added:
- no OpenAPI parser
- no contract test harness

Validation:
- pack detection tests
- manifest/render tests for selected API-service packs

Main risk:
- over-detecting frontend repos that happen to include an `api/` folder; prefer stronger service-oriented paths

### 2.3 Step 4: Align Docs And Validation
Objective:
- keep the source validator, README, and test fixtures aligned with the expanded shipped pack set

Files to change:
- `README.md`
- `scripts/enhancer_spec.py`
- `tests/test_check.py`
- `tests/test_install_enhancer.py`
- `tests/test_stack_packs.py`

Files deliberately not added:
- no separate validator for each pack

Validation:
- `python scripts/check.py --verbose`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- forgetting to update the source required-file inventory or fixture repo shape when new packs are added

### 2.3 Success Bar
- the shipped pack catalog grows without changing installer architecture
- a JS/TS repo can compose `javascript-typescript-app` with `frontend-ui` or `node-api-service`
- selected-pack summaries remain short in `AGENTS.md`
- deeper guidance remains in `docs/ai/stack-guidance.md`
- deferred packs stay explicitly out of scope until the detector can justify them

## Proposed 3.0 Managed Sections, Pack Lifecycle, And Stronger Evidence

### Goal
Make Codex Enhancer feel mature in long-lived target repos by supporting safe pack changes after install, section-aware refresh and upgrade behavior, and stronger evidence-backed recommendations without adding hidden state or framework machinery.

### Scope
- carry the `2.3` shipped packs (`frontend-ui` and `node-api-service`) forward as first-class pack-management and validation targets
- evolve the target manifest so it can explain managed sections, pack evidence, and compatibility state
- add visible managed sections to scaffolded files so the enhancer can refresh owned regions without taking over entire files
- add a deliberate pack-management flow for adding and removing packs after install
- strengthen pack detection with narrow, reviewable manifest evidence
- ship `library-package` only after the stronger evidence layer exists
- make refresh, upgrade, validation, and docs understand the fuller lifecycle

### Non-Goals
- no packaged updater or background service
- no hidden migration database
- no generic plugin marketplace
- no broad config parser that invents commands from arbitrary manifest content
- no large pack explosion beyond what the stronger evidence layer can justify

### 3.0 Step 1: Compatibility And Manifest Evolution
Objective:
- lock the `3.0` compatibility story and extend the target manifest with visible lifecycle metadata for managed sections, evidence, and pack state

Files to change:
- `scripts/enhancer_spec.py`
- `scripts/stack_packs.py`
- `scripts/enhancer_validator.py`
- target manifest rendering tests
- roadmap and operator docs as needed

Files deliberately not added:
- no hidden cache
- no separate migration database

Validation:
- manifest render/load tests for `2.x` and `3.0` states
- validator tests for older, current, and malformed manifests

Main risk:
- making the manifest too opaque or too noisy; keep new fields human-readable and directly tied to visible repo files

Implemented baseline:
- source installs now render enhancer version `3.0` with manifest schema `2`
- schema `1` manifests remain readable for inspect and upgrade flows
- current validation requires schema `2`, lifecycle metadata, and visible pack evidence in generated manifests

### 3.0 Step 2: Managed Sections In Target Scaffold
Objective:
- add visible managed-section markers to selected scaffold files so pack summaries and other enhancer-owned regions can be refreshed without replacing the whole file

Files to change:
- `scaffold/target-repo/AGENTS.md`
- any target scaffold docs that need managed regions
- `scripts/install_enhancer.py`
- `scripts/enhancer_validator.py`
- target-side tests
- installer tests

Files deliberately not added:
- no separate template engine
- no hidden patch format

Validation:
- install and refresh tests that preserve user-owned content outside managed markers
- validator tests for missing, duplicated, or corrupted managed markers

Main risk:
- damaging hand-edited repo guidance or making managed markers so noisy that people stop trusting the files

Implemented baseline:
- target `AGENTS.md` now wraps the selected stack-pack summary in one visible managed-section marker pair
- generated manifests record `AGENTS.md:selected-stack-packs` under `lifecycle.managed_sections`
- target validation catches missing, duplicated, or reversed managed-section markers

### 3.0 Step 3: Pack Management Flow
Objective:
- add a first-class way to add and remove selected packs after install, with dry-run previews and the same review discipline as install and upgrade

Files to change:
- `scripts/install_enhancer.py`
- `scripts/install_enhancer_gui.py`
- `scripts/stack_packs.py`
- `README.md`
- installer tests

Files deliberately not added:
- no separate pack-manager app
- no interactive terminal wizard

Validation:
- CLI tests for add-pack, remove-pack, and replace-pack flows
- GUI helper tests for pack-management preview, confirmation, and completion messaging

Main risk:
- pack changes drift from the target manifest or generated guidance; one shared planner should own both preview and apply behavior

Implemented baseline:
- `--manage-packs` previews and applies selected-pack changes for already-installed target repos
- `--add-pack`, `--remove-pack`, and exact `--set-pack` replacement flows share one manifest-based resolver
- pack management updates the visible managed `AGENTS.md:selected-stack-packs` section plus `docs/ai/stack-guidance.md` and `.codex/enhancer/manifest.toml`
- the GUI exposes a Manage stack packs mode that toggles manifest-based pack selection without reinstalling the scaffold

### 3.0 Step 4: Stronger Evidence Layer
Objective:
- add a narrow, transparent evidence model that can inspect common manifest files and explain why a pack was recommended without guessing repo commands

Files to change:
- `scripts/stack_packs.py`
- `scripts/install_enhancer.py`
- pack metadata as needed
- pack tests
- installer tests

Files deliberately not added:
- no AST parser
- no framework-specific inference engine

Validation:
- evidence tests for `package.json`, `pyproject.toml`, and other supported manifests
- command-discovery tests for npm, pnpm, yarn, and bun evidence from lockfiles or `packageManager`
- preview tests that surface the exact evidence shown to users

Main risk:
- hidden heuristics create false confidence; every recommendation should map to visible, reviewable evidence text
- package-manager evidence drifts from generated commands; command discovery should respect the target repo's lockfile or `packageManager` field instead of defaulting JavaScript repos to npm

Implemented baseline:
- stack-pack detection now enriches existing file/path reasons with readable `package.json`, package-manager, and `pyproject.toml` evidence
- generated manifests and CLI/GUI previews surface the same evidence strings used by the detector
- command discovery now respects `packageManager` plus npm, pnpm, yarn, and bun lockfiles before falling back to npm
- the evidence layer remains deliberately narrow; no AST parser, pack metadata schema expansion, or framework-specific inference engine was added

### 3.0 Step 5: Ship `library-package` And Pack Interaction Rules
Objective:
- add the deferred `library-package` pack once the stronger evidence layer can justify it, and document the normal interaction patterns between existing and new overlapping packs

Files to change:
- `scaffold/stack-packs/library-package/`
- `scripts/stack_packs.py`
- `scripts/enhancer_spec.py`
- `README.md`
- `docs/ai/architecture.md`
- pack tests and installer tests

Files deliberately not added:
- no dependency solver for pack combinations
- no language-specific release harness

Validation:
- render tests that preserve the existing `frontend-ui` and `node-api-service` combinations
- library-detection tests that distinguish reusable packages from normal apps
- render tests for `library-package` alone and in combination with compatible packs

Main risk:
- misclassifying apps as libraries and shipping the wrong guidance; keep the pack conservative and evidence-heavy

Implemented baseline:
- `library-package` ships as a conservative optional pack backed by explicit `package.json` library metadata
- app and service signals suppress automatic `library-package` recommendations to avoid normal app misclassification
- pack interaction guidance documents that `javascript-typescript-app` can compose with UI, API, or library packs while surface-specific packs remain independently justified

### 3.0 Step 6: Section-Aware Upgrade, Refresh, And Validation
Objective:
- make refresh and upgrade flows section-aware where safe, while keeping proposal mode for real repo-owned drift and enforcing the new lifecycle rules in validation

Files to change:
- `scripts/install_enhancer.py`
- `scripts/install_enhancer_gui.py`
- `scripts/enhancer_validator.py`
- `scaffold/target-repo/tests/test_check.py`
- `tests/test_install_enhancer.py`
- `tests/test_stack_packs.py`

Files deliberately not added:
- no auto-merge engine
- no standalone upgrader binary

Validation:
- lifecycle tests covering install -> manage packs -> refresh -> upgrade
- compatibility tests for `2.x -> 3.0` transitions
- proposal-collision tests that prove existing files under `.codex/enhancer-proposals/` are preserved or explicitly handled
- version-comparison tests that treat equivalent versions such as `3.0` and `3.0.0` consistently
- validator coverage for manifest/section drift and invalid pack-state changes

Main risk:
- lifecycle state drifts across install, refresh, and upgrade paths; the planner and validator have to share the same ownership rules
- proposal mode silently overwrites review work if deterministic proposal paths collide; existing proposal files should be treated as conflicts, uniquely named, or require an explicit overwrite choice
- source-vs-target inspection becomes noisy if version comparison treats semantically equivalent dotted versions as newer or older

Implemented baseline:
- upgrade now refreshes the managed `AGENTS.md:selected-stack-packs` section in place when markers are valid, while still writing broader repo-owned scaffold drift as proposals
- proposal paths are collision-safe; existing files under `.codex/enhancer-proposals/` are preserved and new proposals receive a numbered filename
- source-vs-target inspection normalizes trailing zero version segments so `3.0` and `3.0.0` compare as equivalent
- target validation now checks selected-pack state against `detected_packs` entries and verifies selected-pack summaries inside the managed `AGENTS.md` section, not merely anywhere in the file

### 3.0 Step 7: Docs, Migration Notes, And Release Alignment
Objective:
- align human-facing docs, review guidance, and CI expectations with the fuller `3.0` lifecycle so installed repos can actually use the new capabilities safely

Files to change:
- `README.md`
- `AGENTS.md`
- `docs/ai/architecture.md`
- `docs/ai/code-review.md`
- release or migration notes if the diff is large enough
- `.github/workflows/validate.yml` only if validation commands change

Files deliberately not added:
- no separate documentation site
- no extra CI workflow unless the deterministic validation surface truly changes

Validation:
- `python scripts/check.py --verbose`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- doc-link validation for any new migration note references

Main risk:
- operator docs lag the shipped lifecycle behavior and turn `3.0` into tribal knowledge instead of visible repo guidance

Implemented baseline:
- `docs/ai/migration-v3.md` now records the operator checklist for inspect, upgrade, manage-packs, refresh, proposal review, and validation
- root docs point maintainers to the migration note instead of duplicating lifecycle instructions across every file
- source validation treats the migration note as a required durable workflow document

### 3.0 Success Bar
- an installed repo can change selected packs without reinstalling the enhancer from scratch
- managed sections make refresh and upgrade safer without hiding what the enhancer owns
- pack recommendations are backed by explicit, reviewable evidence instead of vague heuristics
- `library-package` is available only if the stronger detector can justify it
- install, inspect, manage-packs, refresh, and upgrade all stay aligned across CLI, GUI, docs, and validation

## Proposed 3.1 Spec Kit Bridge

Status: implemented in enhancer `3.2` across the installer core, GUI, manifest state, generated bridge guide, and narrow bridge skills. Keep this section as design history plus follow-up context.

### Goal
Make Codex Enhancer coexist cleanly with official GitHub Spec Kit so repos that already use Spec Kit can keep one spec-driven workflow without giving up the enhancer's repo-local guidance, validation, and review discipline.

### Scope
- treat Spec Kit as an optional workflow integration, not a stack pack
- detect and document real official Spec Kit footprints such as `.specify/`, `specs/`, `.github/prompts/`, and `.github/agents/`
- record bridge state in the enhancer manifest without taking ownership of Spec Kit files
- let the installer attach to or bootstrap official Spec Kit deliberately
- add narrow bridge skills that consume Spec Kit artifacts for implementation, sync checks, and review prep

### Non-Goals
- no vendored copy of Spec Kit inside this repo
- no reimplementation of `specify`, Spec Kit templates, or Spec Kit command routing
- no hidden migration state for Spec Kit installs
- no automatic rewriting of `.specify/`, `specs/`, or official prompt or agent files

### 3.1 Step 1: Contract, Scaffold, And Roadmap Groundwork
Objective:
- define the bridge as a first-class optional integration in the shared schema, target scaffold, and durable docs before any installer behavior depends on it

Files to change:
- `scripts/enhancer_spec.py`
- `AGENTS.md`
- `docs/ai/architecture.md`
- `docs/ai/code-review.md`
- `docs/ai/roadmap.md`
- `docs/ai/spec-kit-bridge.md`
- `scaffold/target-repo/AGENTS.md`
- `scaffold/target-repo/docs/ai/architecture.md`
- `scaffold/target-repo/docs/ai/code-review.md`
- `scaffold/target-repo/docs/ai/spec-kit-bridge.md`
- validator fixtures and installer tests

Files deliberately not added:
- no bootstrap command execution yet
- no bridge-specific skills yet
- no Spec Kit file mutation logic

Validation:
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- locking the contract too early and making later bridge phases awkward; keep the first patch limited to ownership, manifest, and visible scaffold markers

### 3.1 Step 2: Detection And Inspect Support
Objective:
- detect official Spec Kit footprints and surface bridge state through inspect and manifest helpers without changing target repos yet

Files to change:
- `scripts/spec_kit_bridge.py`
- `scripts/stack_packs.py`
- `scripts/install_enhancer.py`
- tests

Files deliberately not added:
- no installer apply mode for bootstrap yet

Validation:
- unit tests for detection and command-surface resolution
- inspect output tests for bridge-off, attached, and ambiguous repos

Main risk:
- over-assuming one official Spec Kit layout when the integration surface differs by environment

### 3.1 Step 3: Attach And Bootstrap Installer Flow
Objective:
- let the installer explicitly ignore, attach to, or bootstrap official Spec Kit while preserving clear ownership boundaries

Files to change:
- `scripts/install_enhancer.py`
- `scripts/install_enhancer_gui.py`
- `README.md`
- tests

Files deliberately not added:
- no vendored Spec Kit templates
- no silent network bootstrap

Validation:
- dry-run and apply tests for `off`, `attach`, and `bootstrap` bridge modes
- GUI preview tests for bridge messaging

Main risk:
- user confusion about what the enhancer will overwrite; the preview must separate enhancer-owned writes from untouched official Spec Kit state

### 3.1 Step 4: Artifact-Aware Bridge Skills
Objective:
- add a very small bridge skill set that uses existing Spec Kit artifacts to improve implementation, sync checks, and review prep

Files to change:
- `scaffold/target-repo/.codex/skills/`
- target docs
- installer scaffolding
- tests

Files deliberately not added:
- no broad "do Spec Kit workflow" meta-skill

Validation:
- skill frontmatter tests
- target validation fixture updates
- install tests that confirm bridge-enabled targets receive the right skills

Main risk:
- creating generic skills that duplicate official Spec Kit commands instead of complementing them

### 3.1 Step 5: Review, Drift, And Release Follow-Through
Objective:
- make review guidance, optional drift checks, and release docs reflect the bridge so the workflow stays usable after the first install

Files to change:
- `docs/ai/code-review.md`
- `README.md`
- optional validator or helper scripts if justified
- tests

Files deliberately not added:
- no always-on CI job for Spec Kit repos until the drift checks prove stable

Validation:
- full local check suite
- any added drift checks against stable fixtures

Main risk:
- shipping documentation that promises more than the bridge can currently automate

### 3.1 Success Bar
- a repo can keep using official Spec Kit without the enhancer fighting its files or command surface
- the enhancer manifest and `AGENTS.md` make bridge state visible to humans and Codex
- installer previews explain exactly what the enhancer owns and what remains official Spec Kit state
- bridge skills improve implementation and review only when Spec Kit artifacts already exist
