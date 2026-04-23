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
enhancer_version = "2"
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
