#!/usr/bin/env python3
"""Reusable validation engine for Codex Enhancer repositories."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from scripts.enhancer_spec import (
    ENHANCER_MANIFEST_SCHEMA_VERSION,
    MANAGED_SECTIONS,
    ValidationProfile,
)
from scripts.spec_kit_bridge import SPEC_KIT_BRIDGE_SKILLS
from scripts.utility_harness import (
    UTILITY_HARNESS_DEPENDENCY_POLICY,
    UTILITY_HARNESS_DEPENDENCY_FILES,
    UTILITY_HARNESS_REQUIRED_FILES,
    UTILITY_HARNESS_TOOL_FILES,
)


LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def is_ignored_path(root: Path, path: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    if relative_parts and (relative_parts[0] in {"build", "dist"} or relative_parts[0].endswith(".egg-info")):
        return True
    if ".git" in relative_parts or "__pycache__" in relative_parts:
        return True
    if len(relative_parts) >= 2 and relative_parts[0] == "tests" and relative_parts[1] == "_tmp":
        return True
    if len(relative_parts) >= 2 and relative_parts[0] == ".codex" and relative_parts[1] == "enhancer-proposals":
        return True
    if len(relative_parts) >= 2 and relative_parts[0] == "scaffold" and relative_parts[1] == "target-repo":
        return True
    if len(relative_parts) >= 3 and relative_parts[:3] == ("codex_enhancer", "assets", "root"):
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

    enhancer_version = manifest.get("enhancer_version")
    if not isinstance(enhancer_version, str) or not enhancer_version.strip():
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define enhancer_version as a non-empty string",
            "Record the installed enhancer version so future upgrades can compare target state to the current source.",
        )

    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, int):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define schema_version as an integer",
            "Record the enhancer manifest schema so install, refresh, and upgrade flows can reason about compatibility.",
        )
    elif schema_version != ENHANCER_MANIFEST_SCHEMA_VERSION:
        add_error(
            errors,
            f".codex/enhancer/manifest.toml must use schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}",
            "Run the current enhancer upgrade flow to regenerate the manifest before validating with the current checker.",
        )

    lifecycle = manifest.get("lifecycle", {})
    if not isinstance(lifecycle, dict):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define [lifecycle] as a table",
            "Keep lifecycle metadata visible in the manifest so future pack and section management can stay reviewable.",
        )
        lifecycle = {}
    elif schema_version == ENHANCER_MANIFEST_SCHEMA_VERSION:
        if lifecycle.get("state") != "active":
            add_error(
                errors,
                '.codex/enhancer/manifest.toml must set lifecycle.state = "active"',
                "Current installs should explicitly mark the enhancer lifecycle as active.",
            )
        if lifecycle.get("pack_selection") != "manifest":
            add_error(
                errors,
                '.codex/enhancer/manifest.toml must set lifecycle.pack_selection = "manifest"',
                "Pack selection should remain anchored in the visible target manifest.",
            )
        managed_sections = lifecycle.get("managed_sections", [])
        if not isinstance(managed_sections, list) or any(not isinstance(item, str) for item in managed_sections):
            add_error(
                errors,
                ".codex/enhancer/manifest.toml must define lifecycle.managed_sections as a list of strings",
                "Use a simple TOML string array for managed section identifiers.",
            )
            managed_sections = []
        else:
            expected_sections = {section.identifier for section in MANAGED_SECTIONS}
            missing_sections = sorted(expected_sections - set(managed_sections))
            if missing_sections:
                add_error(
                    errors,
                    ".codex/enhancer/manifest.toml is missing managed section ids: "
                    + ", ".join(missing_sections),
                    "Keep lifecycle.managed_sections aligned with visible managed markers in scaffold files.",
                )
            check_managed_section_markers(root, set(managed_sections), errors)

    detected_selection: dict[str, bool] = {}
    detected_packs = manifest.get("detected_packs", [])
    if isinstance(detected_packs, list):
        for entry in detected_packs:
            if not isinstance(entry, dict):
                add_error(
                    errors,
                    ".codex/enhancer/manifest.toml detected_packs entries must be TOML tables",
                    "Keep each detected pack as a [[detected_packs]] table.",
                )
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                add_error(
                    errors,
                    ".codex/enhancer/manifest.toml detected_packs entries must include a non-empty name",
                    "Keep each detected pack tied to a visible stack-pack id.",
                )
                continue
            if name in detected_selection:
                add_error(
                    errors,
                    f".codex/enhancer/manifest.toml repeats detected pack {name!r}",
                    "Keep one detected_packs table per stack pack.",
                )
            selected = entry.get("selected")
            if not isinstance(selected, bool):
                add_error(
                    errors,
                    ".codex/enhancer/manifest.toml detected_packs entries must include selected as a boolean",
                    "Keep detected pack selection state aligned with selected_packs.",
                )
            else:
                detected_selection[name] = selected
            evidence = entry.get("evidence")
            if evidence is None:
                add_error(
                    errors,
                    ".codex/enhancer/manifest.toml detected_packs entries must include evidence",
                    "Record visible evidence for every pack recommendation, even when the pack was not selected.",
                )
            elif not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
                add_error(
                    errors,
                    ".codex/enhancer/manifest.toml detected_packs evidence must be a list of strings",
                    "Use a simple TOML string array for pack evidence.",
                )
    else:
        add_error(
            errors,
            ".codex/enhancer/manifest.toml detected_packs must be an array of tables",
            "Keep pack detection records under repeated [[detected_packs]] TOML tables.",
        )

    selected_set = set(selected_packs)
    if detected_selection:
        missing_selected_records = sorted(selected_set - set(detected_selection))
        if missing_selected_records:
            add_error(
                errors,
                ".codex/enhancer/manifest.toml is missing detected_packs records for selected packs: "
                + ", ".join(missing_selected_records),
                "Keep selected_packs aligned with the per-pack detection records generated by the installer.",
            )
        selected_false = sorted(
            pack_name
            for pack_name in selected_set
            if pack_name in detected_selection and not detected_selection[pack_name]
        )
        if selected_false:
            add_error(
                errors,
                ".codex/enhancer/manifest.toml selected_packs disagree with detected_packs selected flags: "
                + ", ".join(selected_false),
                "Regenerate the manifest so each selected pack has selected = true in its detected_packs table.",
            )
        stale_true = sorted(
            pack_name
            for pack_name, selected in detected_selection.items()
            if selected and pack_name not in selected_set
        )
        if stale_true:
            add_error(
                errors,
                ".codex/enhancer/manifest.toml detected_packs selected flags are stale for unselected packs: "
                + ", ".join(stale_true),
                "Regenerate the manifest so selected flags match the top-level selected_packs list.",
            )

    generated_files = manifest.get("generated_files", {})
    if not isinstance(generated_files, dict):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define a [generated_files] table",
            "Keep generated file paths visible so refresh and review workflows stay explicit.",
        )
        generated_files = {}
    if generated_files.get("stack_guidance") != "docs/ai/stack-guidance.md":
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must record docs/ai/stack-guidance.md under [generated_files]",
            "Keep the generated_files.stack_guidance entry aligned with the installed stack guidance file.",
        )
    if generated_files.get("spec_kit_bridge") != "docs/ai/spec-kit-bridge.md":
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must record docs/ai/spec-kit-bridge.md under [generated_files]",
            "Keep the generated_files.spec_kit_bridge entry aligned with the installed Spec Kit bridge guide.",
        )

    managed_outputs = manifest.get("managed_outputs", {})
    if not isinstance(managed_outputs, dict):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define a [managed_outputs] table",
            "Record which enhancer outputs are safe to regenerate versus usually adapted by hand.",
        )
        managed_outputs = {}

    safe_to_regenerate = managed_outputs.get("safe_to_regenerate", [])
    if not isinstance(safe_to_regenerate, list) or any(not isinstance(item, str) for item in safe_to_regenerate):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define managed_outputs.safe_to_regenerate as a list of strings",
            "Keep managed_outputs.safe_to_regenerate as a TOML string array.",
        )
    else:
        expected_safe_outputs = {
            "docs/ai/stack-guidance.md",
            "docs/ai/spec-kit-bridge.md",
            ".codex/enhancer/manifest.toml",
        }
        if not expected_safe_outputs.issubset(set(safe_to_regenerate)):
            add_error(
                errors,
                ".codex/enhancer/manifest.toml must record docs/ai/stack-guidance.md, docs/ai/spec-kit-bridge.md, and .codex/enhancer/manifest.toml under managed_outputs.safe_to_regenerate",
                "Keep the safe-to-regenerate ownership list aligned with the generated enhancer outputs.",
            )

    adapt_manually = managed_outputs.get("adapt_manually", [])
    if not isinstance(adapt_manually, list) or any(not isinstance(item, str) for item in adapt_manually):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define managed_outputs.adapt_manually as a list of strings",
            "Keep managed_outputs.adapt_manually as a TOML string array.",
        )
    elif "AGENTS.md" not in adapt_manually:
        add_error(
            errors,
            ".codex/enhancer/manifest.toml should list AGENTS.md under managed_outputs.adapt_manually",
            "Treat the installed AGENTS.md scaffold as a repo-owned file to adapt manually after bootstrap.",
        )

    stack_guidance = load_text(stack_guidance_path)
    agents_text = load_text(agents_path) if agents_path.exists() else ""
    managed_agents_text = selected_stack_pack_section_body(root)
    if selected_packs:
        for pack_name in selected_packs:
            snippet = f"`{pack_name}`"
            if snippet not in stack_guidance:
                add_error(
                    errors,
                    f"docs/ai/stack-guidance.md is missing guidance for selected pack {pack_name!r}",
                    "Regenerate the stack guidance or add the missing selected-pack section.",
                )
            if managed_agents_text is not None and snippet not in managed_agents_text:
                add_error(
                    errors,
                    f"AGENTS.md managed selected-stack-packs section is missing a root summary for selected pack {pack_name!r}",
                    "Refresh the managed AGENTS section so it matches selected_packs in the manifest.",
                )
            elif managed_agents_text is None and snippet not in agents_text:
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
    elif managed_agents_text is not None and "No stack packs are selected yet." not in managed_agents_text:
        add_error(
            errors,
            "AGENTS.md managed selected-stack-packs section should explain that no stack packs are selected",
            "Refresh the managed AGENTS section so it matches the empty selected_packs list.",
        )

    check_spec_kit_bridge_outputs(root, manifest, errors)
    check_utility_harness_outputs(root, manifest, errors)

    if verbose:
        print("OK stack pack outputs: .codex/enhancer/manifest.toml and docs/ai/stack-guidance.md")


def check_managed_section_markers(root: Path, managed_section_ids: set[str], errors: list[str]) -> None:
    for section in MANAGED_SECTIONS:
        if section.identifier not in managed_section_ids:
            continue

        full_path = root / section.path
        if not full_path.exists():
            add_error(
                errors,
                f"{section.path.as_posix()} is missing managed section {section.identifier!r}",
                "Restore the managed section file or remove the section id from the manifest in the same change.",
            )
            continue

        text = load_text(full_path)
        start_count = text.count(section.start_marker)
        end_count = text.count(section.end_marker)
        if start_count != 1 or end_count != 1:
            add_error(
                errors,
                f"{section.path.as_posix()} must contain exactly one managed section marker pair for {section.identifier!r}",
                "Keep one visible start marker and one visible end marker around the enhancer-owned content.",
            )
            continue

        if text.index(section.start_marker) > text.index(section.end_marker):
            add_error(
                errors,
                f"{section.path.as_posix()} has reversed managed section markers for {section.identifier!r}",
                "Place the managed section start marker before the matching end marker.",
            )


def managed_section_body(root: Path, identifier: str) -> str | None:
    for section in MANAGED_SECTIONS:
        if section.identifier != identifier:
            continue
        full_path = root / section.path
        if not full_path.exists():
            return None
        text = load_text(full_path)
        if text.count(section.start_marker) != 1 or text.count(section.end_marker) != 1:
            return None
        start_index = text.index(section.start_marker)
        end_index = text.index(section.end_marker)
        if start_index > end_index:
            return None
        return text[start_index + len(section.start_marker) : end_index]
    return None


def selected_stack_pack_section_body(root: Path) -> str | None:
    return managed_section_body(root, "AGENTS.md:selected-stack-packs")


def check_spec_kit_bridge_outputs(root: Path, manifest: dict[str, object], errors: list[str]) -> None:
    integrations = manifest.get("integrations", {})
    if not isinstance(integrations, dict):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define [integrations] as a table",
            "Keep external workflow integrations visible in the target manifest.",
        )
        return

    raw_spec_kit = integrations.get("spec_kit")
    if not isinstance(raw_spec_kit, dict):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define [integrations.spec_kit] as a table",
            "Record the resolved Spec Kit bridge state explicitly, even when the bridge is off.",
        )
        return

    mode = raw_spec_kit.get("mode")
    state = raw_spec_kit.get("state")
    if not isinstance(mode, str) or not mode.strip():
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.spec_kit.mode must be a non-empty string",
            "Keep the resolved bridge mode visible in the manifest.",
        )
    if not isinstance(state, str) or not state.strip():
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.spec_kit.state must be a non-empty string",
            "Keep the resolved bridge state visible in the manifest.",
        )

    available_commands = raw_spec_kit.get("available_commands", [])
    if not isinstance(available_commands, list) or any(not isinstance(item, str) for item in available_commands):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.spec_kit.available_commands must be a list of strings",
            "Use a simple TOML string array for bridge command names.",
        )

    evidence = raw_spec_kit.get("detection_evidence", [])
    if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.spec_kit.detection_evidence must be a list of strings",
            "Record bridge evidence as simple strings so reviewers can trace the decision.",
        )

    paths = raw_spec_kit.get("paths", {})
    if not isinstance(paths, dict):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.spec_kit.paths must be a table",
            "Keep bridge path ownership visible in the manifest.",
        )

    bridge_body = managed_section_body(root, "AGENTS.md:spec-kit-bridge")
    if bridge_body is not None and "docs/ai/spec-kit-bridge.md" not in bridge_body:
        add_error(
            errors,
            "AGENTS.md managed Spec Kit bridge section should link to docs/ai/spec-kit-bridge.md",
            "Keep the root bridge summary anchored to the deeper bridge guide.",
        )

    if state not in {"attached", "bootstrapped"}:
        return

    for skill_name in SPEC_KIT_BRIDGE_SKILLS:
        skill_path = root / ".codex" / "skills" / skill_name / "SKILL.md"
        if not skill_path.exists():
            add_error(
                errors,
                f"Missing Spec Kit bridge skill: .codex/skills/{skill_name}/SKILL.md",
                "Install or restore the bridge skills whenever the manifest records an active Spec Kit bridge.",
            )

    bridge_doc = root / "docs/ai/spec-kit-bridge.md"
    if bridge_doc.exists():
        text = load_text(bridge_doc)
        if "specs/" not in text:
            add_error(
                errors,
                "docs/ai/spec-kit-bridge.md should explain how feature work uses specs/",
                "Keep the bridge guide focused on real Spec Kit artifacts, not just generic references.",
            )
        for skill_name in SPEC_KIT_BRIDGE_SKILLS:
            if skill_name not in text:
                add_error(
                    errors,
                    f"docs/ai/spec-kit-bridge.md is missing bridge skill guidance for {skill_name!r}",
                    "Document each installed bridge skill so users know when to invoke it.",
                )
    if bridge_body is not None and "Spec Kit bridge is" not in bridge_body:
        add_error(
            errors,
            "AGENTS.md managed Spec Kit bridge section should summarize the active bridge state",
            "Refresh the managed bridge section so the root repo map reflects the current bridge mode.",
        )


def check_utility_harness_outputs(root: Path, manifest: dict[str, object], errors: list[str]) -> None:
    integrations = manifest.get("integrations", {})
    if not isinstance(integrations, dict):
        return

    raw_utility = integrations.get("utility_harness")
    if not isinstance(raw_utility, dict):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml must define [integrations.utility_harness] as a table",
            "Record the resolved Utility Harness state explicitly, even when the harness is off.",
        )
        return

    mode = raw_utility.get("mode")
    state = raw_utility.get("state")
    if not isinstance(mode, str) or mode not in {"off", "install"}:
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.utility_harness.mode must be off or install",
            "Keep the Utility Harness mode as a small explicit choice.",
        )
    if not isinstance(state, str) or state not in {"absent", "installed"}:
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.utility_harness.state must be absent or installed",
            "Keep the Utility Harness state visible and reviewable.",
        )

    dependency_policy = raw_utility.get("dependency_policy")
    if dependency_policy != UTILITY_HARNESS_DEPENDENCY_POLICY:
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.utility_harness.dependency_policy is missing or stale",
            "Keep the manifest explicit that harness packages are Codex/operator-only helper dependencies.",
        )

    tool_files = raw_utility.get("tool_files", [])
    if not isinstance(tool_files, list) or any(not isinstance(item, str) for item in tool_files):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.utility_harness.tool_files must be a list of strings",
            "Use a simple TOML string array for installed harness tool paths.",
        )
        tool_files = []

    if state != "installed":
        return

    dependency_files = raw_utility.get("dependency_files", [])
    if not isinstance(dependency_files, list) or any(not isinstance(item, str) for item in dependency_files):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.utility_harness.dependency_files must be a list of strings",
            "Record the all-in and group-specific Utility Harness dependency files explicitly.",
        )
        dependency_files = []

    expected_dependency_files = {path.as_posix() for path in UTILITY_HARNESS_DEPENDENCY_FILES}
    if expected_dependency_files - set(dependency_files):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.utility_harness.dependency_files is missing installed dependency group files",
            "Regenerate the manifest or restore the missing Utility Harness dependency file records.",
        )

    expected_tools = {path.as_posix() for path in UTILITY_HARNESS_TOOL_FILES}
    if expected_tools - set(tool_files):
        add_error(
            errors,
            ".codex/enhancer/manifest.toml integrations.utility_harness.tool_files is missing installed tool paths",
            "Regenerate the manifest or restore the missing Utility Harness tool records.",
        )

    for relative_path in UTILITY_HARNESS_REQUIRED_FILES:
        full_path = root / relative_path
        if not full_path.exists():
            add_error(
                errors,
                f"Missing Utility Harness file: {relative_path.as_posix()}",
                "Restore the optional harness file or set integrations.utility_harness.state to absent if the harness was removed intentionally.",
            )

    docs_path = root / "docs/ai/utility-harness.md"
    if docs_path.exists():
        docs_text = load_text(docs_path)
        for snippet in (
            "requirements-codex.txt",
            "requirements-codex-readers.txt",
            "tools/ai/inspect_repo.py",
            "Do not add these packages to production dependency files",
        ):
            if snippet not in docs_text:
                add_error(
                    errors,
                    f"docs/ai/utility-harness.md is missing required Utility Harness guidance: {snippet!r}",
                    "Keep the harness guide focused on explicit helper use and dependency isolation.",
                )


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
