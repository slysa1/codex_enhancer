#!/usr/bin/env python3
"""Load, detect, and render optional stack packs for Codex Enhancer."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from codex_enhancer.package_assets import asset_path
from scripts.enhancer_spec import (
    ENHANCER_MANIFEST_SCHEMA_VERSION,
    ENHANCER_VERSION,
    MANAGED_SECTIONS,
    SUPPORTED_ENHANCER_MANIFEST_SCHEMA_VERSIONS,
)
from scripts.spec_kit_bridge import SpecKitBridgeConfig, SpecKitPaths
from scripts.utility_harness import (
    UTILITY_HARNESS_DEPENDENCY_POLICY,
    UtilityHarnessConfig,
)


STACK_PACK_ROOT = asset_path("scaffold/stack-packs")
TARGET_MANIFEST_PATH = Path(".codex/enhancer/manifest.toml")
PACKAGE_MANAGER_LOCKFILES = (
    (Path("pnpm-lock.yaml"), "pnpm"),
    (Path("yarn.lock"), "yarn"),
    (Path("bun.lockb"), "bun"),
    (Path("bun.lock"), "bun"),
    (Path("package-lock.json"), "npm"),
    (Path("npm-shrinkwrap.json"), "npm"),
)
SUPPORTED_PACKAGE_MANAGERS = frozenset({"npm", "pnpm", "yarn", "bun"})
PACKAGE_SCRIPT_HINTS_BY_PACK = {
    "javascript-typescript-app": ("build", "lint", "test", "dev", "check", "typecheck"),
    "frontend-ui": ("build", "dev", "preview", "test", "e2e"),
    "library-package": ("build", "lint", "test", "typecheck", "prepublishOnly", "prepare"),
    "node-api-service": ("start", "dev", "test", "build"),
}
PACKAGE_HINTS_BY_PACK = {
    "javascript-typescript-app": (
        "typescript",
        "vite",
        "next",
        "react",
        "eslint",
        "vitest",
        "jest",
        "tsx",
        "ts-node",
        "webpack",
        "rollup",
        "esbuild",
    ),
    "frontend-ui": (
        "react",
        "@vitejs/plugin-react",
        "vite",
        "next",
        "vue",
        "svelte",
        "astro",
        "solid-js",
        "@angular/core",
    ),
    "library-package": (
        "typescript",
        "tsup",
        "rollup",
        "vite",
        "unbuild",
        "microbundle",
        "esbuild",
        "changesets",
        "@changesets/cli",
    ),
    "node-api-service": (
        "express",
        "fastify",
        "koa",
        "hono",
        "@nestjs/core",
        "zod",
        "joi",
        "swagger-ui-express",
    ),
}
LIBRARY_PACKAGE_METADATA_FIELDS = ("exports", "main", "module", "types", "typings", "bin", "files")
LIBRARY_APP_SIGNAL_GLOBS = (
    "src/App.*",
    "app/**",
    "pages/**",
    "src/server.*",
    "src/routes/**/*",
    "src/controllers/**/*",
    "server/**/*",
    "api/**/*",
    "next.config.*",
    "astro.config.*",
    "svelte.config.*",
    "openapi*.json",
    "openapi*.yaml",
    "openapi*.yml",
)
PYPROJECT_TOOL_HINTS = ("pytest", "ruff", "mypy", "black", "poetry", "hatch", "uv")


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
class PackGuidance:
    use_when: tuple[str, ...]
    adds: tuple[str, ...]
    skip_when: tuple[str, ...]


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
    guidance: PackGuidance
    render: PackRender


@dataclass(frozen=True)
class PackageManagerSignal:
    name: str
    evidence: str
    is_default: bool


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


@dataclass(frozen=True)
class ManifestPackEvidence:
    name: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class EnhancerInstallState:
    enhancer_version: str | None
    selected_packs: tuple[str, ...]
    safe_to_regenerate: tuple[str, ...]
    adapt_manually: tuple[str, ...]
    schema_version: int | None = None
    lifecycle_state: str | None = None
    pack_selection_mode: str | None = None
    managed_sections: tuple[str, ...] = ()
    pack_evidence: tuple[ManifestPackEvidence, ...] = ()
    spec_kit_bridge: SpecKitBridgeConfig | None = None
    utility_harness: UtilityHarnessConfig | None = None


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


def _tuple_of_strings(data: dict[str, object], key: str) -> tuple[str, ...]:
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
    guidance = _required_section(raw, "guidance")
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
        guidance=PackGuidance(
            use_when=_tuple_of_strings(guidance, "use_when"),
            adds=_tuple_of_strings(guidance, "adds"),
            skip_when=_tuple_of_strings(guidance, "skip_when"),
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
    if not pack.guidance.use_when or not pack.guidance.adds or not pack.guidance.skip_when:
        raise ValueError(
            f"Stack pack {pack.name} must define guidance.use_when, guidance.adds, and guidance.skip_when."
        )
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


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def _read_toml_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}
    return raw


def _package_manager_name(package_manager: str) -> str | None:
    name = package_manager.split("@", 1)[0].strip().lower()
    if name in SUPPORTED_PACKAGE_MANAGERS:
        return name
    return None


def detect_package_manager(target: Path) -> PackageManagerSignal:
    resolved_target = target.resolve()
    package_data = _read_json_object(resolved_target / "package.json")
    package_manager = package_data.get("packageManager")
    if isinstance(package_manager, str):
        manager = _package_manager_name(package_manager)
        if manager is not None:
            return PackageManagerSignal(
                name=manager,
                evidence=f"package manager: {manager} from package.json packageManager",
                is_default=False,
            )

    for lockfile, manager in PACKAGE_MANAGER_LOCKFILES:
        if (resolved_target / lockfile).exists():
            return PackageManagerSignal(
                name=manager,
                evidence=f"package manager: {manager} from {lockfile.as_posix()}",
                is_default=False,
            )

    return PackageManagerSignal(
        name="npm",
        evidence="package manager: npm default because no packageManager or lockfile was found",
        is_default=True,
    )


def _package_scripts(package_data: dict[str, object], hints: tuple[str, ...]) -> tuple[str, ...]:
    scripts = package_data.get("scripts", {})
    if not isinstance(scripts, dict):
        return ()
    return tuple(name for name in hints if name in scripts)


def _package_names(package_data: dict[str, object]) -> frozenset[str]:
    names: set[str] = set()
    for section_name in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        section = package_data.get(section_name, {})
        if not isinstance(section, dict):
            continue
        names.update(name for name in section if isinstance(name, str))
    return frozenset(names)


def _matching_package_names(
    package_data: dict[str, object],
    hints: tuple[str, ...],
) -> tuple[str, ...]:
    names = _package_names(package_data)
    return tuple(name for name in hints if name in names)


def _collect_package_manifest_evidence(pack: StackPack, target: Path) -> tuple[str, ...]:
    if pack.name not in PACKAGE_SCRIPT_HINTS_BY_PACK and pack.name not in PACKAGE_HINTS_BY_PACK:
        return ()

    package_data = _read_json_object(target / "package.json")
    if not package_data:
        return ()

    evidence: list[str] = []
    package_manager = detect_package_manager(target)
    if not package_manager.is_default:
        evidence.append(package_manager.evidence)

    scripts = _package_scripts(package_data, PACKAGE_SCRIPT_HINTS_BY_PACK.get(pack.name, ()))
    if scripts:
        evidence.append(f"package.json scripts: {', '.join(scripts)}")

    packages = _matching_package_names(package_data, PACKAGE_HINTS_BY_PACK.get(pack.name, ()))
    if packages:
        evidence.append(f"package.json packages: {', '.join(packages)}")

    return tuple(evidence)


def _collect_pyproject_manifest_evidence(pack: StackPack, target: Path) -> tuple[str, ...]:
    if pack.name != "python-service":
        return ()

    pyproject_data = _read_toml_object(target / "pyproject.toml")
    if not pyproject_data:
        return ()

    evidence: list[str] = []
    build_system = pyproject_data.get("build-system", {})
    if isinstance(build_system, dict):
        build_backend = build_system.get("build-backend")
        if isinstance(build_backend, str) and build_backend.strip():
            evidence.append(f"pyproject build backend: {build_backend.strip()}")

    tool = pyproject_data.get("tool", {})
    if isinstance(tool, dict):
        tools = tuple(name for name in PYPROJECT_TOOL_HINTS if name in tool)
        if tools:
            evidence.append(f"pyproject tool tables: {', '.join(tools)}")

    return tuple(evidence)


def collect_manifest_evidence(pack: StackPack, target: Path) -> tuple[str, ...]:
    evidence = [
        *_collect_package_manifest_evidence(pack, target),
        *_collect_pyproject_manifest_evidence(pack, target),
    ]
    return tuple(dict.fromkeys(evidence))


def _has_package_metadata_value(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | dict):
        return bool(value)
    return value is not None


def _library_package_fields(package_data: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        field
        for field in LIBRARY_PACKAGE_METADATA_FIELDS
        if _has_package_metadata_value(package_data.get(field))
    )


def _library_app_signal_matches(target: Path) -> tuple[Path, ...]:
    return _existing_globs(target, LIBRARY_APP_SIGNAL_GLOBS)


def _detect_library_package(pack: StackPack, target: Path) -> PackDetection:
    package_data = _read_json_object(target / "package.json")
    if not package_data:
        return PackDetection(
            pack=pack,
            detected=False,
            recommended=False,
            reasons=("missing readable package.json library metadata",),
        )

    library_fields = _library_package_fields(package_data)
    if not library_fields:
        return PackDetection(
            pack=pack,
            detected=False,
            recommended=False,
            reasons=(
                "missing library package metadata from package.json fields "
                + ", ".join(LIBRARY_PACKAGE_METADATA_FIELDS),
            ),
        )

    app_signal_matches = _library_app_signal_matches(target)
    if app_signal_matches:
        return PackDetection(
            pack=pack,
            detected=False,
            recommended=False,
            reasons=(
                "app or service signals suppress library-package: "
                + _format_path_list(app_signal_matches),
            ),
        )

    reasons = [
        "found package.json",
        "package.json library fields: " + ", ".join(library_fields),
        *collect_manifest_evidence(pack, target),
    ]
    return PackDetection(
        pack=pack,
        detected=True,
        recommended=pack.ui.recommended_if_detected,
        reasons=tuple(dict.fromkeys(reasons)),
    )


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

    if pack.name == "library-package":
        return _detect_library_package(pack, resolved_target)

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
    reasons.extend(collect_manifest_evidence(pack, resolved_target))

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


def load_selected_packs_from_manifest(target: Path) -> tuple[str, ...]:
    return load_enhancer_install_state(target).selected_packs


def _manifest_string_list(
    target: Path,
    manifest_path: Path,
    owner: str,
    value: object,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(
            f"Target {target.resolve()} has an invalid {manifest_path.as_posix()}: "
            f"{owner} must be a list of strings."
        )
    return tuple(value)


def _manifest_optional_string(
    target: Path,
    manifest_path: Path,
    owner: str,
    value: object,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Target {target.resolve()} has an invalid {manifest_path.as_posix()}: "
            f"{owner} must be a non-empty string when present."
        )
    return value


def load_enhancer_install_state(target: Path) -> EnhancerInstallState:
    manifest_path = target.resolve() / TARGET_MANIFEST_PATH
    if not manifest_path.exists():
        raise ValueError(
            f"Target {target.resolve()} does not contain {TARGET_MANIFEST_PATH.as_posix()}; "
            "run a full enhancer install first."
        )

    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ValueError(
            f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: {error}"
        ) from error

    schema_version = manifest.get("schema_version")
    if schema_version is not None and not isinstance(schema_version, int):
        raise ValueError(
            f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
            "schema_version must be an integer when present."
        )
    if (
        schema_version is not None
        and schema_version not in SUPPORTED_ENHANCER_MANIFEST_SCHEMA_VERSIONS
    ):
        supported = ", ".join(str(item) for item in sorted(SUPPORTED_ENHANCER_MANIFEST_SCHEMA_VERSIONS))
        raise ValueError(
            f"Target {target.resolve()} has an unsupported {TARGET_MANIFEST_PATH.as_posix()} "
            f"schema_version {schema_version}; supported versions are: {supported}."
        )

    enhancer_version = manifest.get("enhancer_version")
    if enhancer_version is not None and (
        not isinstance(enhancer_version, str) or not enhancer_version.strip()
    ):
        raise ValueError(
            f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
            "enhancer_version must be a non-empty string when present."
        )

    selected_packs = _manifest_string_list(
        target,
        TARGET_MANIFEST_PATH,
        "selected_packs",
        manifest.get("selected_packs", []),
    )

    lifecycle_state: str | None = None
    pack_selection_mode: str | None = None
    managed_sections: tuple[str, ...] = ()
    lifecycle = manifest.get("lifecycle", {})
    if lifecycle == {}:
        pass
    elif not isinstance(lifecycle, dict):
        raise ValueError(
            f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
            "lifecycle must be a table when present."
        )
    else:
        raw_state = lifecycle.get("state")
        if raw_state is not None:
            if not isinstance(raw_state, str) or not raw_state.strip():
                raise ValueError(
                    f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
                    "lifecycle.state must be a non-empty string when present."
                )
            lifecycle_state = raw_state

        raw_pack_selection = lifecycle.get("pack_selection")
        if raw_pack_selection is not None:
            if not isinstance(raw_pack_selection, str) or not raw_pack_selection.strip():
                raise ValueError(
                    f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
                    "lifecycle.pack_selection must be a non-empty string when present."
                )
            pack_selection_mode = raw_pack_selection

        managed_sections = _manifest_string_list(
            target,
            TARGET_MANIFEST_PATH,
            "lifecycle.managed_sections",
            lifecycle.get("managed_sections", []),
        )

    managed_outputs = manifest.get("managed_outputs", {})
    if managed_outputs == {}:
        safe_to_regenerate: tuple[str, ...] = ()
        adapt_manually: tuple[str, ...] = ()
    elif not isinstance(managed_outputs, dict):
        raise ValueError(
            f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
            "managed_outputs must be a table when present."
        )
    else:
        safe_to_regenerate = _manifest_string_list(
            target,
            TARGET_MANIFEST_PATH,
            "managed_outputs.safe_to_regenerate",
            managed_outputs.get("safe_to_regenerate", []),
        )
        adapt_manually = _manifest_string_list(
            target,
            TARGET_MANIFEST_PATH,
            "managed_outputs.adapt_manually",
            managed_outputs.get("adapt_manually", []),
        )

    pack_evidence: list[ManifestPackEvidence] = []
    detected_packs = manifest.get("detected_packs", [])
    if detected_packs == []:
        pass
    elif not isinstance(detected_packs, list) or any(not isinstance(item, dict) for item in detected_packs):
        raise ValueError(
            f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
            "detected_packs must be an array of tables when present."
        )
    else:
        for item in detected_packs:
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(
                    f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
                    "each detected_packs entry must define a non-empty name."
                )
            evidence = _manifest_string_list(
                target,
                TARGET_MANIFEST_PATH,
                f"detected_packs.{name}.evidence",
                item.get("evidence", []),
            )
            pack_evidence.append(ManifestPackEvidence(name=name, evidence=evidence))

    spec_kit_bridge: SpecKitBridgeConfig | None = None
    integrations = manifest.get("integrations", {})
    if integrations == {}:
        pass
    elif not isinstance(integrations, dict):
        raise ValueError(
            f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
            "integrations must be a table when present."
        )
    else:
        raw_spec_kit = integrations.get("spec_kit")
        if raw_spec_kit is None:
            pass
        elif not isinstance(raw_spec_kit, dict):
            raise ValueError(
                f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
                "integrations.spec_kit must be a table when present."
            )
        else:
            raw_paths = raw_spec_kit.get("paths", {})
            if raw_paths == {}:
                paths = SpecKitPaths()
            elif not isinstance(raw_paths, dict):
                raise ValueError(
                    f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
                    "integrations.spec_kit.paths must be a table when present."
                )
            else:
                paths = SpecKitPaths(
                    specify_root=_manifest_optional_string(
                        target,
                        TARGET_MANIFEST_PATH,
                        "integrations.spec_kit.paths.specify_root",
                        raw_paths.get("specify_root"),
                    ),
                    specs_root=_manifest_optional_string(
                        target,
                        TARGET_MANIFEST_PATH,
                        "integrations.spec_kit.paths.specs_root",
                        raw_paths.get("specs_root"),
                    ),
                    prompts_root=_manifest_optional_string(
                        target,
                        TARGET_MANIFEST_PATH,
                        "integrations.spec_kit.paths.prompts_root",
                        raw_paths.get("prompts_root"),
                    ),
                    agents_root=_manifest_optional_string(
                        target,
                        TARGET_MANIFEST_PATH,
                        "integrations.spec_kit.paths.agents_root",
                        raw_paths.get("agents_root"),
                    ),
                    codex_skills_root=_manifest_optional_string(
                        target,
                        TARGET_MANIFEST_PATH,
                        "integrations.spec_kit.paths.codex_skills_root",
                        raw_paths.get("codex_skills_root"),
                    ),
                    context_file=_manifest_optional_string(
                        target,
                        TARGET_MANIFEST_PATH,
                        "integrations.spec_kit.paths.context_file",
                        raw_paths.get("context_file"),
                    ),
                    constitution=_manifest_optional_string(
                        target,
                        TARGET_MANIFEST_PATH,
                        "integrations.spec_kit.paths.constitution",
                        raw_paths.get("constitution"),
                    ),
                )

            spec_kit_bridge = SpecKitBridgeConfig(
                mode=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.mode",
                    raw_spec_kit.get("mode"),
                )
                or "off",
                state=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.state",
                    raw_spec_kit.get("state"),
                )
                or "absent",
                origin=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.origin",
                    raw_spec_kit.get("origin"),
                ),
                integration_key=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.integration_key",
                    raw_spec_kit.get("integration_key"),
                ),
                managed_by=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.managed_by",
                    raw_spec_kit.get("managed_by"),
                )
                or "spec-kit",
                script_type=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.script_type",
                    raw_spec_kit.get("script_type"),
                ),
                command_surface=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.command_surface",
                    raw_spec_kit.get("command_surface"),
                ),
                command_label=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.command_label",
                    raw_spec_kit.get("command_label"),
                ),
                cli_version=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.cli_version",
                    raw_spec_kit.get("cli_version"),
                ),
                available_commands=_manifest_string_list(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.available_commands",
                    raw_spec_kit.get("available_commands", []),
                ),
                evidence=_manifest_string_list(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.spec_kit.detection_evidence",
                    raw_spec_kit.get("detection_evidence", []),
                ),
                paths=paths,
            )

    utility_harness: UtilityHarnessConfig | None = None
    if integrations == {}:
        pass
    elif isinstance(integrations, dict):
        raw_utility = integrations.get("utility_harness")
        if raw_utility is None:
            pass
        elif not isinstance(raw_utility, dict):
            raise ValueError(
                f"Target {target.resolve()} has an invalid {TARGET_MANIFEST_PATH.as_posix()}: "
                "integrations.utility_harness must be a table when present."
            )
        else:
            utility_harness = UtilityHarnessConfig(
                mode=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.utility_harness.mode",
                    raw_utility.get("mode"),
                )
                or "off",
                state=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.utility_harness.state",
                    raw_utility.get("state"),
                )
                or "absent",
                managed_by=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.utility_harness.managed_by",
                    raw_utility.get("managed_by"),
                )
                or "codex-enhancer",
                requirements_file=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.utility_harness.requirements_file",
                    raw_utility.get("requirements_file"),
                ),
                docs_file=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.utility_harness.docs_file",
                    raw_utility.get("docs_file"),
                ),
                tool_files=_manifest_string_list(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.utility_harness.tool_files",
                    raw_utility.get("tool_files", []),
                ),
                dependency_policy=_manifest_optional_string(
                    target,
                    TARGET_MANIFEST_PATH,
                    "integrations.utility_harness.dependency_policy",
                    raw_utility.get("dependency_policy"),
                )
                or UTILITY_HARNESS_DEPENDENCY_POLICY,
            )

    return EnhancerInstallState(
        enhancer_version=enhancer_version,
        selected_packs=selected_packs,
        safe_to_regenerate=safe_to_regenerate,
        adapt_manually=adapt_manually,
        schema_version=schema_version,
        lifecycle_state=lifecycle_state,
        pack_selection_mode=pack_selection_mode,
        managed_sections=managed_sections,
        pack_evidence=tuple(pack_evidence),
        spec_kit_bridge=spec_kit_bridge,
        utility_harness=utility_harness,
    )


def resolve_manifest_pack_selection(
    detections: tuple[PackDetection, ...],
    *,
    selected_packs: tuple[str, ...],
) -> tuple[PackSelection, ...]:
    selected_set = set(selected_packs)
    unknown = sorted(selected_set - available_pack_names(detections))
    if unknown:
        names = ", ".join(unknown)
        raise ValueError(f"Unknown stack pack name(s) in target manifest: {names}")

    selections: list[PackSelection] = []
    for detection in detections:
        is_selected = detection.pack.name in selected_set
        selections.append(
            PackSelection(
                pack=detection.pack,
                detected=detection.detected,
                recommended=detection.recommended,
                reasons=detection.reasons,
                selected=is_selected,
                selection_source="manifest" if is_selected else "not-selected",
            )
        )
    return tuple(selections)


def resolve_managed_pack_selection(
    detections: tuple[PackDetection, ...],
    *,
    current_selected_packs: tuple[str, ...],
    add_packs: tuple[str, ...] = (),
    remove_packs: tuple[str, ...] = (),
    set_packs: tuple[str, ...] | None = None,
) -> tuple[PackSelection, ...]:
    available = available_pack_names(detections)
    current_set = set(current_selected_packs)
    add_set = set(add_packs)
    remove_set = set(remove_packs)

    unknown_current = sorted(current_set - available)
    if unknown_current:
        names = ", ".join(unknown_current)
        raise ValueError(f"Unknown stack pack name(s) in target manifest: {names}")

    if set_packs is not None and (add_set or remove_set):
        raise ValueError("--set-pack cannot be combined with --add-pack or --remove-pack.")

    if set_packs is not None:
        set_pack_set = set(set_packs)
        unknown = sorted(set_pack_set - available)
        if unknown:
            names = ", ".join(unknown)
            raise ValueError(f"Unknown stack pack name(s): {names}")
        final_set = set_pack_set
    else:
        overlap = add_set & remove_set
        if overlap:
            names = ", ".join(sorted(overlap))
            raise ValueError(f"Conflicting stack-pack management for: {names}")

        unknown = sorted((add_set | remove_set) - available)
        if unknown:
            names = ", ".join(unknown)
            raise ValueError(f"Unknown stack pack name(s): {names}")
        final_set = (current_set | add_set) - remove_set

    selections: list[PackSelection] = []
    for detection in detections:
        name = detection.pack.name
        selected = name in final_set

        if set_packs is not None:
            if selected:
                selection_source = "manage-set"
            elif name in current_set:
                selection_source = "manage-set-remove"
            else:
                selection_source = "not-selected"
        elif name in add_set:
            selection_source = "manage-add"
        elif name in remove_set:
            selection_source = "manage-remove"
        elif selected:
            selection_source = "manifest"
        else:
            selection_source = "not-selected"

        selections.append(
            PackSelection(
                pack=detection.pack,
                detected=detection.detected,
                recommended=detection.recommended,
                reasons=detection.reasons,
                selected=selected,
                selection_source=selection_source,
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
        "- If you change selected packs later, rerun the full installer preview for `AGENTS.md` "
        "changes and use `--refresh-generated` to re-render `docs/ai/stack-guidance.md` plus "
        "`.codex/enhancer/manifest.toml`."
    )
    return lines


def render_refresh_follow_up_lines(selections: tuple[PackSelection, ...]) -> list[str]:
    selected = [selection for selection in selections if selection.selected]
    lines = [
        "- Review the refreshed `docs/ai/stack-guidance.md` and `.codex/enhancer/manifest.toml` outputs.",
    ]
    if selected:
        selected_names = ", ".join(f"`{selection.pack.name}`" for selection in selected)
        lines.append(f"- Refreshed stack-pack guidance for: {selected_names}.")
        for selection in selected:
            summary = _render_compact_agents_summary(selection.pack)
            lines.append(f"- `{selection.pack.name}`: {summary}")
    else:
        lines.append("- No stack packs are currently selected in the target manifest.")
    lines.append(
        "- `AGENTS.md` and the rest of the scaffold stay untouched during refresh; "
        "rerun a full install preview if you need to update manual scaffold files."
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
    *,
    safe_to_regenerate: tuple[Path, ...] = (),
    adapt_manually: tuple[Path, ...] = (),
    spec_kit_bridge: SpecKitBridgeConfig | None = None,
    utility_harness: UtilityHarnessConfig | None = None,
) -> str:
    selected = tuple(selected_packs)
    selected_set = set(selected)
    lines = [
        f"schema_version = {ENHANCER_MANIFEST_SCHEMA_VERSION}",
        f'enhancer_version = "{ENHANCER_VERSION}"',
        f"selected_packs = [{', '.join(_toml_string(item) for item in selected)}]",
        "",
        "[lifecycle]",
        'state = "active"',
        'pack_selection = "manifest"',
        "managed_sections = ["
        + ", ".join(_toml_string(section.identifier) for section in MANAGED_SECTIONS)
        + "]",
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
                "evidence = ["
                + ", ".join(_toml_string(reason) for reason in detection.reasons)
                + "]",
                "",
            ]
        )

    lines.extend(
        [
            "[generated_files]",
            'stack_guidance = "docs/ai/stack-guidance.md"',
            'spec_kit_bridge = "docs/ai/spec-kit-bridge.md"',
            "",
            "[managed_outputs]",
            "safe_to_regenerate = ["
            + ", ".join(_toml_string(path.as_posix()) for path in safe_to_regenerate)
            + "]",
            "adapt_manually = ["
            + ", ".join(_toml_string(path.as_posix()) for path in adapt_manually)
            + "]",
        ]
    )

    if spec_kit_bridge is not None:
        lines.extend(
            [
                "",
                "[integrations.spec_kit]",
                f"mode = {_toml_string(spec_kit_bridge.mode)}",
                f"state = {_toml_string(spec_kit_bridge.state)}",
                f"managed_by = {_toml_string(spec_kit_bridge.managed_by)}",
            ]
        )
        if spec_kit_bridge.origin is not None:
            lines.append(f"origin = {_toml_string(spec_kit_bridge.origin)}")
        if spec_kit_bridge.integration_key is not None:
            lines.append(f"integration_key = {_toml_string(spec_kit_bridge.integration_key)}")
        if spec_kit_bridge.script_type is not None:
            lines.append(f"script_type = {_toml_string(spec_kit_bridge.script_type)}")
        if spec_kit_bridge.command_surface is not None:
            lines.append(f"command_surface = {_toml_string(spec_kit_bridge.command_surface)}")
        if spec_kit_bridge.command_label is not None:
            lines.append(f"command_label = {_toml_string(spec_kit_bridge.command_label)}")
        if spec_kit_bridge.cli_version is not None:
            lines.append(f"cli_version = {_toml_string(spec_kit_bridge.cli_version)}")
        lines.append(
            "available_commands = ["
            + ", ".join(_toml_string(command) for command in spec_kit_bridge.available_commands)
            + "]"
        )
        lines.append(
            "detection_evidence = ["
            + ", ".join(_toml_string(item) for item in spec_kit_bridge.evidence)
            + "]"
        )
        lines.extend(["", "[integrations.spec_kit.paths]"])
        if spec_kit_bridge.paths.specify_root is not None:
            lines.append(f"specify_root = {_toml_string(spec_kit_bridge.paths.specify_root)}")
        if spec_kit_bridge.paths.specs_root is not None:
            lines.append(f"specs_root = {_toml_string(spec_kit_bridge.paths.specs_root)}")
        if spec_kit_bridge.paths.prompts_root is not None:
            lines.append(f"prompts_root = {_toml_string(spec_kit_bridge.paths.prompts_root)}")
        if spec_kit_bridge.paths.agents_root is not None:
            lines.append(f"agents_root = {_toml_string(spec_kit_bridge.paths.agents_root)}")
        if spec_kit_bridge.paths.codex_skills_root is not None:
            lines.append(
                f"codex_skills_root = {_toml_string(spec_kit_bridge.paths.codex_skills_root)}"
            )
        if spec_kit_bridge.paths.context_file is not None:
            lines.append(f"context_file = {_toml_string(spec_kit_bridge.paths.context_file)}")
        if spec_kit_bridge.paths.constitution is not None:
            lines.append(f"constitution = {_toml_string(spec_kit_bridge.paths.constitution)}")

    if utility_harness is not None:
        lines.extend(
            [
                "",
                "[integrations.utility_harness]",
                f"mode = {_toml_string(utility_harness.mode)}",
                f"state = {_toml_string(utility_harness.state)}",
                f"managed_by = {_toml_string(utility_harness.managed_by)}",
                f"dependency_policy = {_toml_string(utility_harness.dependency_policy)}",
            ]
        )
        if utility_harness.requirements_file is not None:
            lines.append(
                f"requirements_file = {_toml_string(utility_harness.requirements_file)}"
            )
        if utility_harness.docs_file is not None:
            lines.append(f"docs_file = {_toml_string(utility_harness.docs_file)}")
        lines.append(
            "tool_files = ["
            + ", ".join(_toml_string(path) for path in utility_harness.tool_files)
            + "]"
        )
    return "\n".join(lines) + "\n"
