#!/usr/bin/env python3
"""Load and detect optional V2 stack packs for Codex Enhancer."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path


STACK_PACK_ROOT = Path(__file__).resolve().parents[1] / "scaffold/stack-packs"


@dataclass(frozen=True)
class PackDiscovery:
    all_files: tuple[Path, ...]
    any_files: tuple[Path, ...]
    any_globs: tuple[str, ...]
    all_dirs: tuple[Path, ...]
    exclude_files: tuple[Path, ...]


@dataclass(frozen=True)
class PackUi:
    recommended_if_detected: bool
    default_selected: bool
    order: int


@dataclass(frozen=True)
class PackRender:
    agents_summary: Path
    stack_guidance: Path
    review_notes: Path


@dataclass(frozen=True)
class StackPack:
    root: Path
    schema_version: int
    name: str
    label: str
    description: str
    version: str
    discovery: PackDiscovery
    ui: PackUi
    render: PackRender


@dataclass(frozen=True)
class PackDetection:
    pack: StackPack
    detected: bool
    recommended: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PackSelection:
    pack: StackPack
    detected: bool
    recommended: bool
    reasons: tuple[str, ...]
    selected: bool
    selection_source: str


def _required_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected non-empty string for {key!r}.")
    return value


def _tuple_of_paths(data: dict[str, object], key: str) -> tuple[Path, ...]:
    raw = data.get(key, [])
    if raw == []:
        return ()
    if not isinstance(raw, list) or any(not isinstance(item, str) or not item.strip() for item in raw):
        raise ValueError(f"Expected {key!r} to be a list of strings.")
    return tuple(Path(item) for item in raw)


def _tuple_of_globs(data: dict[str, object], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if raw == []:
        return ()
    if not isinstance(raw, list) or any(not isinstance(item, str) or not item.strip() for item in raw):
        raise ValueError(f"Expected {key!r} to be a list of strings.")
    return tuple(raw)


def _required_section(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Expected table section {key!r}.")
    return value


def load_stack_pack(pack_dir: Path) -> StackPack:
    pack_toml = pack_dir / "pack.toml"
    raw = tomllib.loads(pack_toml.read_text(encoding="utf-8"))
    schema_version = raw.get("schema_version")
    if not isinstance(schema_version, int):
        raise ValueError(f"{pack_toml} must define integer schema_version.")

    discovery = _required_section(raw, "discovery")
    ui = _required_section(raw, "ui")
    render = _required_section(raw, "render")

    pack = StackPack(
        root=pack_dir,
        schema_version=schema_version,
        name=_required_str(raw, "name"),
        label=_required_str(raw, "label"),
        description=_required_str(raw, "description"),
        version=_required_str(raw, "version"),
        discovery=PackDiscovery(
            all_files=_tuple_of_paths(discovery, "all_files"),
            any_files=_tuple_of_paths(discovery, "any_files"),
            any_globs=_tuple_of_globs(discovery, "any_globs"),
            all_dirs=_tuple_of_paths(discovery, "all_dirs"),
            exclude_files=_tuple_of_paths(discovery, "exclude_files"),
        ),
        ui=PackUi(
            recommended_if_detected=bool(ui.get("recommended_if_detected", False)),
            default_selected=bool(ui.get("default_selected", False)),
            order=int(ui.get("order", 100)),
        ),
        render=PackRender(
            agents_summary=Path(_required_str(render, "agents_summary")),
            stack_guidance=Path(_required_str(render, "stack_guidance")),
            review_notes=Path(_required_str(render, "review_notes")),
        ),
    )
    _validate_pack(pack)
    return pack


def _validate_pack(pack: StackPack) -> None:
    if pack.schema_version != 1:
        raise ValueError(f"Unsupported stack pack schema_version for {pack.name}: {pack.schema_version}")
    if not (
        pack.discovery.all_files
        or pack.discovery.any_files
        or pack.discovery.any_globs
        or pack.discovery.all_dirs
    ):
        raise ValueError(f"Stack pack {pack.name} must define at least one discovery signal.")
    for fragment_path in (
        pack.render.agents_summary,
        pack.render.stack_guidance,
        pack.render.review_notes,
    ):
        full_path = pack.root / fragment_path
        if not full_path.exists():
            raise ValueError(f"Stack pack {pack.name} is missing fragment {fragment_path.as_posix()}")


def load_stack_packs(pack_root: Path | None = None) -> tuple[StackPack, ...]:
    root = (pack_root or STACK_PACK_ROOT).resolve()
    packs = [load_stack_pack(path) for path in root.iterdir() if path.is_dir()]
    packs.sort(key=lambda pack: (pack.ui.order, pack.name))
    return tuple(packs)


def _matches_all_files(target: Path, paths: tuple[Path, ...]) -> tuple[bool, tuple[Path, ...]]:
    if not paths:
        return True, ()
    missing = tuple(path for path in paths if not (target / path).exists())
    return not missing, missing


def _matches_all_dirs(target: Path, paths: tuple[Path, ...]) -> tuple[bool, tuple[Path, ...]]:
    if not paths:
        return True, ()
    missing = tuple(path for path in paths if not (target / path).is_dir())
    return not missing, missing


def _existing_any_files(target: Path, paths: tuple[Path, ...]) -> tuple[Path, ...]:
    return tuple(path for path in paths if (target / path).exists())


def _existing_globs(target: Path, patterns: tuple[str, ...]) -> tuple[Path, ...]:
    matches: list[Path] = []
    for pattern in patterns:
        for match in target.glob(pattern):
            matches.append(match.relative_to(target))
    matches = sorted(set(matches), key=lambda item: item.as_posix())
    return tuple(matches)


def _format_path_list(paths: tuple[Path, ...]) -> str:
    return ", ".join(path.as_posix() for path in paths)


def detect_stack_pack(pack: StackPack, target: Path) -> PackDetection:
    resolved_target = target.resolve()
    excluded = tuple(path for path in pack.discovery.exclude_files if (resolved_target / path).exists())
    if excluded:
        return PackDetection(
            pack=pack,
            detected=False,
            recommended=False,
            reasons=(f"excluded by {_format_path_list(excluded)}",),
        )

    matches_required_files, missing_required_files = _matches_all_files(
        resolved_target, pack.discovery.all_files
    )
    if not matches_required_files:
        return PackDetection(
            pack=pack,
            detected=False,
            recommended=False,
            reasons=(f"missing required file {_format_path_list(missing_required_files)}",),
        )

    matches_required_dirs, missing_required_dirs = _matches_all_dirs(
        resolved_target, pack.discovery.all_dirs
    )
    if not matches_required_dirs:
        return PackDetection(
            pack=pack,
            detected=False,
            recommended=False,
            reasons=(f"missing required directory {_format_path_list(missing_required_dirs)}",),
        )

    reasons: list[str] = []
    if pack.discovery.all_files:
        reasons.append(f"found {_format_path_list(pack.discovery.all_files)}")
    if pack.discovery.all_dirs:
        reasons.append(f"found directories {_format_path_list(pack.discovery.all_dirs)}")

    any_file_matches = _existing_any_files(resolved_target, pack.discovery.any_files)
    any_glob_matches = _existing_globs(resolved_target, pack.discovery.any_globs)

    has_optional_rules = bool(pack.discovery.any_files or pack.discovery.any_globs)
    if has_optional_rules and not (any_file_matches or any_glob_matches):
        details: list[str] = []
        if pack.discovery.any_files:
            details.append(f"files {_format_path_list(pack.discovery.any_files)}")
        if pack.discovery.any_globs:
            details.append(f"globs {', '.join(pack.discovery.any_globs)}")
        return PackDetection(
            pack=pack,
            detected=False,
            recommended=False,
            reasons=(f"missing detection signal from {' or '.join(details)}",),
        )

    if any_file_matches:
        reasons.append(f"found {_format_path_list(any_file_matches)}")
    if any_glob_matches:
        reasons.append(f"matched {_format_path_list(any_glob_matches)}")

    return PackDetection(
        pack=pack,
        detected=True,
        recommended=pack.ui.recommended_if_detected,
        reasons=tuple(reasons),
    )


def detect_stack_packs(
    target: Path,
    packs: tuple[StackPack, ...] | None = None,
) -> tuple[PackDetection, ...]:
    loaded = packs or load_stack_packs()
    return tuple(detect_stack_pack(pack, target) for pack in loaded)


def render_pack_fragment(pack: StackPack, fragment_name: str) -> str:
    fragment_path = getattr(pack.render, fragment_name, None)
    if not isinstance(fragment_path, Path):
        raise ValueError(f"Unknown fragment {fragment_name!r} for stack pack rendering.")
    content = (pack.root / fragment_path).read_text(encoding="utf-8").strip()
    return f"## {pack.label}\n\n{content}\n"


def format_detection_reason(detection: PackDetection) -> str:
    return "; ".join(detection.reasons)


def available_pack_names(
    detections: tuple[PackDetection, ...] | tuple[PackSelection, ...],
) -> frozenset[str]:
    return frozenset(item.pack.name for item in detections)


def resolve_stack_pack_selection(
    detections: tuple[PackDetection, ...],
    *,
    use_recommended_packs: bool = False,
    include_packs: tuple[str, ...] = (),
    exclude_packs: tuple[str, ...] = (),
) -> tuple[PackSelection, ...]:
    available = available_pack_names(detections)
    include_set = set(include_packs)
    exclude_set = set(exclude_packs)

    overlap = include_set & exclude_set
    if overlap:
        names = ", ".join(sorted(overlap))
        raise ValueError(f"Conflicting stack-pack selection for: {names}")

    unknown = sorted((include_set | exclude_set) - available)
    if unknown:
        names = ", ".join(unknown)
        raise ValueError(f"Unknown stack pack name(s): {names}")

    selections: list[PackSelection] = []
    for detection in detections:
        name = detection.pack.name
        if name in exclude_set:
            selections.append(
                PackSelection(
                    pack=detection.pack,
                    detected=detection.detected,
                    recommended=detection.recommended,
                    reasons=detection.reasons,
                    selected=False,
                    selection_source="explicit-exclude",
                )
            )
            continue

        if name in include_set:
            selections.append(
                PackSelection(
                    pack=detection.pack,
                    detected=detection.detected,
                    recommended=detection.recommended,
                    reasons=detection.reasons,
                    selected=True,
                    selection_source="explicit-include",
                )
            )
            continue

        if use_recommended_packs and detection.recommended:
            selections.append(
                PackSelection(
                    pack=detection.pack,
                    detected=detection.detected,
                    recommended=detection.recommended,
                    reasons=detection.reasons,
                    selected=True,
                    selection_source="recommended",
                )
            )
            continue

        if detection.detected and detection.pack.ui.default_selected:
            selections.append(
                PackSelection(
                    pack=detection.pack,
                    detected=detection.detected,
                    recommended=detection.recommended,
                    reasons=detection.reasons,
                    selected=True,
                    selection_source="default",
                )
            )
            continue

        selections.append(
            PackSelection(
                pack=detection.pack,
                detected=detection.detected,
                recommended=detection.recommended,
                reasons=detection.reasons,
                selected=False,
                selection_source="not-selected",
            )
        )

    return tuple(selections)


def selected_pack_names(selections: tuple[PackSelection, ...]) -> tuple[str, ...]:
    return tuple(selection.pack.name for selection in selections if selection.selected)


def _compact_agents_summary_lines(lines: list[str]) -> str:
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if stripped.endswith("."):
            stripped = stripped[:-1]
        items.append(stripped)
    if not items:
        return ""
    return "; ".join(items) + "."


def _render_compact_agents_summary(pack: StackPack) -> str:
    fragment_text = (pack.root / pack.render.agents_summary).read_text(encoding="utf-8")
    return _compact_agents_summary_lines(fragment_text.splitlines())


def render_agents_summary(selections: tuple[PackSelection, ...]) -> str:
    selected = [selection for selection in selections if selection.selected]
    if not selected:
        return (
            "- No stack packs are selected yet. Keep [docs/ai/stack-guidance.md](docs/ai/stack-guidance.md) "
            "and [.codex/enhancer/manifest.toml](.codex/enhancer/manifest.toml) aligned if pack selection changes later."
        )

    lines = [
        "Selected packs: " + ", ".join(f"`{selection.pack.name}`" for selection in selected),
        "",
    ]
    for selection in selected:
        summary = _render_compact_agents_summary(selection.pack)
        lines.append(f"- `{selection.pack.name}` ({selection.pack.label}): {summary}")

    lines.extend(
        [
            "",
            "- Keep [docs/ai/stack-guidance.md](docs/ai/stack-guidance.md) and "
            "[.codex/enhancer/manifest.toml](.codex/enhancer/manifest.toml) aligned if pack selection changes.",
        ]
    )
    return "\n".join(lines)


def render_install_follow_up_lines(selections: tuple[PackSelection, ...]) -> list[str]:
    selected = [selection for selection in selections if selection.selected]
    if not selected:
        return []

    selected_names = ", ".join(f"`{selection.pack.name}`" for selection in selected)
    lines = [
        f"- Review `AGENTS.md` and `docs/ai/stack-guidance.md` for selected packs: {selected_names}.",
    ]
    for selection in selected:
        summary = _render_compact_agents_summary(selection.pack)
        lines.append(f"- `{selection.pack.name}`: {summary}")
    lines.append(
        "- If you change selected packs later, regenerate `AGENTS.md`, "
        "`docs/ai/stack-guidance.md`, and `.codex/enhancer/manifest.toml` together."
    )
    return lines


def render_stack_guidance(selections: tuple[PackSelection, ...]) -> str:
    selected = [selection for selection in selections if selection.selected]
    lines = [
        "# Stack Guidance",
        "",
        "This file records the optional Codex Enhancer stack packs selected for this repository.",
        "",
    ]

    if not selected:
        lines.extend(
            [
                "No stack packs are selected yet.",
                "",
                "If this repository later adopts one of the shipped stack packs, update the installer selection and regenerate this file with the matching manifest.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.append(
        "Selected packs: "
        + ", ".join(f"`{selection.pack.name}`" for selection in selected)
    )
    lines.append("")

    for selection in selected:
        lines.extend(
            [
                f"## {selection.pack.label}",
                "",
                f"Pack id: `{selection.pack.name}`",
                "",
                (selection.pack.root / selection.pack.render.stack_guidance)
                .read_text(encoding="utf-8")
                .strip(),
                "",
                "### Review Notes",
                "",
                (selection.pack.root / selection.pack.render.review_notes)
                .read_text(encoding="utf-8")
                .strip(),
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _toml_string(value: str) -> str:
    return json.dumps(value)


def render_stack_pack_manifest(
    detections: tuple[PackDetection, ...],
    selected_packs: tuple[str, ...] = (),
) -> str:
    selected = tuple(selected_packs)
    selected_set = set(selected)
    lines = [
        "schema_version = 1",
        'enhancer_version = "2"',
        f"selected_packs = [{', '.join(_toml_string(item) for item in selected)}]",
        "",
    ]

    for detection in detections:
        lines.extend(
            [
                "[[detected_packs]]",
                f"name = {_toml_string(detection.pack.name)}",
                f"selected = {'true' if detection.pack.name in selected_set else 'false'}",
                f"recommended = {'true' if detection.recommended else 'false'}",
                f"detected = {'true' if detection.detected else 'false'}",
                f"reason = {_toml_string('; '.join(detection.reasons))}",
                "",
            ]
        )

    lines.extend(
        [
            "[generated_files]",
            'stack_guidance = "docs/ai/stack-guidance.md"',
        ]
    )
    return "\n".join(lines) + "\n"
