"""Locate source-checkout files or packaged runtime assets."""

from __future__ import annotations

from contextlib import AbstractContextManager
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path


CHECKOUT_ROOT = Path(__file__).resolve().parents[1]
_OPEN_RESOURCE_CONTEXTS: list[AbstractContextManager[Path]] = []


def asset_path(relative_path: str | Path) -> Path:
    """Return a filesystem path for a checkout file or packaged asset."""

    relative = Path(relative_path)
    checkout_candidate = CHECKOUT_ROOT / relative
    if checkout_candidate.exists():
        return checkout_candidate

    packaged = _packaged_asset(relative)
    if not (packaged.is_file() or packaged.is_dir()):
        raise FileNotFoundError(f"Codex Enhancer package asset is missing: {relative.as_posix()}")
    return _resource_to_path(packaged)


def read_asset_text(relative_path: str | Path) -> str:
    return asset_path(relative_path).read_text(encoding="utf-8")


def _packaged_asset(relative_path: Path) -> Traversable:
    root = resources.files("codex_enhancer").joinpath("assets", "root")
    return root.joinpath(*relative_path.parts) if relative_path.parts else root


def _resource_to_path(resource: Traversable) -> Path:
    if isinstance(resource, Path):
        return resource
    context = resources.as_file(resource)
    path = context.__enter__()
    _OPEN_RESOURCE_CONTEXTS.append(context)
    return path

