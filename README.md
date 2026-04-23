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
- review which files will be created, proposed, or overwritten
- confirm overwrite actions before install
- watch installation progress
- open the product README automatically after completion

If you prefer the CLI or want to script installs, use the commands below.

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

For an existing repo with conflicting files:
- by default, conflicting files are written as proposals under `.codex/enhancer-proposals/`
- use `--force` only when you explicitly want installer-managed files to overwrite existing ones

What gets installed:

```text
AGENTS.md
.codex/skills/
docs/ai/
scripts/check.py
scripts/enhancer_spec.py
scripts/enhancer_validator.py
tests/test_check.py
.github/workflows/validate.yml
.gitignore (merged, not overwritten)
```

After installation, adapt the repo in this order:
1. Update `AGENTS.md` with the target repo's purpose, layout, and real commands.
2. Use the `adapt-enhancer` skill to replace inherited generic guidance.
3. Remove or replace any docs that do not apply to the target repo.
4. Keep only the skills that solve repeated procedures in that repo.
5. Update `scripts/check.py` and `scripts/enhancer_spec.py` so the validation rules match the target repo.
6. Update `tests/test_check.py` so the fixture matches the target repo's expected enhancer shape.
7. Update `.github/workflows/validate.yml` so CI runs the same local commands.

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
python scripts/install_enhancer.py --target ../my-new-repo --mode new
install_enhancer.bat
```

What they do:
- `python scripts/check.py`: validates required files, markdown links, skill frontmatter, and command alignment
- `python scripts/check.py --verbose`: prints each successful check
- `python -m unittest discover -s tests -p "test_*.py" -v`: tests the validator itself
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
[docs/ai/architecture.md](docs/ai/architecture.md) and [docs/ai/code-review.md](docs/ai/code-review.md) hold the durable detail that would otherwise bloat `AGENTS.md`.

Use docs when guidance needs more explanation. Use `AGENTS.md` when guidance must be visible immediately.

### `.codex/skills/`
[.codex/skills/](.codex/skills/) holds narrow, repeatable procedures. The subtree rules live in [.codex/skills/AGENTS.md](.codex/skills/AGENTS.md).

Skills in this repo are intentionally narrow. If a procedure is too broad, too generic, or needs lots of reference material, it probably belongs in `docs/ai/` instead.

### `scripts/install_enhancer.py`
[scripts/install_enhancer.py](scripts/install_enhancer.py) is the bootstrap entrypoint. It:
- scaffolds enhancer files into a target repo
- discovers a small set of likely commands from common manifests
- merges `.gitignore` entries instead of overwriting the file
- writes proposal files for conflicts in existing repos unless `--force` is used
- exposes structured install planning so the GUI and CLI share the same overwrite and progress behavior

### `scripts/install_enhancer_gui.py`
[scripts/install_enhancer_gui.py](scripts/install_enhancer_gui.py) is the Windows-first GUI layer over the installer core. It adds:
- manual path entry plus folder browsing
- a readable install preview grouped by creates, overwrites, and proposals
- an overwrite acknowledgement gate before destructive install actions
- a progress bar tied to real install steps
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

### `tests/`
[tests/test_check.py](tests/test_check.py) gives you regression coverage for the source-repo validator.
[tests/test_install_enhancer.py](tests/test_install_enhancer.py) verifies dry-run behavior, actual installs, proposal mode, force overwrite on safe paths, and the installed target profile.

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
|-- scripts/enhancer_spec.py
|-- scripts/enhancer_validator.py
|-- scaffold/target-repo/
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
