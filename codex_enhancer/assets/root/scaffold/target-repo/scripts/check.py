#!/usr/bin/env python3
"""Validate the installed Codex Enhancer assets in this repository."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.enhancer_spec import TARGET_VALIDATION_PROFILE
from scripts.enhancer_validator import run_validation, validate as run_profile_validation


DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def validate(root: Path, verbose: bool = False) -> list[str]:
    return run_profile_validation(root, TARGET_VALIDATION_PROFILE, verbose=verbose)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print each successful check",
    )
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    return run_validation(root, TARGET_VALIDATION_PROFILE, verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
