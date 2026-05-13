# Codex Enhancer Roadmap

## Purpose
This roadmap records the phased enhancer design from the shipped `2.x` stack-pack work through the implemented `3.x` lifecycle, Spec Kit bridge, Utility Harness, and packaging-readiness work. The core idea remains optional, visible, repo-local workflow guidance that improves Codex use without turning the enhancer into an agent runtime, package manager, or hidden orchestration layer.

Sections through `3.4` are retained as design history and implementation context. The `4.0` product maturity work is retained as the completed audit-backed roadmap for first-time-user polish, safer command execution, packaging confidence, and integration-ready installer output. The `4.1` section is the active follow-up plan from a first-time-user product audit and should be treated as the next implementation contract.

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

## Proposed 3.3 Codex Utility Harness

Status: implemented as an optional install-time integration. Keep this section as scope history plus future guardrails.

### Goal
Give target repos explicit repo-local helper tools that help Codex inspect large trees, read mixed file formats, summarize structure, and run recorded validation commands without turning the enhancer into a package manager or agent runtime.

### Scope
- install `requirements-codex.txt` for Codex/operator helper dependencies only
- install `tools/ai/inspect_repo.py`, `tools/ai/read_any.py`, `tools/ai/summarize_tree.py`, and `tools/ai/run_checks.py`
- install `docs/ai/utility-harness.md`
- record state under `[integrations.utility_harness]` in the target manifest
- expose the option through CLI and GUI previews before writing

### Non-Goals
- no automatic dependency installation
- no production dependency pollution
- no OCR, daemon, background indexer, package manager, or hidden orchestration
- no guessed validation commands
- no broad Utility Harness skill until repeated use proves one is worth adding

### Success Bar
- a target repo can preview and install the harness explicitly with `--utility-harness-mode install`
- the manifest records whether the harness is absent or installed
- harness file drift is reviewable as normal files or proposals
- helper scripts stay deterministic, bounded, and safe to run without optional dependencies unless richer formats require them

## Proposed 3.4 Spec Kit Usability And Release Hardening

Status: implemented as a narrow CLI and packaging-readiness pass.

### Goal
Make the packaged `codex-enhancer` command more useful for Spec Kit repos after install, while keeping release readiness explicit and reviewable.

### Scope
- add a read-only Spec Kit feature report that summarizes `specs/` feature artifacts, missing core files, and task checkbox state
- add a read-only Spec Kit sync report that maps changed paths to feature artifacts, task state, contracts, quickstart cues, and obvious validation gaps
- add a dedicated bridge-management flow for installed targets so bridge mode, script flavor, and command-surface guidance can change without a full enhancer upgrade
- keep official Spec Kit files read-only from enhancer flows
- document the package release checklist and keep the wheel/sdist boundary visible
- bump the public package version to `3.4.0`

### Non-Goals
- no Spec Kit template rewriting
- no semantic implementation drift engine
- no PR automation
- no package runtime dependencies
- no release publisher or background updater

### Success Bar
- `codex-enhancer spec-report <repo>` gives useful artifact context without writes
- `codex-enhancer spec-sync <repo> --feature <feature> --changed <path>` gives useful code-to-artifact cues without writes
- `codex-enhancer bridge <repo> --attach-spec-kit` previews enhancer-owned bridge updates only
- source validation and packaging tests enforce the release checklist and packaged asset mirror
- release builds remain normal Python wheel/sdist artifacts with no hidden downloader behavior

## 4.0 Product Maturity Roadmap

Status: completed. This section now records the completed audit-backed maturity pass that moved Codex Enhancer from an early-alpha workflow scaffold toward a more trustworthy daily-use tool. Future 4.x work should treat these steps as regression expectations and only add follow-up items when real usage exposes gaps beyond the acceptance criteria below.

Completed implementation:
- README first-run productization, before/after walkthrough, positioning guidance, cross-platform paths, and source-versus-target inspection clarity
- guided adaptation audit, concise preview mode, full diff preview, JSON output, and stronger failure/recovery diagnostics
- safer target-side `tools/ai/run_checks.py` command discovery and execution defaults
- CI package build plus wheel-installed console-script smoke coverage
- pinned Spec Kit bootstrap default, prerequisite/fallback documentation, executable diagnostics, and partial-failure guidance
- machine-readable plan/report surfaces for installer, bridge, pack, inspection, and Spec Kit reporting commands
- installable Utility Harness dependency groups scoped to Codex/operator use

### Goal
Make the enhancer clear, safe, and confidence-building for a technically capable first-time user without changing the project's thin, repo-local architecture.

### Scope
- improve first-run comprehension and product positioning
- make post-install adaptation guided, inspectable, and verifiable
- make installer previews shorter by default while still offering full detail and diffs
- harden target-side command execution before the Utility Harness is promoted as a daily-use helper
- make command discovery distinguish confirmed commands from guessed or suspicious command text
- add release and package smoke tests that prove the distributable `codex-enhancer` command works outside the source checkout
- stabilize Spec Kit bootstrap expectations around prerequisites, version pins, local executable fallback, and recovery
- add machine-readable planning output for wrappers and CI without hidden state
- rationalize Utility Harness dependencies so optional helper installs do not feel all-or-nothing

### Non-Goals
- no rewrite of the installer architecture
- no background service, command daemon, or persistent external database
- no automatic execution of commands extracted from arbitrary prose
- no broad plugin marketplace or framework-specific pack explosion
- no hosted documentation site until the README and repo-local docs are already clear
- no dependency installation during enhancer install, Spec Kit bridge attach, or Utility Harness setup unless the user explicitly runs an external tool

### Existing Baseline To Preserve
- dry-run-first install and upgrade planning
- proposal-mode conflict safety for repo-owned scaffold drift
- visible `.codex/enhancer/manifest.toml` ownership and integration state
- managed sections for enhancer-owned summaries in `AGENTS.md`
- optional stack packs with visible evidence
- read-only Spec Kit feature and sync reports
- optional Utility Harness files that remain Codex/operator-only
- zero runtime package dependencies for the source `codex-enhancer` command

### Sequencing Rationale
Do the user-facing comprehension work first so future behavior changes have a clear story. Then improve trust surfaces around adaptation, previews, diffs, and diagnostics. Harden command execution before making helper automation more discoverable. After that, add release confidence, Spec Kit bootstrap stabilization, machine-readable plans, and dependency rationalization as independent patches.

### 4.0 Step 1: First-Time User Productization
Objective:
- make a first-time user understand what the enhancer does, why it exists, when not to use it, and what a successful first install looks like

Files to change:
- `README.md`
- `docs/ai/architecture.md`
- `docs/ai/roadmap.md`
- `docs/ai/code-review.md`, if review guidance needs the new productization checks
- `tests/test_check.py`, only if source validation expectations need new required snippets

Files deliberately not added or changed:
- no new documentation site
- no new installer behavior in this step
- no new skill just to explain the product
- no marketing page that duplicates the README

Implementation steps:
1. Restructure the README so the first screen answers: what it is, who it is for, why it beats plain prompts in the right situation, and what the first successful workflow looks like.
2. Add a concrete before/after walkthrough using a tiny target repo: preview command, expected plan shape, files created, adaptation pass, validation, and final trust checks.
3. Add a decision table comparing Codex Enhancer with plain `AGENTS.md`, Claude Code conventions, official Spec Kit, and normal repo prompts.
4. Add cross-platform first-run paths for source checkout, installed console script, Windows GUI, and CLI-only macOS/Linux use.
5. Clarify source-repo inspection versus installed-target inspection so `--inspect-install .` on the product repo is not mistaken for a failed install.

Validation:
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- manual re-read of every README command and link touched
- optional dry-run of `python scripts/codex_enhancer_cli.py init <probe> --new` if examples change

Main risk:
- making the README longer instead of clearer; solve by moving reference detail out of the first-run path and linking to deeper docs.

Acceptance criteria:
- a new technical user can explain the enhancer's purpose, non-goals, install path, and first useful workflow after reading the top README sections
- the README includes one concrete before/after walkthrough with expected output shape and follow-up commands
- the decision table makes it clear when a plain `AGENTS.md`, Spec Kit alone, or no enhancer is the better choice

### 4.0 Step 2: Guided Adaptation And Trust
Objective:
- turn installation from "files were written" into "the target repo is visibly adapted, reviewable, and ready for Codex"

Files to change:
- `scripts/install_enhancer.py`
- `scripts/codex_enhancer_cli.py`
- `scripts/install_enhancer_gui.py`, if GUI parity is needed
- `scripts/enhancer_spec.py`
- `scripts/enhancer_validator.py`
- `scaffold/target-repo/AGENTS.md`
- `scaffold/target-repo/docs/ai/code-review.md`
- `README.md`
- installer, CLI, and validator tests under `tests/`

Files deliberately not added or changed:
- no hidden adaptation database
- no automatic merge engine for repo-owned scaffold edits
- no AI-generated rewrite of target repo guidance
- no background watcher for installed repos

Implementation steps:
1. Add a guided target audit or adaptation-check mode that detects inherited generic guidance, unresolved placeholders, broad guessed commands, and unreviewed proposal files.
2. Teach install and upgrade next-step output to point at that adaptation check instead of leaving adaptation as an open-ended instruction.
3. Add a concise preview mode for installer dry-runs that shows operation, selected packs, bridge state, write counts, critical conflicts, and next command, with a verbose path for full detail.
4. Add a full diff preview option for planned creates, overwrites, proposals, managed-section refreshes, and `.gitignore` merges.
5. Add stronger diagnostics and recovery notes for partial install, upgrade, refresh, or bootstrap failures.
6. Add contributor hygiene guidance for generated local artifacts such as `dist/`, `*.egg-info/`, `__pycache__/`, and `tests/_tmp/`, preferably as documentation first and a cleanup helper only if repeated manual toil proves it is needed.

Validation:
- unit tests for adaptation-check findings and clean-target success
- installer preview tests for concise and verbose output
- diff-preview tests for creates, overwrites, proposals, managed sections, and `.gitignore`
- failure-path tests that prove recovery guidance is visible
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- an adaptation checker could become a noisy linter for subjective docs; keep findings limited to inherited text, placeholders, stale generated sections, unresolved proposals, and commands the tool can justify with evidence.

Acceptance criteria:
- after a scaffold install, the user has one command that explains what still needs adaptation
- a fully adapted target can pass that check without suppressions
- default previews are short enough for first-time users while full detail and diffs remain available
- failure output tells the user which files may have changed and how to recover

### 4.0 Step 3: Command Safety And Validation Hardening
Objective:
- make target-side command discovery and `tools/ai/run_checks.py` safe enough for semi-trusted or unfamiliar repos

Files to change:
- `scaffold/target-repo/tools/ai/run_checks.py`
- `scripts/install_enhancer.py`
- `scripts/stack_packs.py`, only if command evidence needs shared package-manager helpers
- `scripts/enhancer_spec.py`
- `scripts/enhancer_validator.py`
- `scaffold/target-repo/AGENTS.md`
- `scaffold/target-repo/docs/ai/utility-harness.md`
- `README.md`
- tests covering generated target helper behavior

Files deliberately not added or changed:
- no automatic execution of commands extracted from arbitrary prose
- no hidden allowlist database
- no shell command runner service
- no guessed install, test, lint, or build wrappers when the repo has no confirmed command

Implementation steps:
1. Classify discovered commands as confirmed, inferred, or prose-extracted.
2. Keep confirmed manifest/package-manager commands runnable only through explicit user intent.
3. List inferred or prose-extracted commands by default without executing them.
4. Remove unsafe default execution of backticked validation-looking text from `AGENTS.md` and other docs.
5. Avoid `shell=True` for known argv-safe command forms where practical, and isolate any remaining shell execution behind an explicit flag with warning text.
6. Improve source installer command discovery so guessed commands such as `python -m pytest` are not rendered as confirmed when the repo only has a `tests/` directory.
7. Add fixtures for malicious backticked commands, accidental shell metacharacters, missing pytest, package-manager lockfile selection, and command de-duplication.

Validation:
- unit tests prove malicious or accidental command text is surfaced but not executed by default
- tests prove confirmed commands from trusted structured sources still run with a deliberate flag
- installer tests prove guessed commands are labeled or omitted instead of promoted to canonical target commands
- target validation tests cover command-source metadata if it becomes part of generated files
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- making the helper too conservative to be useful; solve by separating trusted structured command sources from prose and giving users an explicit, reviewable way to run confirmed commands.

Acceptance criteria:
- a new user can run `tools/ai/run_checks.py` in an unfamiliar repo without arbitrary doc text executing
- unsafe command text appears as a finding, not a subprocess
- generated target guidance distinguishes confirmed commands from commands that still need human verification

### 4.0 Step 4: Packaging, CI, And Release Confidence
Objective:
- prove that the packaged command works outside the source checkout and keep release expectations aligned with CI

Files to change:
- `.github/workflows/validate.yml`
- `docs/ai/release.md`
- `README.md`
- `pyproject.toml`
- `MANIFEST.in`
- `codex_enhancer/package_assets.py`, only if asset lookup changes
- `tests/test_packaging.py`
- installer or CLI tests as needed for wheel smoke fixtures

Files deliberately not added or changed:
- no automatic release publisher
- no package runtime dependencies unless a future implementation earns them
- no committed build artifacts
- no PyPI claim until publication actually exists

Implementation steps:
1. Add a CI job or deterministic script that builds wheel and source distribution artifacts.
2. Install the built wheel into a fresh virtual environment and smoke `codex-enhancer list-packs`.
3. Preview a basic install from the wheel-installed command to prove packaged assets are available.
4. Preview the optional helper bundle from the wheel-installed command without running external Spec Kit bootstrap.
5. Keep README, release checklist, package metadata, Python version support, and CI matrix in agreement.
6. Either document Python `3.13+` as required everywhere or broaden support with a tested matrix before changing `requires-python`.

Validation:
- package build smoke in CI
- fresh virtualenv console-script smoke
- packaged asset mirror tests
- no generated `build/`, `dist/`, or `*.egg-info/` committed
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- release checks become slow or flaky if they depend on network installs; keep package smoke local and avoid external Spec Kit downloads in CI.

Acceptance criteria:
- CI proves the built wheel exposes `codex-enhancer` and can find scaffold assets
- release docs and automated checks agree on the package smoke path
- README and `pyproject.toml` state the same Python support policy

### 4.0 Step 5: Spec Kit Bridge Stabilization
Objective:
- make Spec Kit bootstrap and bridge management predictable, reproducible, and recoverable

Files to change:
- `scripts/spec_kit_bridge.py`
- `scripts/install_enhancer.py`
- `scripts/codex_enhancer_cli.py`
- `scripts/install_enhancer_gui.py`
- `docs/ai/spec-kit-bridge.md`
- `docs/ai/migration-v3.md`
- `README.md`
- Spec Kit bridge and installer tests

Files deliberately not added or changed:
- no vendored Spec Kit files
- no rewrite of `.specify/`, `specs/`, `.github/prompts/`, `.github/agents/`, or official Spec Kit skills
- no network bootstrap during dry-runs
- no semantic Spec Kit drift engine in this step

Implementation steps:
1. Document `uv`/`uvx` as a bootstrap prerequisite and make the `--spec-kit-exe` fallback easy to find.
2. Replace silent default bootstrap from moving `main` with either a tested pinned ref or an explicit moving-ref warning in preview, manifest state, and docs.
3. Add preflight checks for bootstrap executable availability where possible without performing downloads.
4. Make bootstrap partial-failure recovery explicit: what may have been written by official Spec Kit, what enhancer files were not yet written, and which command to rerun.
5. Add bridge status diagnostics that distinguish absent, attached, bootstrapped, mixed command surfaces, and source-repo-only Spec Kit footprints.
6. Keep external bootstrap execution visibly separated from enhancer-owned writes in CLI and GUI previews.

Validation:
- tests for default pinned or warning behavior
- tests for `--spec-kit-exe` command rendering and error handling
- tests for partial external-step failure messaging
- tests that official Spec Kit-owned paths are not written by enhancer flows
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- making Spec Kit support look owned by the enhancer; every preview and doc should continue to say official Spec Kit files remain externally owned.

Acceptance criteria:
- a user can tell before apply whether bootstrap needs `uvx`, a local executable, network access, or a moving/pinned ref decision
- failed bootstrap leaves clear recovery guidance
- bridge diagnostics explain current state without touching official Spec Kit files

### 4.0 Step 6: Machine-Readable Planning And Integrations
Objective:
- let wrappers, CI jobs, and future GUI surfaces consume installer plans without parsing human prose

Files to change:
- `scripts/install_enhancer.py`
- `scripts/codex_enhancer_cli.py`
- `scripts/install_enhancer_gui.py`, if it can share the schema
- `scripts/enhancer_spec.py`
- `README.md`
- tests for plan serialization and error output

Files deliberately not added or changed:
- no hidden state store
- no remote API
- no MCP server just to expose local plans
- no JSON-only replacement for the human preview

Implementation steps:
1. Add `--json` output for install, upgrade, refresh, manage-packs, bridge management, Spec Kit reports, and error diagnostics where practical.
2. Define a stable plan schema for operation, target, mode, selected packs, pack evidence, bridge state, Utility Harness state, planned writes, proposal paths, overwrite paths, external steps, `.gitignore` changes, diagnostics, and next steps.
3. Include schema versioning for JSON output separately from the enhancer manifest schema.
4. Ensure JSON mode never performs writes without `--write`.
5. Add tests that verify JSON output is parseable, stable, and free of human-only formatting.

Validation:
- JSON schema snapshot or structural tests for every major operation
- parse tests for expected error output
- existing human-output tests remain meaningful
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- overcommitting to a schema before wrappers exist; keep the first schema small, explicit, versioned, and limited to data the installer already owns.

Acceptance criteria:
- a CI job can preview an install or upgrade and make decisions from JSON without scraping text
- the human preview remains the default interface
- JSON output has a documented schema version and tests that catch accidental breaking changes

### 4.0 Step 7: Utility Harness And Dependency Rationalization
Objective:
- keep the Utility Harness useful without making target repos install a large, unclear helper dependency bundle

Files to change:
- `scaffold/target-repo/requirements-codex.txt`
- `scaffold/target-repo/docs/ai/utility-harness.md`
- `scaffold/target-repo/tools/ai/read_any.py`, only if optional dependency grouping needs clearer runtime messages
- `scripts/utility_harness.py`
- `scripts/install_enhancer.py`
- `scripts/enhancer_spec.py`
- `scripts/enhancer_validator.py`
- `README.md`
- `docs/ai/utility-harness.md`
- Utility Harness and installer tests

Files deliberately not added or changed:
- no automatic dependency installation
- no production dependency integration
- no background indexer, daemon, OCR pipeline, or broad code-analysis platform
- no new helper dependency without a named tool and documented use

Implementation steps:
1. Split helper dependencies into documented groups such as minimal, document readers, spreadsheets/slides, and code-analysis extras, or keep one file with clear comments if multiple files create more friction than value.
2. Document which helper needs each dependency and what still works without it.
3. Improve `read_any.py` missing-dependency messages if grouped dependencies make remediation easier.
4. Ensure installer previews and manifest state still make Utility Harness installation explicit and optional.
5. Add validation that Utility Harness dependencies remain Codex/operator-only and do not appear in production dependency files.

Validation:
- Utility Harness resolver tests
- scaffold validation tests for grouped dependency files or documented sections
- tests for missing optional reader dependencies, if messages change
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- splitting dependencies could make setup harder; only split where it reduces real user burden, and keep a documented all-in helper path if needed.

Acceptance criteria:
- a user can see exactly why each optional helper dependency exists
- a target repo can install only the helper dependency group it needs
- no production dependency file is touched by Utility Harness setup

### 4.0 Success Bar
- a first-time technical user can complete a documented preview -> apply -> adapt -> validate loop without outside explanation
- installed targets have a verifiable adaptation path instead of a vague "clean this up later" instruction
- command execution defaults are safe for unfamiliar repos
- package build and wheel smoke checks run in CI before release
- Spec Kit bootstrap is explicit about prerequisites, version stability, and recovery
- installer plans can be consumed by humans and machines without hidden state
- Utility Harness dependencies are optional, explained, and scoped to Codex/operator use

## 4.1 Audit-Derived Improvement Instructions

Status: active. This section converts the first-time-user product audit into implementation instructions. The goal is not to add a large new feature surface; it is to make the existing enhancer easier to trust, harder to misuse, and clearer as a daily Codex workflow helper.

### Goal
Turn the audit findings into small, evidence-backed improvements that strengthen onboarding, write safety, roadmap clarity, packaging confidence, and real-world Codex workflow value without changing the enhancer's repo-local architecture.

### Scope
- shorten the first-run path and make source-checkout usage obvious before the installed command is shown
- harden risky write flows so target repos cannot be modified on top of dirty worktrees without explicit operator intent
- make external setup actions, especially Spec Kit bootstrap commands, visible in concise previews
- add guardrails that prevent users from accidentally treating the enhancer source repo as an install target
- clarify distribution status, Python support, POSIX shim behavior, and active versus historical roadmap material
- add a concrete worked example showing how the enhancer changes a Codex-assisted workflow in practice
- improve auditability for stack-pack detection, external links, and cross-platform release confidence

### Non-Goals
- no implementation of all audit findings in one patch
- no hosted docs site, daemon, package manager, or background service
- no AI-generated rewrite of target repo instructions
- no automatic dependency install or network action in default dry-runs
- no broad license change without an explicit project decision
- no speculative metrics framework before there are stable real-world examples to measure

### Existing Baseline To Preserve
- dry-run-first installer behavior
- proposal files for repo-owned conflicts
- visible manifest ownership and managed sections
- optional, evidence-backed stack packs
- read-only Spec Kit reports and explicit bootstrap mode
- Utility Harness dependencies isolated from production dependency files
- zero third-party runtime dependencies for the enhancer command
- canonical validation through `python scripts/check.py` and `python -m unittest discover -s tests -p "test_*.py" -v`

### 4.1 Step 1: First-Run Clarity And Proof Of Value
Objective:
- make a first-time user understand the install path, source-checkout commands, and practical value before they reach the reference sections

Files to change:
- `README.md`
- `docs/ai/roadmap.md`
- `docs/ai/architecture.md`, only if the product positioning changes
- README mirror assets or packaging tests only if packaged documentation expectations change

Files deliberately not added or changed:
- no hosted documentation site
- no new CLI behavior in this step
- no new skill just to explain the enhancer

Implementation steps:
1. Add a 5-minute path near the top of the README with separate command lanes for source checkout, editable install, wheel install, and Windows GUI use.
2. Move or link advanced material so the first screen answers: what this is, when to use it, when not to use it, and what a successful first workflow looks like.
3. Add one concrete before/after walkthrough that shows a tiny target repo before install, the dry-run plan shape, the applied files, the adaptation audit, and the validation loop.
4. Explain why the enhancer is useful compared with plain `AGENTS.md`, normal prompts, Claude Code conventions, official Spec Kit alone, and generic automation tools.
5. Clarify distribution status so users know whether to install from source, a wheel artifact, or a published package channel.

Validation:
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- manual command audit for every command shown in the first-run path

Main risk:
- making the README longer without making it easier; solve by keeping the top path short and moving reference detail deeper.

Acceptance criteria:
- a new user can run a read-only first command from a fresh clone without first installing the console script
- the README includes one evidence-backed before/after workflow
- the README states the supported install channels and does not imply unverified publication

### 4.1 Step 2: Write-Safety Guardrails
Objective:
- make `--write` safer for real projects by requiring explicit consent before modifying dirty target repos or source checkouts

Files to change:
- `scripts/install_enhancer.py`
- `scripts/codex_enhancer_cli.py`
- `scripts/install_enhancer_gui.py`, if GUI parity is needed
- `README.md`
- installer and CLI tests under `tests/`

Files deliberately not added or changed:
- no hidden rollback database
- no automatic stash, reset, checkout, or destructive cleanup
- no write behavior that bypasses dry-run-first planning

Implementation steps:
1. Change dirty worktree handling from warning-only to blocked-by-default for write operations against git repos.
2. Add an explicit override such as `--allow-dirty` with JSON and human diagnostics that name the risk.
3. Add a source-checkout guard that refuses installing into the enhancer source repo unless an explicit escape hatch is provided.
4. Preserve existing proposal-mode conflict behavior and make the new dirty/source guards appear before any external bootstrap or file write.
5. Extend tests for clean targets, dirty targets, source-checkout targets, JSON error output, and override behavior.

Validation:
- focused installer and CLI tests for dirty/source guards
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- blocking legitimate advanced workflows; solve with an explicit, auditable override flag instead of removing the capability.

Acceptance criteria:
- `--write` exits before modifying a dirty git target unless the override is present
- installing into the enhancer source checkout requires deliberate acknowledgement
- diagnostics explain what the user should commit, stash manually, or re-run

### 4.1 Step 3: External Action Transparency
Objective:
- make concise previews show enough information for users to audit external setup before applying changes

Files to change:
- `scripts/install_enhancer.py`
- `scripts/codex_enhancer_cli.py`
- `scripts/install_enhancer_gui.py`, if summary previews are shared there
- `docs/ai/spec-kit-bridge.md`
- `README.md`
- Spec Kit bridge and installer tests

Files deliberately not added or changed:
- no network action during dry-run
- no vendored Spec Kit files
- no hidden installer bootstrap step

Implementation steps:
1. Include exact external bootstrap commands, executable paths, pinned refs, and fallback hints in `--summary` output when external steps are planned.
2. Keep full previews and JSON output aligned with the concise summary fields.
3. Add a warning when a command requires network access or an executable that is not present.
4. Keep external bootstrap ordering explicit: official tool first, enhancer-owned writes second.
5. Test summary, full preview, JSON, and failure-path output for external steps.

Validation:
- focused Spec Kit bridge and installer tests
- dry-run smoke for `init <probe> --new --with-spec-kit --summary`
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- leaking too much command detail into the concise view; solve by showing the command line and a short reason, with full detail still available elsewhere.

Acceptance criteria:
- a user can see the exact external command before approving `--write`
- JSON and human previews agree on external step count, command, executable, and recovery hint
- dry-runs never execute external bootstrap

### 4.1 Step 4: Roadmap And Documentation Hygiene
Objective:
- make current priorities easy to find without deleting useful design history

Files to change:
- `docs/ai/roadmap.md`
- `README.md`
- `AGENTS.md`, only if the repo map or canonical guidance changes

Files deliberately not added or changed:
- no large archival migration unless the roadmap remains hard to scan after this step
- no rewrite of completed history just to make old sections read like new work

Implementation steps:
1. Clearly label active, completed, and historical roadmap sections.
2. Move stale-looking historical version notes into an explicit history subsection or add context that prevents them being read as active instructions.
3. Add a short active-priorities summary that points to the current implementation steps.
4. Keep README references to the roadmap accurate after any split or relabeling.

Validation:
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- manual scan for broken internal links and misleading "current" language

Main risk:
- losing useful design context; solve by relabeling first and splitting only if the file remains too heavy.

Acceptance criteria:
- the top of the roadmap identifies the active section in one paragraph
- completed `4.0` work cannot be mistaken for the next implementation plan
- old version notes are clearly historical

### 4.1 Step 5: Cross-Platform And Release Confidence
Objective:
- increase confidence that documented install paths work outside the author's Windows source checkout

Files to change:
- `.github/workflows/validate.yml`
- `pyproject.toml`
- `MANIFEST.in`
- `README.md`
- `docs/ai/release.md`
- `codex-enhancer`
- packaging and CLI tests under `tests/`

Files deliberately not added or changed:
- no automatic release publisher
- no committed build artifacts
- no PyPI claim unless publication is verified

Implementation steps:
1. Decide whether Python `3.13+` is a hard requirement or can be broadened with tested support for older Python versions.
2. Add or document a CI matrix for the chosen Python and operating-system support policy.
3. Fix or document POSIX source-shim execution if the checkout command is advertised for macOS/Linux users.
4. Keep wheel/sdist build checks and packaged asset smoke tests aligned with README install guidance.
5. Make release docs state the supported distribution channels and what is intentionally unpublished.

Validation:
- packaging tests
- wheel-installed `codex-enhancer list-packs` smoke
- CI matrix, if added
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- widening support without actually testing it; solve by keeping the declared support policy exactly as broad as CI proves.

Acceptance criteria:
- README, `pyproject.toml`, release docs, and CI agree on Python support
- documented source-checkout shims work or are replaced by explicit Python commands
- users can tell whether the package is source-only, wheel-distributed, or published

### 4.1 Step 6: Auditability And Trust Surfaces
Objective:
- help users trust what the enhancer detected, skipped, and validated

Files to change:
- `scripts/stack_packs.py`
- `scripts/codex_enhancer_cli.py`
- `scripts/enhancer_validator.py`
- `README.md`
- `docs/ai/release.md`, if external link checks become release-only
- tests for pack reporting and validation

Files deliberately not added or changed:
- no remote telemetry
- no broad semantic codebase index
- no automatic fixes for every audit finding

Implementation steps:
1. Add a pack-explanation mode or enrich existing pack output so users can see evidence, skipped signals, and false-positive boundaries.
2. Add an optional external-link check with timeouts and clear "unverified" reporting, or document that normal validation only checks local links.
3. Add a small real-world evaluation checklist for whether the enhancer improved a Codex workflow, such as fewer repeated prompts, clearer validation commands, or safer handoff.
4. Add targeted fixtures only for recurring bug classes or stable behavior, not speculative eval machinery.

Validation:
- stack-pack reporting tests
- optional link-check tests with deterministic fixtures if implemented
- `python scripts/check.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Main risk:
- turning trust work into noisy scoring; keep it evidence-based, explainable, and optional where external systems are involved.

Acceptance criteria:
- pack choices are explainable from visible repo evidence
- documentation is clear about which links and facts are locally validated
- the repo has a lightweight way to record whether the enhancer helped an actual Codex workflow

### 4.1 Step 7: Larger Follow-Ups To Defer Until Needed
Objective:
- capture valuable audit findings that are real but should not displace the safer short-term work

Candidate work:
- minimal, standard, and full install profiles if file-count friction remains after onboarding improvements
- transactional writes or a structured apply log if partial-write recovery remains a user trust blocker
- Utility Harness dependency grouping if users report the helper dependency bundle feels too broad
- license strategy review if broader organizational adoption is a goal
- richer GUI QA once the CLI path is stable and the GUI is a common entrypoint

Deferral rule:
- start one of these only after a user report, repeated maintainer friction, or a targeted implementation plan shows that the smaller 4.1 steps are not enough.
