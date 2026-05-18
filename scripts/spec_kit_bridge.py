#!/usr/bin/env python3
"""Detect, resolve, and summarize optional official GitHub Spec Kit installs."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


CORE_COMMAND_ORDER = (
    "constitution",
    "specify",
    "clarify",
    "plan",
    "analyze",
    "tasks",
    "implement",
    "checklist",
    "taskstoissues",
)
PROMPT_SUFFIX = ".prompt.md"
AGENT_SUFFIX = ".agent.md"
SPEC_KIT_BRIDGE_MODES = ("off", "auto", "attach", "bootstrap")
SPEC_KIT_SCRIPT_OPTIONS = ("auto", "ps", "sh")
SPEC_KIT_COMMAND_SURFACE_OPTIONS = ("auto", "dollar", "slash")
SPEC_KIT_BRIDGE_SKILLS = (
    "spec-implement-bridge",
    "spec-sync-check",
    "spec-review-bridge",
)
DEFAULT_BOOTSTRAP_COMMANDS = CORE_COMMAND_ORDER[:7]
DEFAULT_SPEC_KIT_VERSION = "v0.8.3"
FEATURE_CORE_FILES = ("spec.md", "plan.md", "tasks.md")
FEATURE_SUPPORT_FILES = ("research.md", "data-model.md", "quickstart.md")
TASK_CHECKBOX_PATTERN = re.compile(r"^\s*[-*]\s+\[(?P<state>[ xX])\]\s+")
DEFAULT_SYNC_ARTIFACT_LIMIT = 60
DEFAULT_SYNC_CHANGED_PATH_LIMIT = 80
SPEC_KIT_CLI_TIMEOUT_SECONDS = 10
MULTI_INSTALL_SAFE_INTEGRATIONS = (
    "auggie",
    "claude",
    "codebuddy",
    "codex",
    "cursor-agent",
    "gemini",
    "iflow",
    "junie",
    "kilocode",
    "kimi",
    "qodercli",
    "qwen",
    "roo",
    "shai",
    "tabnine",
    "trae",
    "windsurf",
)
SPEC_KIT_MULTI_INSTALL_MIN_VERSION = (0, 8, 5)
SPEC_KIT_REVIEW_SAFETY_SUMMARY_LINES = (
    "- Cross-agent review context may include only relevant Spec Kit artifacts, reviewed diffs, implementation notes, and validation evidence; exclude secrets, credentials, raw environment values, and unrelated private content.",
    "- Peer CLI smoke tests, network calls, package installs, or sandbox escalation require separate operator approval; review-context approval is not shell or network approval.",
)


def default_spec_kit_script_type() -> str:
    return "ps" if os.name == "nt" else "sh"


@dataclass(frozen=True)
class SpecKitAddonSummary:
    kind: str
    name: str
    path: str
    status: str
    version: str | None = None
    description: str | None = None
    priority: str | None = None
    config_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpecKitPaths:
    specify_root: str | None = None
    specs_root: str | None = None
    prompts_root: str | None = None
    agents_root: str | None = None
    codex_skills_root: str | None = None
    script_root: str | None = None
    presets_root: str | None = None
    extensions_root: str | None = None
    generic_commands_root: str | None = None
    context_file: str | None = None
    constitution: str | None = None


@dataclass(frozen=True)
class SpecKitDetection:
    detected: bool
    integration: str | None
    command_surface: str | None
    command_label: str | None
    script_type: str | None
    version: str | None
    commands: tuple[str, ...]
    evidence: tuple[str, ...]
    paths: SpecKitPaths
    has_git_extension: bool = False
    default_integration: str | None = None
    installed_integrations: tuple[str, ...] = ()
    integration_settings_keys: tuple[str, ...] = ()
    generic_commands_dir: str | None = None
    branch_numbering: str | None = None
    presets: tuple[SpecKitAddonSummary, ...] = ()
    extensions: tuple[SpecKitAddonSummary, ...] = ()
    script_directory: str | None = None


@dataclass(frozen=True)
class SpecKitBridgeConfig:
    mode: str
    state: str
    origin: str | None
    integration_key: str | None
    managed_by: str
    script_type: str | None
    command_surface: str | None
    command_label: str | None
    cli_version: str | None
    available_commands: tuple[str, ...]
    evidence: tuple[str, ...]
    paths: SpecKitPaths
    bootstrap_command: tuple[str, ...] = ()

    @property
    def enabled(self) -> bool:
        return self.state in {"attached", "bootstrapped"}


@dataclass(frozen=True)
class SpecKitFeatureSummary:
    name: str
    path: str
    core_files: tuple[str, ...]
    missing_core_files: tuple[str, ...]
    support_files: tuple[str, ...]
    contract_file_count: int
    checklist_file_count: int
    task_total: int
    task_done: int
    task_open: int


@dataclass(frozen=True)
class SpecKitSyncReport:
    target: str
    feature_filter: str | None
    features: tuple[SpecKitFeatureSummary, ...]
    artifact_paths: tuple[str, ...]
    changed_paths: tuple[str, ...]
    notes: tuple[str, ...]
    git_base: str | None = None
    git_error: str | None = None


@dataclass(frozen=True)
class SpecKitCliDiagnostic:
    checked: bool
    executable: str
    executable_path: str | None
    version: str | None
    version_output: str | None
    feature_flags: tuple[str, ...]
    feature_payload: dict[str, object] | None
    integration_output: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class SpecKitDoctorReport:
    target: str
    detection: SpecKitDetection
    cli: SpecKitCliDiagnostic
    notes: tuple[str, ...]


def _read_json_object(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _read_bounded_text(path: Path, *, limit_bytes: int = 512 * 1024) -> str:
    try:
        with path.open("rb") as handle:
            raw = handle.read(limit_bytes + 1)
    except OSError:
        return ""
    return raw[:limit_bytes].decode("utf-8", errors="replace")


def _string_value(data: dict[str, object] | None, key: str) -> str | None:
    if not data:
        return None
    value = data.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _first_string_value(data: dict[str, object] | None, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _string_value(data, key)
        if value:
            return value
    return None


def _string_sequence_value(data: dict[str, object] | None, key: str) -> tuple[str, ...]:
    if not data:
        return ()
    value = data.get(key)
    if isinstance(value, str):
        pieces = value.split(",") if "," in value else (value,)
    elif isinstance(value, (list, tuple, set)):
        pieces = value
    elif isinstance(value, dict):
        pieces = value.keys()
    else:
        return ()

    normalized: list[str] = []
    for item in pieces:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if stripped and stripped not in normalized:
            normalized.append(stripped)
    return tuple(normalized)


def _mapping_value(data: dict[str, object] | None, key: str) -> dict[str, object]:
    if not data:
        return {}
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _relative_if_exists(root: Path, relative_path: str) -> str | None:
    return relative_path if (root / relative_path).exists() else None


def _normalize_recorded_path(root: Path, value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    candidate = Path(stripped).expanduser()
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(root).as_posix()
        except (OSError, ValueError):
            return candidate.as_posix()
    normalized = stripped.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/") or None


def _script_directory_for_type(script_type: str | None) -> str | None:
    if script_type == "ps":
        return ".specify/scripts/powershell"
    if script_type == "sh":
        return ".specify/scripts/bash"
    return None


def _metadata_value_as_string(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        stripped = str(value).strip()
        return stripped or None
    return None


def _read_simple_metadata(path: Path) -> dict[str, object]:
    json_data = _read_json_object(path)
    if json_data is not None:
        return json_data

    text = _read_bounded_text(path, limit_bytes=64 * 1024)
    metadata: dict[str, object] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*[:=]\s*(.+?)\s*$", line)
        if match is None:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip().strip("\"'")
        if value.lower() == "true":
            metadata[key] = True
        elif value.lower() == "false":
            metadata[key] = False
        else:
            metadata[key] = value
    return metadata


def _metadata_file_for_addon(path: Path, kind: str) -> Path | None:
    if path.is_file():
        return path
    if not path.is_dir():
        return None
    candidates = (
        f"{kind}.json",
        f"{kind}.yml",
        f"{kind}.yaml",
        f"{kind}.toml",
        "metadata.json",
        "metadata.yml",
        "metadata.yaml",
        "manifest.json",
        f"{path.name}.json",
        f"{path.name}.yml",
        f"{path.name}.yaml",
    )
    for name in candidates:
        candidate = path / name
        if candidate.is_file():
            return candidate
    return None


def _addon_status(metadata: dict[str, object]) -> str:
    enabled = metadata.get("enabled")
    if enabled is False:
        return "disabled"
    disabled = metadata.get("disabled")
    if disabled is True:
        return "disabled"
    status = _metadata_value_as_string(metadata, "status")
    if status:
        return status.lower()
    return "enabled"


def _addon_config_files(root: Path, addon_path: Path, name: str, *, limit: int = 8) -> tuple[str, ...]:
    if not addon_path.is_dir():
        return ()
    config_files: list[str] = []
    suffixes = (".yml", ".yaml", ".json", ".toml")
    for path in sorted(addon_path.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        lowered = path.name.lower()
        if "config" not in lowered and lowered not in {"settings.yml", "settings.yaml", "settings.json"}:
            continue
        try:
            config_files.append(path.relative_to(root).as_posix())
        except ValueError:
            config_files.append(path.as_posix())
        if len(config_files) >= limit:
            break

    sibling_prefix = f"{name}-config"
    for path in sorted(addon_path.parent.glob(f"{sibling_prefix}.*")):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        try:
            rendered = path.relative_to(root).as_posix()
        except ValueError:
            rendered = path.as_posix()
        if rendered not in config_files:
            config_files.append(rendered)
        if len(config_files) >= limit:
            break
    return tuple(config_files)


def _collect_addons(root: Path, kind: str) -> tuple[SpecKitAddonSummary, ...]:
    directory = root / ".specify" / f"{kind}s"
    if not directory.is_dir():
        return ()

    summaries: list[SpecKitAddonSummary] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
        if path.name.startswith("."):
            continue
        if path.is_file() and (
            path.suffix.lower() not in {".json", ".yml", ".yaml", ".toml"}
            or "-config" in path.stem.lower()
        ):
            continue
        metadata_path = _metadata_file_for_addon(path, kind)
        metadata = _read_simple_metadata(metadata_path) if metadata_path is not None else {}
        name = (
            _metadata_value_as_string(metadata, "id")
            or _metadata_value_as_string(metadata, "name")
            or path.stem
        )
        try:
            relative_path = path.relative_to(root).as_posix()
        except ValueError:
            relative_path = path.as_posix()
        summaries.append(
            SpecKitAddonSummary(
                kind=kind,
                name=name,
                path=relative_path,
                status=_addon_status(metadata),
                version=_metadata_value_as_string(metadata, "version"),
                description=_metadata_value_as_string(metadata, "description"),
                priority=_metadata_value_as_string(metadata, "priority"),
                config_files=_addon_config_files(root, path, name),
            )
        )
    return tuple(summaries)


def _integration_settings(integration_data: dict[str, object] | None) -> dict[str, object]:
    return _mapping_value(integration_data, "integration_settings")


def _generic_commands_dir(
    root: Path,
    integration_data: dict[str, object] | None,
    init_options: dict[str, object] | None,
) -> str | None:
    settings = _integration_settings(integration_data)
    generic_settings = settings.get("generic")
    generic_mapping = generic_settings if isinstance(generic_settings, dict) else {}
    for data in (generic_mapping, init_options):
        value = _first_string_value(
            data,
            ("commands_dir", "commands-dir", "commandsDirectory", "commandsDir"),
        )
        normalized = _normalize_recorded_path(root, value)
        if normalized:
            return normalized
    return None


def _multi_install_status(integration: str) -> str:
    key = integration.strip().lower()
    if key in MULTI_INSTALL_SAFE_INTEGRATIONS:
        return "multi-install safe"
    if key == "generic":
        return "requires explicit official `--force` for multi-install"
    return "multi-install safety unknown"


def _parse_version_tuple(version: str | None) -> tuple[int, ...] | None:
    if not version:
        return None
    match = re.search(r"v?(\d+)\.(\d+)(?:\.(\d+))?", version)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups(default="0"))


def _extract_cli_version(output: str | None) -> str | None:
    if not output:
        return None
    lines = output.splitlines()
    for line in lines:
        lowered = line.lower()
        if "spec" not in lowered and "specify" not in lowered:
            continue
        match = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", line)
        if match:
            return match.group(1)
    match = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", output)
    return match.group(1) if match else None


def _feature_flags_from_payload(payload: object) -> tuple[str, ...]:
    if isinstance(payload, dict):
        features = payload.get("features")
        if isinstance(features, dict):
            return tuple(sorted(str(key) for key, enabled in features.items() if enabled is not False))
        if isinstance(features, list):
            return tuple(str(item) for item in features if isinstance(item, str))
        return tuple(
            sorted(
                str(key)
                for key, value in payload.items()
                if isinstance(value, bool) and value
            )
        )
    if isinstance(payload, list):
        return tuple(str(item) for item in payload if isinstance(item, str))
    return ()


def _run_specify_command(
    executable_path: str,
    args: tuple[str, ...],
    *,
    cwd: Path,
) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            [executable_path, *args],
            cwd=cwd,
            capture_output=True,
            check=False,
            text=True,
            timeout=SPEC_KIT_CLI_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return (None, f"`{executable_path}` was not found")
    except subprocess.TimeoutExpired:
        return (None, f"`specify {' '.join(args)}` timed out after {SPEC_KIT_CLI_TIMEOUT_SECONDS} seconds")
    except OSError as error:
        return (None, f"`specify {' '.join(args)}` could not run: {error}")

    output = "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part and part.strip()
    )
    if result.returncode != 0:
        detail = output or f"exit code {result.returncode}"
        return (None, f"`specify {' '.join(args)}` failed: {detail}")
    return (output, None)


def _resolve_executable_path(executable: str) -> str | None:
    candidate = Path(executable).expanduser()
    if candidate.exists():
        try:
            return str(candidate.resolve())
        except OSError:
            return str(candidate)
    return shutil.which(executable)


def _collect_prompt_or_agent_commands(directory: Path, suffix: str) -> tuple[str, ...]:
    if not directory.is_dir():
        return ()
    commands: list[str] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        name = path.name
        if not name.startswith("speckit.") or not name.endswith(suffix):
            continue
        commands.append(name[len("speckit.") : -len(suffix)])
    return tuple(commands)


def _collect_codex_skill_commands(directory: Path) -> tuple[str, ...]:
    if not directory.is_dir():
        return ()
    commands: list[str] = []
    for path in sorted(directory.iterdir()):
        if not path.is_dir():
            continue
        name = path.name
        if not name.startswith("speckit-"):
            continue
        commands.append(name[len("speckit-") :].replace("-", "."))
    return tuple(commands)


def _ordered_commands(commands: tuple[str, ...]) -> tuple[str, ...]:
    unique = tuple(dict.fromkeys(command for command in commands if command))
    if not unique:
        return ()
    extras = sorted(command for command in unique if command not in CORE_COMMAND_ORDER)
    core = tuple(command for command in CORE_COMMAND_ORDER if command in unique)
    return core + tuple(command for command in extras if command not in core)


def _count_files_bounded(directory: Path, *, limit: int = 100) -> int:
    if not directory.is_dir():
        return 0
    count = 0
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        count += 1
        if count >= limit:
            return count
    return count


def _list_files_bounded(directory: Path, *, limit: int = 25) -> tuple[Path, ...]:
    if not directory.is_dir():
        return ()
    paths: list[Path] = []
    for path in sorted(directory.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file():
            continue
        paths.append(path)
        if len(paths) >= limit:
            break
    return tuple(paths)


def _count_task_checkboxes(path: Path) -> tuple[int, int, int]:
    if not path.is_file():
        return (0, 0, 0)

    total = 0
    done = 0
    for line in _read_bounded_text(path).splitlines():
        match = TASK_CHECKBOX_PATTERN.match(line)
        if match is None:
            continue
        total += 1
        if match.group("state").lower() == "x":
            done += 1
    return (total, done, total - done)


def _feature_matches(name: str, requested: str | None) -> bool:
    if requested is None:
        return True
    wanted = requested.strip().lower()
    if not wanted:
        return True
    lowered = name.lower()
    if lowered == wanted:
        return True
    numeric_prefix = lowered.split("-", 1)[0]
    return numeric_prefix == wanted


def summarize_spec_kit_feature(feature_dir: Path, target: Path) -> SpecKitFeatureSummary:
    core_files = tuple(name for name in FEATURE_CORE_FILES if (feature_dir / name).is_file())
    support_files = tuple(
        name for name in FEATURE_SUPPORT_FILES if (feature_dir / name).is_file()
    )
    missing_core_files = tuple(name for name in FEATURE_CORE_FILES if name not in core_files)
    task_total, task_done, task_open = _count_task_checkboxes(feature_dir / "tasks.md")
    return SpecKitFeatureSummary(
        name=feature_dir.name,
        path=feature_dir.relative_to(target).as_posix(),
        core_files=core_files,
        missing_core_files=missing_core_files,
        support_files=support_files,
        contract_file_count=_count_files_bounded(feature_dir / "contracts"),
        checklist_file_count=_count_files_bounded(feature_dir / "checklists"),
        task_total=task_total,
        task_done=task_done,
        task_open=task_open,
    )


def discover_spec_kit_features(
    target: Path,
    *,
    feature: str | None = None,
    max_features: int = 20,
) -> tuple[SpecKitFeatureSummary, ...]:
    root = target.resolve()
    specs_root = root / "specs"
    if not specs_root.is_dir():
        return ()

    summaries: list[SpecKitFeatureSummary] = []
    for path in sorted(specs_root.iterdir(), key=lambda item: item.name.lower()):
        if len(summaries) >= max_features:
            break
        if not path.is_dir() or path.name.startswith("."):
            continue
        if not _feature_matches(path.name, feature):
            continue
        summaries.append(summarize_spec_kit_feature(path, root))
    return tuple(summaries)


def _normalize_changed_path(root: Path, path: str) -> str | None:
    stripped = path.strip()
    if not stripped:
        return None

    candidate = Path(stripped).expanduser()
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(root).as_posix()
        except (OSError, ValueError):
            return candidate.as_posix()

    normalized = stripped.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.strip("/")
    return normalized or None


def _normalize_changed_paths(root: Path, changed_paths: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    normalized_paths: list[str] = []
    for changed_path in changed_paths:
        normalized = _normalize_changed_path(root, changed_path)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        normalized_paths.append(normalized)
    return tuple(normalized_paths)


def collect_spec_kit_changed_paths_from_git(
    target: Path,
    *,
    base: str,
) -> tuple[tuple[str, ...], str | None]:
    root = target.resolve()
    base_ref = base.strip()
    if not base_ref:
        return ((), "no git base ref was supplied")

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=root,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return ((), "git executable was not found")
    except subprocess.TimeoutExpired:
        return ((), f"git diff against {base_ref!r} timed out")
    except OSError as error:
        return ((), f"git diff could not run: {error}")

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        return ((), f"git diff against {base_ref!r} failed: {detail}")

    paths = tuple(line.strip() for line in result.stdout.splitlines() if line.strip())
    return (_normalize_changed_paths(root, paths), None)


def _collect_feature_artifact_paths(
    root: Path,
    feature: SpecKitFeatureSummary,
    *,
    limit: int = DEFAULT_SYNC_ARTIFACT_LIMIT,
) -> tuple[str, ...]:
    feature_dir = root / feature.path
    artifacts: list[str] = []

    for name in (*FEATURE_CORE_FILES, *FEATURE_SUPPORT_FILES):
        path = feature_dir / name
        if path.is_file():
            artifacts.append(path.relative_to(root).as_posix())

    for directory_name in ("contracts", "checklists"):
        for path in _list_files_bounded(feature_dir / directory_name, limit=limit):
            artifacts.append(path.relative_to(root).as_posix())
            if len(artifacts) >= limit:
                return tuple(artifacts)

    return tuple(artifacts[:limit])


def _classify_changed_path(path: str) -> str:
    lowered = path.lower()
    normalized = lowered.replace("\\", "/")
    name = Path(normalized).name

    if normalized.startswith(("specs/", ".specify/")):
        return "Spec Kit artifacts"
    if normalized.startswith(("tests/", "test/")) or "/tests/" in normalized:
        return "tests"
    if name.startswith("test_") or name.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
        return "tests"
    if any(token in normalized for token in ("contract", "openapi", "schema", "graphql")):
        return "contracts/API"
    if normalized.startswith(("docs/", "readme")):
        return "docs"
    return "source"


def _format_changed_path_categories(changed_paths: tuple[str, ...]) -> str:
    categories: dict[str, int] = {}
    for changed_path in changed_paths:
        category = _classify_changed_path(changed_path)
        categories[category] = categories.get(category, 0) + 1
    return ", ".join(f"{name}: {count}" for name, count in sorted(categories.items()))


def build_spec_kit_sync_report(
    target: Path,
    *,
    feature: str | None = None,
    changed_paths: tuple[str, ...] = (),
    git_base: str | None = None,
    max_features: int = 20,
) -> SpecKitSyncReport:
    root = target.resolve()
    detection = detect_spec_kit(root)
    normalized_changed_paths = _normalize_changed_paths(root, changed_paths)
    git_changed_paths: tuple[str, ...] = ()
    git_error: str | None = None
    if git_base:
        git_changed_paths, git_error = collect_spec_kit_changed_paths_from_git(
            root,
            base=git_base,
        )
        normalized_changed_paths = _normalize_changed_paths(
            root,
            normalized_changed_paths + git_changed_paths,
        )

    features = discover_spec_kit_features(root, feature=feature, max_features=max_features)
    artifact_paths: list[str] = []
    for feature_summary in features:
        for artifact_path in _collect_feature_artifact_paths(root, feature_summary):
            if artifact_path not in artifact_paths:
                artifact_paths.append(artifact_path)

    notes: list[str] = []
    if git_base and git_error is None:
        notes.append(f"Changed paths include local git diff names from `{git_base}...HEAD`.")
    if git_error:
        notes.append(f"Git diff unavailable: {git_error}.")

    if not features:
        if not (root / "specs").is_dir():
            notes.append("No `specs/` directory was found.")
        elif feature:
            notes.append("No feature directory matched the requested filter.")
        else:
            notes.append("No feature directories were found under `specs/`.")
    elif feature is None and len(features) > 1:
        notes.append("Multiple feature directories matched; pass `--feature` to focus the sync report.")

    for feature_summary in features:
        if feature_summary.missing_core_files:
            missing = ", ".join(f"`{name}`" for name in feature_summary.missing_core_files)
            notes.append(f"`{feature_summary.name}` is missing core artifact(s): {missing}.")
        if feature_summary.task_open:
            notes.append(f"`{feature_summary.name}` still has {feature_summary.task_open} open task(s).")
        if feature_summary.contract_file_count and normalized_changed_paths:
            notes.append(f"`{feature_summary.name}` has contracts; re-read them before reviewing API or client changes.")
        if "quickstart.md" in feature_summary.support_files and normalized_changed_paths:
            notes.append(f"`{feature_summary.name}` has `quickstart.md`; re-check it when validation behavior changes.")

    if not normalized_changed_paths:
        notes.append("No changed paths were supplied; use `--changed` or `--base` for code-to-spec sync cues.")
    else:
        notes.append(f"Changed path categories: {_format_changed_path_categories(normalized_changed_paths)}.")
        if any(_classify_changed_path(path) == "Spec Kit artifacts" for path in normalized_changed_paths):
            notes.append("Spec Kit-owned files appear in the changed paths; this enhancer report remains read-only.")
        if not any(_classify_changed_path(path) == "tests" for path in normalized_changed_paths):
            notes.append("No obvious test paths were supplied; verify whether the feature tasks require validation updates.")

    if not (root / ".git").is_dir():
        notes.append(
            "No `.git/` directory was found; official Spec Kit feature scripts may need `SPECIFY_FEATURE` for non-Git repositories."
        )
    elif not detection.has_git_extension:
        notes.append(
            "Spec Kit git extension was not detected; add or remove it with official Spec Kit extension commands, not the enhancer."
        )
    if detection.branch_numbering:
        notes.append(f"Spec Kit branch numbering hint: `{detection.branch_numbering}`.")
    if detection.presets:
        notes.append(
            f"Detected {len(detection.presets)} local Spec Kit preset(s); review preset precedence before judging generated artifacts."
        )
    if detection.extensions:
        notes.append(
            f"Detected {len(detection.extensions)} local Spec Kit extension(s); review extension commands, gates, and config before review."
        )

    return SpecKitSyncReport(
        target=root.as_posix(),
        feature_filter=feature,
        features=features,
        artifact_paths=tuple(artifact_paths[:DEFAULT_SYNC_ARTIFACT_LIMIT]),
        changed_paths=normalized_changed_paths[:DEFAULT_SYNC_CHANGED_PATH_LIMIT],
        notes=tuple(notes),
        git_base=git_base,
        git_error=git_error,
    )


def _resolve_command_surface(
    *,
    integration: str | None,
    has_prompt_or_agent_surface: bool,
    has_codex_skill_surface: bool,
) -> tuple[str | None, str | None]:
    if has_prompt_or_agent_surface and has_codex_skill_surface:
        return ("mixed", "multiple official Spec Kit surfaces detected")
    if has_codex_skill_surface:
        return ("codex-skills", "$speckit-<command>")
    if has_prompt_or_agent_surface:
        return ("github-prompts-agents", ".github/prompts and .github/agents")
    if integration == "codex":
        return ("codex-skills", "$speckit-<command>")
    if integration == "copilot":
        return ("github-prompts-agents", ".github/prompts and .github/agents")
    if integration:
        return (integration, f"official {integration} integration")
    return (None, None)


def _bridge_surface_from_detection(detection: SpecKitDetection) -> tuple[str | None, str | None]:
    if detection.command_surface == "codex-skills":
        return ("dollar", "$speckit-<command>")
    if detection.command_surface == "github-prompts-agents":
        return ("slash", "/prompts:speckit.<command>")
    if detection.command_surface == "mixed":
        return ("mixed", "multiple official Spec Kit surfaces detected")
    return (None, None)


def _bridge_surface_from_preference(
    preference: str,
    detection: SpecKitDetection,
) -> tuple[str | None, str | None]:
    if preference == "dollar":
        return ("dollar", "$speckit-<command>")
    if preference == "slash":
        return ("slash", "/prompts:speckit.<command>")
    resolved_surface, resolved_label = _bridge_surface_from_detection(detection)
    if resolved_surface or resolved_label:
        return (resolved_surface, resolved_label)
    return ("dollar", "$speckit-<command>")


def build_spec_kit_bootstrap_command(
    *,
    script_type: str,
    version: str,
    executable: str | None = None,
) -> tuple[str, ...]:
    if executable:
        return (
            executable,
            "init",
            "--here",
            "--integration",
            "codex",
            "--script",
            script_type,
        )
    return (
        "uvx",
        "--from",
        f"git+https://github.com/github/spec-kit.git@{version}",
        "specify",
        "init",
        "--here",
        "--integration",
        "codex",
        "--script",
        script_type,
    )


def _format_installed_integrations(detection: SpecKitDetection) -> str:
    default_key = detection.default_integration or detection.integration
    rendered: list[str] = []
    for integration in detection.installed_integrations:
        qualifiers = []
        if default_key and integration == default_key:
            qualifiers.append("default")
        qualifiers.append(_multi_install_status(integration))
        rendered.append(f"`{integration}` ({', '.join(qualifiers)})")
    return ", ".join(rendered)


def _format_addons(addons: tuple[SpecKitAddonSummary, ...]) -> str:
    rendered: list[str] = []
    for addon in addons:
        qualifiers = [addon.status]
        if addon.version:
            qualifiers.append(f"v{addon.version}")
        if addon.priority:
            qualifiers.append(f"priority {addon.priority}")
        if addon.config_files:
            qualifiers.append(f"{len(addon.config_files)} config file(s)")
        rendered.append(f"`{addon.name}` ({', '.join(qualifiers)})")
    return ", ".join(rendered)


def detect_spec_kit(target: Path) -> SpecKitDetection:
    root = target.resolve()
    integration_data = _read_json_object(root / ".specify/integration.json")
    init_options = _read_json_object(root / ".specify/init-options.json")

    prompt_commands = _collect_prompt_or_agent_commands(root / ".github/prompts", PROMPT_SUFFIX)
    agent_commands = _collect_prompt_or_agent_commands(root / ".github/agents", AGENT_SUFFIX)
    codex_skill_commands = _collect_codex_skill_commands(root / ".agents/skills")

    default_integration = (
        _string_value(integration_data, "default_integration")
        or _string_value(init_options, "default_integration")
    )
    legacy_integration = (
        _string_value(init_options, "integration")
        or _string_value(init_options, "ai")
        or _string_value(integration_data, "integration")
    )
    integration = default_integration or legacy_integration
    installed_integrations = (
        _string_sequence_value(integration_data, "installed_integrations")
        or _string_sequence_value(init_options, "installed_integrations")
    )
    if integration and integration not in installed_integrations:
        installed_integrations = (integration, *installed_integrations)
    integration_settings_keys = tuple(sorted(_integration_settings(integration_data).keys()))
    version = _string_value(init_options, "speckit_version") or _string_value(
        integration_data, "version"
    )
    script_type = _string_value(init_options, "script")
    script_directory = _script_directory_for_type(script_type)
    generic_commands_dir = _generic_commands_dir(root, integration_data, init_options)
    branch_numbering = (
        _first_string_value(init_options, ("branch_numbering", "branch-numbering"))
        or _first_string_value(integration_data, ("branch_numbering", "branch-numbering"))
    )
    presets = _collect_addons(root, "preset")
    extensions = _collect_addons(root, "extension")
    has_prompt_or_agent_surface = bool(prompt_commands or agent_commands)
    has_codex_skill_surface = bool(codex_skill_commands)
    command_surface, command_label = _resolve_command_surface(
        integration=integration,
        has_prompt_or_agent_surface=has_prompt_or_agent_surface,
        has_codex_skill_surface=has_codex_skill_surface,
    )

    paths = SpecKitPaths(
        specify_root=_relative_if_exists(root, ".specify"),
        specs_root=_relative_if_exists(root, "specs"),
        prompts_root=(
            ".github/prompts" if has_prompt_or_agent_surface and (root / ".github/prompts").is_dir() else None
        ),
        agents_root=(
            ".github/agents" if has_prompt_or_agent_surface and (root / ".github/agents").is_dir() else None
        ),
        codex_skills_root=".agents/skills" if has_codex_skill_surface else None,
        script_root=(
            script_directory
            if script_directory and (root / script_directory).is_dir()
            else _relative_if_exists(root, ".specify/scripts")
        ),
        presets_root=_relative_if_exists(root, ".specify/presets"),
        extensions_root=_relative_if_exists(root, ".specify/extensions"),
        generic_commands_root=(
            generic_commands_dir
            if generic_commands_dir and (root / generic_commands_dir).exists()
            else None
        ),
        context_file=_string_value(init_options, "context_file"),
        constitution=_relative_if_exists(root, ".specify/memory/constitution.md"),
    )

    detected = any(
        (
            paths.specify_root,
            paths.specs_root,
            paths.prompts_root,
            paths.agents_root,
            paths.codex_skills_root,
            paths.presets_root,
            paths.extensions_root,
        )
    )
    commands = _ordered_commands(prompt_commands + agent_commands + codex_skill_commands)
    has_git_extension = (root / ".specify/extensions/git").is_dir()

    evidence: list[str] = []
    if paths.specify_root:
        evidence.append("found .specify/")
    if paths.specs_root:
        evidence.append("found specs/")
    if paths.prompts_root:
        evidence.append("found Spec Kit prompt files under .github/prompts/")
    if paths.agents_root:
        evidence.append("found Spec Kit agent files under .github/agents/")
    if paths.codex_skills_root:
        evidence.append("found Spec Kit skills under .agents/skills/")
    if integration:
        evidence.append(f"integration: {integration}")
    if default_integration:
        evidence.append(f"default integration: {default_integration}")
    if installed_integrations:
        evidence.append("installed integrations: " + ", ".join(installed_integrations))
    if integration_settings_keys:
        evidence.append("integration settings: " + ", ".join(integration_settings_keys))
    if script_type:
        evidence.append(f"script type: {script_type}")
    if script_directory:
        evidence.append(f"script directory: {script_directory}")
    if version:
        evidence.append(f"Spec Kit version: {version}")
    if generic_commands_dir:
        evidence.append(f"generic commands dir: {generic_commands_dir}")
    if branch_numbering:
        evidence.append(f"branch numbering: {branch_numbering}")
    if presets:
        evidence.append(f"presets detected: {len(presets)}")
    if extensions:
        evidence.append(f"extensions detected: {len(extensions)}")
    if has_git_extension:
        evidence.append("git extension hooks configured")

    return SpecKitDetection(
        detected=detected,
        integration=integration,
        command_surface=command_surface,
        command_label=command_label,
        script_type=script_type,
        version=version,
        commands=commands,
        evidence=tuple(evidence),
        paths=paths,
        has_git_extension=has_git_extension,
        default_integration=default_integration,
        installed_integrations=installed_integrations,
        integration_settings_keys=integration_settings_keys,
        generic_commands_dir=generic_commands_dir,
        branch_numbering=branch_numbering,
        presets=presets,
        extensions=extensions,
        script_directory=script_directory,
    )


def resolve_spec_kit_bridge(
    target: Path,
    *,
    mode: str = "auto",
    script_type: str = "auto",
    command_surface: str = "auto",
    version: str | None = None,
    executable: str | None = None,
    detection: SpecKitDetection | None = None,
    existing_bridge: SpecKitBridgeConfig | None = None,
) -> SpecKitBridgeConfig:
    if mode not in SPEC_KIT_BRIDGE_MODES:
        choices = ", ".join(SPEC_KIT_BRIDGE_MODES)
        raise ValueError(f"Unknown Spec Kit bridge mode {mode!r}. Expected one of: {choices}.")
    if script_type not in SPEC_KIT_SCRIPT_OPTIONS:
        choices = ", ".join(SPEC_KIT_SCRIPT_OPTIONS)
        raise ValueError(
            f"Unknown Spec Kit script type {script_type!r}. Expected one of: {choices}."
        )
    if command_surface not in SPEC_KIT_COMMAND_SURFACE_OPTIONS:
        choices = ", ".join(SPEC_KIT_COMMAND_SURFACE_OPTIONS)
        raise ValueError(
            f"Unknown Spec Kit command surface {command_surface!r}. Expected one of: {choices}."
        )

    detection = detection or detect_spec_kit(target)
    resolved_mode = "attach" if mode == "auto" and detection.detected else "off" if mode == "auto" else mode

    if resolved_mode == "off":
        detected_surface, detected_label = _bridge_surface_from_detection(detection)
        return SpecKitBridgeConfig(
            mode="off",
            state="absent",
            origin=None,
            integration_key=detection.integration,
            managed_by="spec-kit",
            script_type=detection.script_type,
            command_surface=detected_surface,
            command_label=detected_label,
            cli_version=detection.version,
            available_commands=detection.commands,
            evidence=detection.evidence,
            paths=detection.paths,
        )

    if resolved_mode == "attach":
        if not detection.detected:
            raise ValueError(
                "Spec Kit bridge mode 'attach' requires an existing official Spec Kit install in the target repo."
            )
        resolved_script = (
            default_spec_kit_script_type()
            if script_type == "auto" and detection.script_type is None
            else detection.script_type
            if script_type == "auto"
            else script_type
        )
        resolved_surface, resolved_label = _bridge_surface_from_preference(command_surface, detection)
        return SpecKitBridgeConfig(
            mode="attach",
            state="attached",
            origin="preexisting",
            integration_key=detection.integration or "codex",
            managed_by="spec-kit",
            script_type=resolved_script,
            command_surface=resolved_surface,
            command_label=resolved_label,
            cli_version=detection.version or version,
            available_commands=detection.commands or DEFAULT_BOOTSTRAP_COMMANDS,
            evidence=detection.evidence,
            paths=detection.paths,
        )

    if (
        detection.detected
        and existing_bridge is not None
        and existing_bridge.state == "bootstrapped"
        and existing_bridge.mode == "bootstrap"
    ):
        resolved_script = (
            default_spec_kit_script_type()
            if script_type == "auto" and detection.script_type is None
            else detection.script_type
            if script_type == "auto"
            else script_type
        )
        resolved_surface, resolved_label = _bridge_surface_from_preference(command_surface, detection)
        return SpecKitBridgeConfig(
            mode="bootstrap",
            state="bootstrapped",
            origin="enhancer-bootstrap",
            integration_key=detection.integration or "codex",
            managed_by="spec-kit",
            script_type=resolved_script,
            command_surface=resolved_surface,
            command_label=resolved_label,
            cli_version=detection.version or version or existing_bridge.cli_version,
            available_commands=detection.commands or DEFAULT_BOOTSTRAP_COMMANDS,
            evidence=detection.evidence,
            paths=detection.paths,
        )

    if detection.detected:
        raise ValueError(
            "Spec Kit bridge mode 'bootstrap' cannot run because official Spec Kit is already detected in the target repo. "
            "Use 'attach' or 'off' instead."
        )

    resolved_script = default_spec_kit_script_type() if script_type == "auto" else script_type
    resolved_surface, resolved_label = _bridge_surface_from_preference(
        "dollar" if command_surface == "auto" else command_surface,
        detection,
    )
    resolved_version = version or DEFAULT_SPEC_KIT_VERSION
    bootstrap_command = build_spec_kit_bootstrap_command(
        script_type=resolved_script,
        version=resolved_version,
        executable=executable,
    )
    return SpecKitBridgeConfig(
        mode="bootstrap",
        state="bootstrapped",
        origin="enhancer-bootstrap",
        integration_key="codex",
        managed_by="spec-kit",
        script_type=resolved_script,
        command_surface=resolved_surface,
        command_label=resolved_label,
        cli_version=resolved_version,
        available_commands=DEFAULT_BOOTSTRAP_COMMANDS,
        evidence=(
            "installer will bootstrap official Spec Kit for Codex",
            f"script type: {resolved_script}",
            f"requested Spec Kit version: {resolved_version}",
        ),
        paths=SpecKitPaths(
            specify_root=".specify",
            specs_root="specs",
            codex_skills_root=".agents/skills",
            constitution=".specify/memory/constitution.md",
        ),
        bootstrap_command=bootstrap_command,
    )


def render_spec_kit_detection_lines(detection: SpecKitDetection) -> list[str]:
    if not detection.detected:
        return ["- Official Spec Kit not detected."]

    lines = ["- Official Spec Kit detected."]
    if detection.integration:
        lines.append(f"- Integration: `{detection.integration}`")
    if detection.default_integration and detection.default_integration != detection.integration:
        lines.append(f"- Default integration: `{detection.default_integration}`")
    if detection.installed_integrations:
        lines.append(f"- Installed integrations: {_format_installed_integrations(detection)}")
    if detection.version:
        lines.append(f"- Spec Kit version: `{detection.version}`")
    if detection.script_type:
        lines.append(f"- Script type: `{detection.script_type}`")
    if detection.script_directory:
        lines.append(f"- Expected script directory: `{detection.script_directory}`")
    if detection.command_label:
        lines.append(f"- Likely command surface: {detection.command_label}.")
    if detection.generic_commands_dir:
        lines.append(
            f"- Generic integration command directory: `{detection.generic_commands_dir}` (official Spec Kit-owned)."
        )
    if detection.branch_numbering:
        lines.append(f"- Branch numbering: `{detection.branch_numbering}`")
    if detection.presets:
        lines.append(f"- Presets: {_format_addons(detection.presets)}")
    if detection.extensions:
        lines.append(f"- Extensions: {_format_addons(detection.extensions)}")
    if detection.paths.extensions_root and not detection.has_git_extension:
        lines.append("- Git extension: not detected; manage it through official Spec Kit extension commands.")
    if detection.commands:
        rendered = ", ".join(f"`{command}`" for command in detection.commands)
        lines.append(f"- Available commands: {rendered}")
    if detection.evidence:
        lines.append("- Evidence: " + "; ".join(detection.evidence))
    return lines


def _format_count_label(count: int, singular: str) -> str:
    if count == 1:
        return f"1 {singular}"
    return f"{count} {singular}s"


def render_spec_kit_feature_report(
    target: Path,
    *,
    feature: str | None = None,
    max_features: int = 20,
) -> str:
    root = target.resolve()
    detection = detect_spec_kit(root)
    summaries = discover_spec_kit_features(
        root,
        feature=feature,
        max_features=max_features,
    )

    lines = [f"Spec Kit feature report for {root}"]
    lines.extend(render_spec_kit_detection_lines(detection))
    if feature:
        lines.append(f"- Feature filter: `{feature}`")

    if not summaries:
        if not (root / "specs").is_dir():
            lines.append("- No `specs/` directory was found.")
        elif feature:
            lines.append("- No feature directory matched the requested filter.")
        else:
            lines.append("- No feature directories were found under `specs/`.")
        return "\n".join(lines)

    lines.append("")
    lines.append("Features:")
    for summary in summaries:
        lines.append(f"- `{summary.name}` at `{summary.path}`")
        artifacts = [*summary.core_files, *summary.support_files]
        if summary.contract_file_count:
            artifacts.append(
                f"contracts/ ({_format_count_label(summary.contract_file_count, 'file')})"
            )
        if summary.checklist_file_count:
            artifacts.append(
                f"checklists/ ({_format_count_label(summary.checklist_file_count, 'file')})"
            )
        lines.append(
            "  - Artifacts: " + (", ".join(f"`{item}`" for item in artifacts) or "none")
        )
        missing = (
            ", ".join(f"`{item}`" for item in summary.missing_core_files)
            if summary.missing_core_files
            else "none"
        )
        lines.append(f"  - Missing core artifacts: {missing}")
        if summary.task_total:
            lines.append(
                "  - Tasks: "
                f"{summary.task_total} total, {summary.task_done} done, {summary.task_open} open"
            )
        else:
            lines.append("  - Tasks: no checkbox tasks found")
    return "\n".join(lines)


def render_spec_kit_sync_report(
    target: Path,
    *,
    feature: str | None = None,
    changed_paths: tuple[str, ...] = (),
    git_base: str | None = None,
    max_features: int = 20,
) -> str:
    root = target.resolve()
    detection = detect_spec_kit(root)
    report = build_spec_kit_sync_report(
        root,
        feature=feature,
        changed_paths=changed_paths,
        git_base=git_base,
        max_features=max_features,
    )

    lines = [f"Spec Kit sync report for {root}"]
    lines.extend(render_spec_kit_detection_lines(detection))
    if feature:
        lines.append(f"- Feature filter: `{feature}`")
    if git_base:
        lines.append(f"- Git base: `{git_base}`")

    if report.features:
        lines.append("")
        lines.append("Feature artifacts:")
        for summary in report.features:
            lines.append(f"- `{summary.name}` at `{summary.path}`")
            artifacts = [*summary.core_files, *summary.support_files]
            if summary.contract_file_count:
                artifacts.append(
                    f"contracts/ ({_format_count_label(summary.contract_file_count, 'file')})"
                )
            if summary.checklist_file_count:
                artifacts.append(
                    f"checklists/ ({_format_count_label(summary.checklist_file_count, 'file')})"
                )
            lines.append(
                "  - Artifacts: " + (", ".join(f"`{item}`" for item in artifacts) or "none")
            )
            missing = (
                ", ".join(f"`{item}`" for item in summary.missing_core_files)
                if summary.missing_core_files
                else "none"
            )
            lines.append(f"  - Missing core artifacts: {missing}")
            if summary.task_total:
                lines.append(
                    "  - Tasks: "
                    f"{summary.task_total} total, {summary.task_done} done, {summary.task_open} open"
                )
            else:
                lines.append("  - Tasks: no checkbox tasks found")

    if report.artifact_paths:
        lines.append("")
        lines.append("Artifacts to re-read:")
        for artifact_path in report.artifact_paths:
            lines.append(f"- `{artifact_path}`")

    if report.changed_paths:
        lines.append("")
        lines.append("Changed paths reviewed:")
        for changed_path in report.changed_paths:
            lines.append(f"- `{changed_path}`")

    if report.notes:
        lines.append("")
        lines.append("Sync cues:")
        for note in report.notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def inspect_spec_kit_cli(
    target: Path,
    *,
    executable: str = "specify",
    check_cli: bool = False,
) -> SpecKitCliDiagnostic:
    if not check_cli:
        return SpecKitCliDiagnostic(
            checked=False,
            executable=executable,
            executable_path=None,
            version=None,
            version_output=None,
            feature_flags=(),
            feature_payload=None,
            integration_output=None,
            errors=(),
            warnings=(
                "Spec Kit CLI check skipped; pass `--check-spec-kit-cli` to run local read-only `specify` diagnostics.",
            ),
        )

    root = target.resolve()
    resolved = _resolve_executable_path(executable)
    if resolved is None:
        return SpecKitCliDiagnostic(
            checked=True,
            executable=executable,
            executable_path=None,
            version=None,
            version_output=None,
            feature_flags=(),
            feature_payload=None,
            integration_output=None,
            errors=(f"`{executable}` was not found on PATH or as a filesystem path.",),
            warnings=(),
        )

    errors: list[str] = []
    warnings: list[str] = []
    version_output, version_error = _run_specify_command(resolved, ("version",), cwd=root)
    if version_error:
        errors.append(version_error)
    version = _extract_cli_version(version_output)

    feature_payload: dict[str, object] | None = None
    feature_flags: tuple[str, ...] = ()
    features_output, features_error = _run_specify_command(
        resolved,
        ("version", "--features", "--json"),
        cwd=root,
    )
    if features_error:
        warnings.append(features_error)
    elif features_output:
        try:
            parsed_features = json.loads(features_output)
        except json.JSONDecodeError:
            warnings.append("`specify version --features --json` returned malformed JSON.")
        else:
            if isinstance(parsed_features, dict):
                feature_payload = parsed_features
            elif isinstance(parsed_features, list):
                feature_payload = {"features": parsed_features}
            else:
                warnings.append("`specify version --features --json` returned an unexpected JSON shape.")
            feature_flags = _feature_flags_from_payload(feature_payload)

    integration_output, integration_error = _run_specify_command(
        resolved,
        ("integration", "list"),
        cwd=root,
    )
    if integration_error:
        warnings.append(integration_error)

    return SpecKitCliDiagnostic(
        checked=True,
        executable=executable,
        executable_path=resolved,
        version=version,
        version_output=version_output,
        feature_flags=feature_flags,
        feature_payload=feature_payload,
        integration_output=integration_output,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def build_spec_kit_doctor_report(
    target: Path,
    *,
    check_cli: bool = False,
    executable: str = "specify",
) -> SpecKitDoctorReport:
    root = target.resolve()
    detection = detect_spec_kit(root)
    cli = inspect_spec_kit_cli(root, executable=executable, check_cli=check_cli)
    notes: list[str] = []

    if not detection.detected:
        notes.append("No official Spec Kit files were detected; this report remains advisory.")
    if detection.installed_integrations and len(detection.installed_integrations) > 1:
        notes.append(
            "Multiple integrations are recorded locally; use official Spec Kit integration commands to switch, use, upgrade, or uninstall them."
        )
    if any(_multi_install_status(item) != "multi-install safe" for item in detection.installed_integrations):
        notes.append("At least one integration has unknown or forced multi-install safety; do not let the enhancer change it.")
    if detection.generic_commands_dir:
        notes.append(
            "Generic integration command directories are external Spec Kit-owned surfaces; the enhancer will not write bridge files there."
        )
    if detection.presets or detection.extensions:
        notes.append(
            "Presets and extensions can change command files, templates, and quality gates; review their local metadata before implementation or review."
        )
    if detection.branch_numbering:
        notes.append(f"Recorded branch numbering strategy: `{detection.branch_numbering}`.")
    if not (root / ".git").is_dir():
        notes.append("Non-Git target detected; official Spec Kit feature commands may need `SPECIFY_FEATURE`.")
    if not detection.has_git_extension:
        notes.append("Spec Kit git extension was not detected; manage it through official Spec Kit extension commands.")

    cli_version_tuple = _parse_version_tuple(cli.version)
    if (
        cli.checked
        and cli_version_tuple is not None
        and cli_version_tuple < SPEC_KIT_MULTI_INSTALL_MIN_VERSION
        and len(detection.installed_integrations) > 1
    ):
        notes.append(
            "The local Spec Kit CLI appears older than 0.8.5; verify multi-install behavior before using official integration install or upgrade commands."
        )
    default_version_tuple = _parse_version_tuple(DEFAULT_SPEC_KIT_VERSION)
    if default_version_tuple is not None and default_version_tuple < SPEC_KIT_MULTI_INSTALL_MIN_VERSION:
        notes.append(
            f"The enhancer bootstrap default `{DEFAULT_SPEC_KIT_VERSION}` is pinned below Spec Kit 0.8.5, so multi-install guidance remains diagnostic-only unless the local CLI proves support."
        )

    return SpecKitDoctorReport(
        target=root.as_posix(),
        detection=detection,
        cli=cli,
        notes=tuple(dict.fromkeys(notes)),
    )


def _format_output_excerpt(output: str, *, limit: int = 8) -> list[str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    excerpt = [f"  - {line}" for line in lines[:limit]]
    hidden = len(lines) - limit
    if hidden > 0:
        excerpt.append(f"  - ... {hidden} more line(s) not shown.")
    return excerpt


def render_spec_kit_doctor_report(report: SpecKitDoctorReport) -> str:
    lines = [f"Spec Kit doctor report for {report.target}"]
    lines.extend(render_spec_kit_detection_lines(report.detection))
    lines.append("")
    lines.append("CLI diagnostics:")
    if not report.cli.checked:
        lines.extend(f"- {warning}" for warning in report.cli.warnings)
    else:
        lines.append(f"- Executable: `{report.cli.executable}`")
        if report.cli.executable_path:
            lines.append(f"- Resolved path: `{report.cli.executable_path}`")
        if report.cli.version:
            lines.append(f"- Version: `{report.cli.version}`")
        if report.cli.feature_flags:
            flags = ", ".join(f"`{flag}`" for flag in report.cli.feature_flags)
            lines.append(f"- Feature flags: {flags}")
        if report.cli.integration_output:
            lines.append("- Integration list output:")
            lines.extend(_format_output_excerpt(report.cli.integration_output))
        if report.cli.warnings:
            lines.append("- Warnings:")
            lines.extend(f"  - {warning}" for warning in report.cli.warnings)
        if report.cli.errors:
            lines.append("- Errors:")
            lines.extend(f"  - {error}" for error in report.cli.errors)

    if report.notes:
        lines.append("")
        lines.append("Bridge notes:")
        lines.extend(f"- {note}" for note in report.notes)
    return "\n".join(lines)


def format_spec_kit_bridge_mode_label(bridge: SpecKitBridgeConfig) -> str:
    if bridge.mode == "bootstrap":
        return "managed bootstrap"
    if bridge.mode == "attach":
        return "attached to an existing official install"
    return "off"


def render_spec_kit_bridge_summary(
    bridge: SpecKitBridgeConfig | SpecKitDetection,
    detection: SpecKitDetection | None = None,
) -> str:
    if isinstance(bridge, SpecKitDetection):
        detection = bridge
        bridge = resolve_spec_kit_bridge(Path("."), detection=detection)

    detection = detection or SpecKitDetection(
        detected=False,
        integration=None,
        command_surface=None,
        command_label=None,
        script_type=None,
        version=None,
        commands=(),
        evidence=(),
        paths=SpecKitPaths(),
    )
    if not bridge.enabled:
        lines = ["- Spec Kit bridge is off for this enhancer install."]
        if detection.detected:
            lines.append(
                "- Official Spec Kit was detected, but the enhancer bridge was left off intentionally."
            )
        else:
            lines.append(
                "- Official Spec Kit is not installed here yet. Re-run the installer with bridge attach or bootstrap if this repo adopts Spec Kit later."
            )
        lines.append(
            "- If `.specify/`, `specs/`, `.github/prompts/`, `.github/agents/`, or `.agents/skills/speckit-*` exist, review [docs/ai/spec-kit-bridge.md](docs/ai/spec-kit-bridge.md) before changing workflow guidance."
        )
        return "\n".join(lines)

    lines = [f"- Spec Kit bridge is {format_spec_kit_bridge_mode_label(bridge)}."]
    if bridge.integration_key:
        lines.append(f"- Official integration: `{bridge.integration_key}`.")
    if bridge.command_label:
        lines.append(f"- Default command surface: {bridge.command_label}.")
    if bridge.available_commands:
        commands = ", ".join(f"`{command}`" for command in bridge.available_commands)
        lines.append(f"- Bridge-aware commands: {commands}.")
    lines.append(
        "- Read feature artifacts in `specs/` before implementation or review, and keep enhancer validation or review notes aligned with the current spec, plan, tasks, contracts, and quickstart."
    )
    lines.append(
        "- Treat `.specify/`, `specs/`, and official Spec Kit prompt, agent, or skill files as separately owned."
    )
    lines.extend(SPEC_KIT_REVIEW_SAFETY_SUMMARY_LINES)
    return "\n".join(lines)


def render_spec_kit_bridge_doc_status(
    bridge: SpecKitBridgeConfig,
    detection: SpecKitDetection | None = None,
) -> str:
    detection = detection or SpecKitDetection(
        detected=False,
        integration=None,
        command_surface=None,
        command_label=None,
        script_type=None,
        version=None,
        commands=(),
        evidence=(),
        paths=SpecKitPaths(),
    )
    lines = [f"- Bridge mode: `{bridge.mode}`."]
    lines.append(f"- Bridge state: `{bridge.state}`.")
    if bridge.origin:
        lines.append(f"- Bridge origin: `{bridge.origin}`.")
    if bridge.integration_key:
        lines.append(f"- Official integration: `{bridge.integration_key}`.")
    if detection.default_integration:
        lines.append(f"- Default integration recorded by Spec Kit: `{detection.default_integration}`.")
    if detection.installed_integrations:
        lines.append(f"- Installed integrations: {_format_installed_integrations(detection)}.")
    if bridge.script_type:
        lines.append(f"- Script type: `{bridge.script_type}`.")
    if detection.script_directory:
        lines.append(f"- Expected script directory: `{detection.script_directory}`.")
    if bridge.cli_version:
        lines.append(f"- Spec Kit version: `{bridge.cli_version}`.")
    if bridge.command_label:
        lines.append(f"- Default command surface: {bridge.command_label}.")
    if detection.detected:
        lines.append("- Official Spec Kit files were detected in this repo.")
    else:
        lines.append("- Official Spec Kit files are not currently detected in this repo.")
    if detection.generic_commands_dir:
        lines.append(f"- Generic integration commands live at `{detection.generic_commands_dir}` and remain Spec Kit-owned.")
    if detection.presets:
        lines.append(f"- Local presets: {_format_addons(detection.presets)}.")
    if detection.extensions:
        lines.append(f"- Local extensions: {_format_addons(detection.extensions)}.")
    return "\n".join(lines)


def render_spec_kit_bridge_doc_command_surface(bridge: SpecKitBridgeConfig) -> str:
    if not bridge.enabled:
        return (
            "- No bridge-specific command surface is active.\n"
            "- If the repo later adopts official Spec Kit, prefer the official command surface that install created and then re-run the enhancer install or upgrade flow."
        )

    lines = []
    if bridge.command_label:
        lines.append(f"- Use {bridge.command_label} for official Spec Kit workflow steps.")
    if bridge.available_commands:
        commands = ", ".join(f"`{command}`" for command in bridge.available_commands)
        lines.append(f"- Expected commands in this repo: {commands}.")
    lines.append(
        "- Use enhancer skills after Spec Kit has already produced artifacts; do not use the enhancer to replace official Spec Kit planning commands."
    )
    return "\n".join(lines)


def render_spec_kit_bridge_doc_workflow(bridge: SpecKitBridgeConfig) -> str:
    if not bridge.enabled:
        return (
            "1. Use the normal enhancer loop: inspect -> plan -> edit -> validate -> review.\n"
            "2. If official Spec Kit appears later, read this file again and decide whether the bridge should be attached or bootstrapped."
        )

    return (
        "1. Start feature work with official Spec Kit: constitution -> specify -> clarify -> plan -> analyze -> tasks -> implement.\n"
        "2. Before editing code, read the active `spec.md`, `plan.md`, `tasks.md`, and any `contracts/`, `quickstart.md`, `research.md`, or `data-model.md` files for that feature.\n"
        "3. Implement the smallest coherent slice, then compare the code back against the feature artifacts.\n"
        "4. Use the bridge skills below for implementation alignment, drift checks, and review prep.\n"
        "5. For cross-agent reviews, share only relevant feature context and ask separately before peer CLI smoke tests or networked validation."
    )


def render_spec_kit_bridge_doc_skills(bridge: SpecKitBridgeConfig) -> str:
    if not bridge.enabled:
        return (
            "- Bridge skills are not installed while the bridge is off.\n"
            "- Turn the bridge on before adding workflow that assumes `specs/` artifacts exist."
        )

    return "\n".join(
        [
            "- `spec-implement-bridge`: use when a feature already has `plan.md` and `tasks.md` and you want repo-aware implementation work.",
            "- `spec-sync-check`: use when code changed and you need to compare it against `spec.md`, tasks, contracts, quickstart notes, or other feature artifacts.",
            "- `spec-review-bridge`: use when preparing a PR or review summary for a Spec Kit-driven branch.",
        ]
    )
