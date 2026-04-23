# Codex Enhancer V2 Design

## Purpose
V2 should make Codex Enhancer meaningfully more helpful in common real-world repositories without turning it into a generic framework. The core idea is optional stack packs: small, visible, repo-local overlays that add durable guidance for common app shapes while preserving the current thin enhancer model.

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
|   `-- v2-design.md
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
schema_version = 1
enhancer_version = "2.1"
selected_packs = ["monorepo-workspace", "javascript-typescript-app"]

[[detected_packs]]
name = "monorepo-workspace"
selected = true
reason = "Found pnpm-workspace.yaml"

[[detected_packs]]
name = "python-service"
selected = false
reason = "No pyproject.toml or requirements.txt found"

[generated_files]
stack_guidance = "docs/ai/stack-guidance.md"
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
- no frontend-ui pack yet
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
- `docs/ai/v2-design.md`

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
