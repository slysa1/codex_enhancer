#!/usr/bin/env python3
"""Reusable validation engine for Codex Enhancer repositories."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from scripts.enhancer_spec import ValidationProfile


LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def is_ignored_path(root: Path, path: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    if ".git" in relative_parts or "__pycache__" in relative_parts:
        return True
    if len(relative_parts) >= 2 and relative_parts[0] == "tests" and relative_parts[1] == "_tmp":
        return True
    if len(relative_parts) >= 2 and relative_parts[0] == ".codex" and relative_parts[1] == "enhancer-proposals":
        return True
    if len(relative_parts) >= 2 and relative_parts[0] == "scaffold" and relative_parts[1] == "target-repo":
        return True
    return False


def iter_markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not is_ignored_path(root, path)
    )


def add_error(errors: list[str], message: str, hint: str | None = None) -> None:
    if hint:
        errors.append(f"{message} Hint: {hint}")
        return
    errors.append(message)


def hint_for_required_file(relative_path: Path) -> str:
    relative_text = relative_path.as_posix()
    if relative_text.startswith(".codex/skills/"):
        return (
            "Restore the skill file or remove its references in docs and validator "
            "rules if the skill was intentionally retired."
        )
    if relative_text.startswith("docs/ai/"):
        return (
            "Recreate the durable doc or move its guidance elsewhere and update "
            "AGENTS.md, review docs, and validator expectations in the same patch."
        )
    if relative_text == ".github/workflows/validate.yml":
        return "Keep CI aligned with the local validation commands in this repository."
    return (
        "Restore the file, or if the repo shape changed intentionally, update the "
        "validator and the related docs in the same patch."
    )


def hint_for_line_limit(relative_path: Path) -> str:
    if relative_path.as_posix() == "AGENTS.md":
        return "Keep AGENTS.md as the repo map and move durable detail into docs/ai/."
    return "Move detail into a narrower doc or skill so the entrypoint stays concise."


def hint_for_broken_link(target: str) -> str:
    return (
        f"Fix the relative path for {target!r}, add the missing target, or remove the "
        "stale link."
    )


def hint_for_frontmatter_issue(kind: str) -> str:
    hints = {
        "missing": "Start the file with a --- frontmatter block containing name and description.",
        "unterminated": "Close the frontmatter with a second --- line before the skill body.",
        "invalid_line": "Use simple key: value lines in frontmatter; nested YAML is not supported here.",
        "keys": "Keep skill frontmatter limited to name and description in this repository.",
        "name": "Match the folder name exactly so the skill stays discoverable and predictable.",
        "description": "Add a concrete 'Use when ...' trigger so the skill has a narrow invocation boundary.",
        "do_not_use": "Add a ## Do not use section with explicit non-goals and boundary conditions.",
    }
    return hints[kind]


def hint_for_content_requirement(relative_path: Path, snippet: str) -> str:
    if relative_path.as_posix() == ".github/workflows/validate.yml":
        return (
            "Mirror the same commands in CI that contributors run locally; update both "
            "surfaces together when commands change."
        )
    if "python scripts/check.py" in snippet or "python -m unittest discover" in snippet:
        return (
            "Keep the canonical validation commands visible anywhere this repo defines "
            "its review or validation workflow."
        )
    return (
        "Add the missing canonical reference or update validator expectations if the "
        "rule changed intentionally."
    )


def check_required_files(
    root: Path,
    profile: ValidationProfile,
    errors: list[str],
    verbose: bool,
) -> None:
    for relative_path in profile.required_files:
        full_path = root / relative_path
        if not full_path.exists():
            add_error(
                errors,
                f"Missing required file: {relative_path.as_posix()}",
                hint_for_required_file(relative_path),
            )
        elif verbose:
            print(f"OK required file: {relative_path.as_posix()}")


def check_line_limits(
    root: Path,
    profile: ValidationProfile,
    errors: list[str],
    verbose: bool,
) -> None:
    for relative_path, max_lines in profile.line_limits.items():
        full_path = root / relative_path
        if not full_path.exists():
            continue
        line_count = len(load_text(full_path).splitlines())
        if line_count > max_lines:
            add_error(
                errors,
                f"{relative_path.as_posix()} has {line_count} lines; limit is {max_lines}",
                hint_for_line_limit(relative_path),
            )
        elif verbose:
            print(
                f"OK line limit: {relative_path.as_posix()} "
                f"({line_count}/{max_lines})"
            )


def resolve_link(source: Path, target: str) -> Path | None:
    cleaned = target.strip()
    if not cleaned or cleaned.startswith(("#", "http://", "https://", "mailto:")):
        return None
    if cleaned.startswith("<") and cleaned.endswith(">"):
        cleaned = cleaned[1:-1]
    cleaned = cleaned.split("#", 1)[0]
    if not cleaned:
        return None
    return (source.parent / cleaned).resolve()


def check_markdown_links(root: Path, errors: list[str], verbose: bool) -> None:
    for path in iter_markdown_files(root):
        text = load_text(path)
        matches = list(LINK_RE.finditer(text))
        for match in matches:
            target = match.group(1)
            resolved = resolve_link(path, target)
            if resolved is None:
                continue
            if not resolved.exists():
                add_error(
                    errors,
                    f"Broken link in {relative(root, path)} -> {target}",
                    hint_for_broken_link(target),
                )
        if verbose:
            print(f"OK links: {relative(root, path)} ({len(matches)} link(s))")


def parse_frontmatter(
    root: Path,
    text: str,
    path: Path,
    errors: list[str],
) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        add_error(
            errors,
            f"{relative(root, path)} is missing YAML frontmatter",
            hint_for_frontmatter_issue("missing"),
        )
        return None

    try:
        end_index = lines[1:].index("---") + 1
    except ValueError:
        add_error(
            errors,
            f"{relative(root, path)} has an unterminated YAML frontmatter block",
            hint_for_frontmatter_issue("unterminated"),
        )
        return None

    frontmatter_lines = lines[1:end_index]
    data: dict[str, str] = {}

    for line in frontmatter_lines:
        if ":" not in line:
            add_error(
                errors,
                f"{relative(root, path)} has an invalid frontmatter line: {line!r}",
                hint_for_frontmatter_issue("invalid_line"),
            )
            return None
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            add_error(
                errors,
                f"{relative(root, path)} has an invalid frontmatter line: {line!r}",
                hint_for_frontmatter_issue("invalid_line"),
            )
            return None
        data[key] = value

    return data


def check_skills(
    root: Path,
    profile: ValidationProfile,
    errors: list[str],
    verbose: bool,
) -> None:
    skills_root = root / ".codex/skills"
    if not skills_root.exists():
        add_error(
            errors,
            "Missing required directory: .codex/skills",
            "Restore the skills subtree or update the repo map and validator together if the workflow layer moved.",
        )
        return

    present_skills: set[str] = set()

    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            add_error(
                errors,
                f"Skill directory missing SKILL.md: {relative(root, skill_dir)}",
                "Each skill folder should contain one SKILL.md entrypoint file.",
            )
            continue

        present_skills.add(skill_dir.name)
        text = load_text(skill_file)
        frontmatter = parse_frontmatter(root, text, skill_file, errors)
        if frontmatter is None:
            continue

        keys = set(frontmatter)
        if keys != {"name", "description"}:
            add_error(
                errors,
                f"{relative(root, skill_file)} must use only 'name' and 'description' "
                "in frontmatter",
                hint_for_frontmatter_issue("keys"),
            )

        if frontmatter.get("name") != skill_dir.name:
            add_error(
                errors,
                f"{relative(root, skill_file)} frontmatter name must match folder name "
                f"'{skill_dir.name}'",
                hint_for_frontmatter_issue("name"),
            )

        description = frontmatter.get("description", "")
        if "Use when" not in description:
            add_error(
                errors,
                f"{relative(root, skill_file)} description must include a concrete "
                "'Use when' trigger",
                hint_for_frontmatter_issue("description"),
            )

        if "## Do not use" not in text:
            add_error(
                errors,
                f"{relative(root, skill_file)} must include a '## Do not use' section",
                hint_for_frontmatter_issue("do_not_use"),
            )

        if verbose:
            print(f"OK skill: {relative(root, skill_file)}")

    missing_skills = sorted(profile.min_required_skills - present_skills)
    for skill_name in missing_skills:
        add_error(
            errors,
            f"Missing required skill: .codex/skills/{skill_name}/SKILL.md",
            "Restore the required skill or update the minimum skill set and its docs in the same patch.",
        )


def check_content_requirements(
    root: Path,
    profile: ValidationProfile,
    errors: list[str],
    verbose: bool,
) -> None:
    for relative_path, snippets in profile.content_requirements.items():
        full_path = root / relative_path
        if not full_path.exists():
            continue
        text = load_text(full_path)
        for snippet in snippets:
            if snippet not in text:
                add_error(
                    errors,
                    f"{relative_path.as_posix()} is missing required text: {snippet!r}",
                    hint_for_content_requirement(relative_path, snippet),
                )
        if verbose:
            print(f"OK content rules: {relative_path.as_posix()}")


def check_stack_pack_outputs(root: Path, profile: ValidationProfile, errors: list[str], verbose: bool) -> None:
    manifest_path = root / ".codex/enhancer/manifest.toml"
    stack_guidance_path = root / "docs/ai/stack-guidance.md"
    agents_path = root / "AGENTS.md"
    if not manifest_path.exists() or not stack_guidance_path.exists():
        return

    try:
        manifest = tomllib.loads(load_text(manifest_path))
    except tomllib.TOMLDecodeError:
        add_error(
            errors,
            ".codex/enhancer/manifest.toml is not valid TOML",
            "Regenerate the enhancer manifest or fix the TOML syntax by hand.",
        )
        return

    selected_packs = manifest.get("selected_packs", [])
    if not isinstance(selected_packs, list) or any(not isinstance(item, str) for item in selected_packs):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define selected_packs as a list of strings",
            "Keep selected_packs as a simple TOML string array.",
        )
        return

    generated_files = manifest.get("generated_files", {})
    if not isinstance(generated_files, dict) or generated_files.get("stack_guidance") != "docs/ai/stack-guidance.md":
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must record docs/ai/stack-guidance.md under [generated_files]",
            "Keep the generated_files.stack_guidance entry aligned with the installed stack guidance file.",
        )

    stack_guidance = load_text(stack_guidance_path)
    agents_text = load_text(agents_path) if agents_path.exists() else ""
    if selected_packs:
        for pack_name in selected_packs:
            snippet = f"`{pack_name}`"
            if snippet not in stack_guidance:
                add_error(
                    errors,
                    f"docs/ai/stack-guidance.md is missing guidance for selected pack {pack_name!r}",
                    "Regenerate the stack guidance or add the missing selected-pack section.",
                )
            if snippet not in agents_text:
                add_error(
                    errors,
                    f"AGENTS.md is missing a root summary for selected pack {pack_name!r}",
                    "Keep the root AGENTS summary aligned with the selected stack packs in the manifest.",
                )
    elif "No stack packs are selected yet." not in stack_guidance:
        add_error(
            errors,
            "docs/ai/stack-guidance.md should explain that no stack packs are selected",
            "Keep the placeholder guidance visible until one or more packs are selected.",
        )

    if verbose:
        print("OK stack pack outputs: .codex/enhancer/manifest.toml and docs/ai/stack-guidance.md")


def validate(root: Path, profile: ValidationProfile, verbose: bool = False) -> list[str]:
    errors: list[str] = []

    check_required_files(root, profile, errors, verbose)
    check_line_limits(root, profile, errors, verbose)
    check_markdown_links(root, errors, verbose)
    check_skills(root, profile, errors, verbose)
    check_content_requirements(root, profile, errors, verbose)
    check_stack_pack_outputs(root, profile, errors, verbose)

    return errors


def run_validation(root: Path, profile: ValidationProfile, verbose: bool = False) -> int:
    errors = validate(root, profile, verbose=verbose)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("All Codex Enhancer checks passed.")
    return 0
