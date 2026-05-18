#!/usr/bin/env python3
"""Friendly command facade for the Codex Enhancer installer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-enhancer",
        description=(
            "Run Codex Enhancer installer workflows with short subcommands. "
            "This command delegates to scripts/install_enhancer.py."
        ),
        epilog=(
            "First useful commands:\n"
            "  codex-enhancer quickstart\n"
            "  codex-enhancer doctor .\n"
            "  codex-enhancer init ../my-repo --existing --summary\n"
            "  codex-enhancer init ../my-repo --existing --summary --diff\n"
            "  codex-enhancer inspect ../my-repo\n\n"
            "Preview is the default. Add --write only after the plan looks right."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    quickstart = subparsers.add_parser(
        "quickstart",
        help="print a concise read-only getting-started guide",
    )
    quickstart.set_defaults(action="quickstart")
    quickstart.add_argument("target", nargs="?", default=".", help="target repository path; defaults to the current directory")
    add_output_options(quickstart, include_plan_options=False)

    doctor = subparsers.add_parser(
        "doctor",
        help="run a read-only first-run diagnostic",
    )
    doctor.set_defaults(action="doctor")
    doctor.add_argument("target", nargs="?", default=".", help="target repository path; defaults to the current directory")
    add_output_options(doctor, include_plan_options=False)

    install = subparsers.add_parser(
        "install",
        aliases=("init",),
        help="preview or apply an enhancer install into a target repo",
    )
    install.set_defaults(action="install")
    install.add_argument("target", help="target repository path")
    add_mode_options(install)
    add_write_options(install, include_force=True)
    add_output_options(install, include_plan_options=True)
    add_install_pack_options(install)
    add_spec_kit_options(install)
    add_utility_harness_options(install)

    inspect = subparsers.add_parser(
        "inspect",
        help="inspect source-vs-target enhancer install state",
    )
    inspect.set_defaults(action="inspect")
    inspect.add_argument("target", help="target repository path")
    add_output_options(inspect, include_plan_options=False)

    audit = subparsers.add_parser(
        "audit",
        help="audit an installed target for inherited enhancer guidance",
    )
    audit.set_defaults(action="audit")
    audit.add_argument("target", help="target repository path")
    add_output_options(audit, include_plan_options=False)

    upgrade = subparsers.add_parser(
        "upgrade",
        help="preview or apply a reconcile of an installed enhancer",
    )
    upgrade.set_defaults(action="upgrade")
    upgrade.add_argument("target", help="target repository path")
    add_write_options(upgrade, include_force=False)
    add_output_options(upgrade, include_plan_options=True)
    add_spec_kit_options(upgrade)
    add_utility_harness_options(upgrade)
    add_existing_pack_options(upgrade)

    refresh = subparsers.add_parser(
        "refresh",
        help="re-render enhancer-managed generated outputs",
    )
    refresh.set_defaults(action="refresh")
    refresh.add_argument("target", help="target repository path")
    add_write_options(refresh, include_force=False)
    add_output_options(refresh, include_plan_options=True)

    bridge = subparsers.add_parser(
        "bridge",
        help="manage Spec Kit bridge state for an installed target",
    )
    bridge.set_defaults(action="bridge")
    bridge.add_argument("target", help="target repository path")
    add_write_options(bridge, include_force=False)
    add_output_options(bridge, include_plan_options=True)
    add_spec_kit_options(bridge)

    spec_report = subparsers.add_parser(
        "spec-report",
        help="print a read-only report of Spec Kit feature artifacts",
    )
    spec_report.set_defaults(action="spec_report")
    spec_report.add_argument("target", help="target repository path")
    add_output_options(spec_report, include_plan_options=False)
    spec_report.add_argument(
        "--feature",
        "--spec-kit-feature",
        dest="spec_kit_feature",
        help="limit the report to a feature directory name or numeric prefix",
    )

    spec_doctor = subparsers.add_parser(
        "spec-doctor",
        help="print a read-only Spec Kit bridge diagnostics report",
    )
    spec_doctor.set_defaults(action="spec_doctor")
    spec_doctor.add_argument("target", help="target repository path")
    add_output_options(spec_doctor, include_plan_options=False)
    spec_doctor.add_argument(
        "--check-spec-kit-cli",
        action="store_true",
        help="run local read-only `specify` version and integration diagnostics",
    )
    spec_doctor.add_argument(
        "--spec-kit-exe",
        help="path to a local `specify`-compatible executable for diagnostics",
    )

    spec_sync = subparsers.add_parser(
        "spec-sync",
        help="print a read-only Spec Kit sync report for changed paths",
    )
    spec_sync.set_defaults(action="spec_sync")
    spec_sync.add_argument("target", help="target repository path")
    add_output_options(spec_sync, include_plan_options=False)
    spec_sync.add_argument(
        "--feature",
        "--spec-kit-feature",
        dest="spec_kit_feature",
        help="limit the report to a feature directory name or numeric prefix",
    )
    spec_sync.add_argument(
        "--changed",
        "--spec-kit-changed-path",
        action="append",
        default=[],
        dest="spec_kit_changed_path",
        help="changed path to include in the sync report; may be repeated",
    )
    spec_sync.add_argument(
        "--base",
        "--spec-kit-base",
        dest="spec_kit_base",
        help="git base ref for local diff path discovery",
    )

    packs = subparsers.add_parser(
        "packs",
        help="manage selected stack packs for an installed target",
    )
    packs.set_defaults(action="packs")
    packs.add_argument("target", help="target repository path")
    add_write_options(packs, include_force=False)
    add_output_options(packs, include_plan_options=True)
    packs.add_argument("--add", "--add-pack", action="append", default=[], dest="add_pack")
    packs.add_argument("--remove", "--remove-pack", action="append", default=[], dest="remove_pack")
    packs.add_argument("--set", "--set-pack", action="append", default=[], dest="set_pack")

    workflows = subparsers.add_parser(
        "workflows",
        help="manage selected workflow packs for an installed target",
    )
    workflows.set_defaults(action="workflows")
    workflows.add_argument("target", help="target repository path")
    add_write_options(workflows, include_force=False)
    add_output_options(workflows, include_plan_options=True)
    workflows.add_argument("--add", "--add-workflow", action="append", default=[], dest="add_workflow")
    workflows.add_argument("--remove", "--remove-workflow", action="append", default=[], dest="remove_workflow")
    workflows.add_argument("--set", "--set-workflow", action="append", default=[], dest="set_workflow")

    list_packs = subparsers.add_parser(
        "list-packs",
        help="print available stack packs",
    )
    list_packs.set_defaults(action="list_packs")
    list_packs.add_argument("target", nargs="?", help="optional target repository path")
    add_mode_options(list_packs)
    add_output_options(list_packs, include_plan_options=False)

    list_workflows = subparsers.add_parser(
        "list-workflows",
        help="print available workflow packs",
    )
    list_workflows.set_defaults(action="list_workflows")
    list_workflows.add_argument("target", nargs="?", help="optional target repository path")
    add_mode_options(list_workflows)
    add_output_options(list_workflows, include_plan_options=False)

    gui = subparsers.add_parser(
        "gui",
        help="open the Windows-first browser GUI installer",
    )
    gui.set_defaults(action="gui")

    return parser


def add_mode_options(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mode", choices=("auto", "new", "existing"))
    mode.add_argument("--auto", action="store_const", const="auto", dest="mode_shortcut")
    mode.add_argument("--new", action="store_const", const="new", dest="mode_shortcut")
    mode.add_argument("--existing", action="store_const", const="existing", dest="mode_shortcut")


def add_write_options(parser: argparse.ArgumentParser, *, include_force: bool) -> None:
    write_mode = parser.add_mutually_exclusive_group()
    write_mode.add_argument("--write", dest="write", action="store_true", help="apply the planned change")
    write_mode.add_argument(
        "--dry-run",
        dest="write",
        action="store_false",
        help="preview the plan without writing files; this is the default",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="allow --write over unrelated local target changes after reviewing the plan",
    )
    parser.add_argument(
        "--allow-source-target",
        action="store_true",
        help="allow --write when the target looks like the Codex Enhancer source checkout",
    )
    parser.set_defaults(write=False)
    if include_force:
        parser.add_argument(
            "--force",
            action="store_true",
            help="overwrite colliding files instead of writing proposals",
        )


def add_output_options(parser: argparse.ArgumentParser, *, include_plan_options: bool) -> None:
    if include_plan_options:
        parser.add_argument("--summary", action="store_true", help="print a concise plan preview")
        parser.add_argument("--diff", action="store_true", help="include a unified diff preview")
        parser.add_argument(
            "--diff-full",
            action="store_true",
            help="show full per-file diffs instead of truncating large --diff output",
        )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")


def add_install_pack_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--recommended",
        "--use-recommended-packs",
        action="store_true",
        dest="use_recommended_packs",
        help="select detected stack packs marked as recommended",
    )
    parser.add_argument("--pack", action="append", default=[], help="include a stack pack")
    parser.add_argument("--no-pack", action="append", default=[], help="exclude a stack pack")


def add_existing_pack_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--add-pack", action="append", default=[], help="add a stack pack during upgrade")
    parser.add_argument(
        "--remove-pack",
        action="append",
        default=[],
        help="remove a stack pack during upgrade",
    )
    parser.add_argument(
        "--set-pack",
        action="append",
        default=[],
        help="replace the installed stack-pack set during upgrade",
    )


def add_spec_kit_options(parser: argparse.ArgumentParser) -> None:
    spec_kit = parser.add_mutually_exclusive_group()
    spec_kit.add_argument(
        "--spec-kit",
        "--spec-kit-mode",
        choices=("off", "auto", "attach", "bootstrap"),
        dest="spec_kit_mode",
        help="set optional Spec Kit bridge mode",
    )
    spec_kit.add_argument(
        "--with-spec-kit",
        action="store_const",
        const="bootstrap",
        dest="spec_kit_mode",
        help=(
            "bootstrap official Spec Kit for Codex and install enhancer bridge guidance; "
            "the external bootstrap only runs when --write is used"
        ),
    )
    spec_kit.add_argument(
        "--attach-spec-kit",
        action="store_const",
        const="attach",
        dest="spec_kit_mode",
        help="attach enhancer bridge guidance to an existing official Spec Kit install",
    )
    spec_kit.add_argument(
        "--no-spec-kit",
        action="store_const",
        const="off",
        dest="spec_kit_mode",
        help="leave official Spec Kit disabled for this enhancer flow",
    )
    parser.add_argument(
        "--spec-kit-script",
        choices=("auto", "ps", "sh"),
        default="auto",
        help="override Spec Kit bridge script flavor",
    )
    parser.add_argument(
        "--spec-kit-command-surface",
        choices=("auto", "dollar", "slash"),
        default="auto",
        help="override the preferred Spec Kit command surface",
    )
    parser.add_argument("--spec-kit-version", help="pin the official Spec Kit version or ref")
    parser.add_argument(
        "--spec-kit-exe",
        help="path to a local specify-compatible executable for Spec Kit bootstrap",
    )


def add_utility_harness_options(parser: argparse.ArgumentParser) -> None:
    utility = parser.add_mutually_exclusive_group()
    utility.add_argument(
        "--utility-harness",
        action="store_const",
        const="install",
        dest="utility_harness_mode",
        help="install the optional Codex Utility Harness helper files",
    )
    utility.add_argument(
        "--no-utility-harness",
        action="store_const",
        const="off",
        dest="utility_harness_mode",
        help="disable the optional Codex Utility Harness helper files",
    )
    utility.add_argument(
        "--utility-harness-mode",
        choices=("off", "install"),
        dest="utility_harness_mode",
        help="set optional Codex Utility Harness mode",
    )
    parser.add_argument(
        "--install-utility-harness-dependencies",
        action="store_true",
        help="after writing Utility Harness files, install helper dependencies with pip",
    )


def selected_mode(args: argparse.Namespace) -> str:
    return args.mode_shortcut or args.mode or "auto"


def translate_to_installer_args(args: argparse.Namespace) -> list[str]:
    if args.action == "quickstart":
        installer_args = ["--target", args.target, "--quickstart"]
        append_output_args(installer_args, args)
        return installer_args

    if args.action == "doctor":
        installer_args = ["--target", args.target, "--doctor"]
        append_output_args(installer_args, args)
        return installer_args

    if args.action == "list_packs":
        installer_args = ["--list-packs", "--mode", selected_mode(args)]
        if args.target:
            installer_args.extend(["--target", args.target])
        append_output_args(installer_args, args)
        return installer_args

    if args.action == "list_workflows":
        installer_args = ["--list-workflows", "--mode", selected_mode(args)]
        if args.target:
            installer_args.extend(["--target", args.target])
        append_output_args(installer_args, args)
        return installer_args

    installer_args = ["--target", args.target]

    if args.action == "install":
        installer_args.extend(["--mode", selected_mode(args)])
        if args.write:
            installer_args.append("--write")
        if args.force:
            installer_args.append("--force")
        append_write_safety_args(installer_args, args)
        if args.use_recommended_packs:
            installer_args.append("--use-recommended-packs")
        for pack in args.pack:
            installer_args.extend(["--pack", pack])
        for pack in args.no_pack:
            installer_args.extend(["--no-pack", pack])
        append_output_args(installer_args, args)
        append_spec_kit_args(installer_args, args)
        append_utility_harness_args(installer_args, args)
        return installer_args

    if args.action == "inspect":
        installer_args.append("--inspect-install")
        append_output_args(installer_args, args)
        return installer_args

    if args.action == "audit":
        installer_args.append("--audit-adaptation")
        append_output_args(installer_args, args)
        return installer_args

    if args.action == "upgrade":
        installer_args.append("--upgrade-enhancer")
        if args.write:
            installer_args.append("--write")
        append_write_safety_args(installer_args, args)
        append_output_args(installer_args, args)
        append_spec_kit_args(installer_args, args)
        append_utility_harness_args(installer_args, args)
        append_existing_pack_args(installer_args, args)
        return installer_args

    if args.action == "refresh":
        installer_args.append("--refresh-generated")
        if args.write:
            installer_args.append("--write")
        append_write_safety_args(installer_args, args)
        append_output_args(installer_args, args)
        return installer_args

    if args.action == "bridge":
        installer_args.append("--manage-spec-kit-bridge")
        if args.write:
            installer_args.append("--write")
        append_write_safety_args(installer_args, args)
        append_output_args(installer_args, args)
        append_spec_kit_args(installer_args, args)
        return installer_args

    if args.action == "spec_report":
        installer_args.append("--spec-kit-report")
        append_output_args(installer_args, args)
        if args.spec_kit_feature:
            installer_args.extend(["--spec-kit-feature", args.spec_kit_feature])
        return installer_args

    if args.action == "spec_doctor":
        installer_args.append("--spec-kit-doctor")
        append_output_args(installer_args, args)
        if args.check_spec_kit_cli:
            installer_args.append("--check-spec-kit-cli")
        if args.spec_kit_exe:
            installer_args.extend(["--spec-kit-exe", args.spec_kit_exe])
        return installer_args

    if args.action == "spec_sync":
        installer_args.append("--spec-kit-sync-report")
        append_output_args(installer_args, args)
        if args.spec_kit_feature:
            installer_args.extend(["--spec-kit-feature", args.spec_kit_feature])
        for changed_path in args.spec_kit_changed_path:
            installer_args.extend(["--spec-kit-changed-path", changed_path])
        if args.spec_kit_base:
            installer_args.extend(["--spec-kit-base", args.spec_kit_base])
        return installer_args

    if args.action == "packs":
        installer_args.append("--manage-packs")
        if args.write:
            installer_args.append("--write")
        append_write_safety_args(installer_args, args)
        append_output_args(installer_args, args)
        for pack in args.add_pack:
            installer_args.extend(["--add-pack", pack])
        for pack in args.remove_pack:
            installer_args.extend(["--remove-pack", pack])
        for pack in args.set_pack:
            installer_args.extend(["--set-pack", pack])
        return installer_args

    if args.action == "workflows":
        installer_args.append("--manage-workflows")
        if args.write:
            installer_args.append("--write")
        append_write_safety_args(installer_args, args)
        append_output_args(installer_args, args)
        for workflow in args.add_workflow:
            installer_args.extend(["--add-workflow", workflow])
        for workflow in args.remove_workflow:
            installer_args.extend(["--remove-workflow", workflow])
        for workflow in args.set_workflow:
            installer_args.extend(["--set-workflow", workflow])
        return installer_args

    raise ValueError(f"Unsupported codex-enhancer action: {args.action}")


def append_spec_kit_args(installer_args: list[str], args: argparse.Namespace) -> None:
    if args.spec_kit_mode:
        installer_args.extend(["--spec-kit-mode", args.spec_kit_mode])
    if args.spec_kit_script != "auto":
        installer_args.extend(["--spec-kit-script", args.spec_kit_script])
    if args.spec_kit_command_surface != "auto":
        installer_args.extend(["--spec-kit-command-surface", args.spec_kit_command_surface])
    if args.spec_kit_version:
        installer_args.extend(["--spec-kit-version", args.spec_kit_version])
    if args.spec_kit_exe:
        installer_args.extend(["--spec-kit-exe", args.spec_kit_exe])


def append_output_args(installer_args: list[str], args: argparse.Namespace) -> None:
    if getattr(args, "summary", False):
        installer_args.append("--summary")
    if getattr(args, "diff", False):
        installer_args.append("--diff")
    if getattr(args, "diff_full", False):
        installer_args.append("--diff-full")
    if getattr(args, "json", False):
        installer_args.append("--json")


def append_write_safety_args(installer_args: list[str], args: argparse.Namespace) -> None:
    if args.allow_dirty:
        installer_args.append("--allow-dirty")
    if args.allow_source_target:
        installer_args.append("--allow-source-target")


def append_utility_harness_args(installer_args: list[str], args: argparse.Namespace) -> None:
    if args.utility_harness_mode:
        installer_args.extend(["--utility-harness-mode", args.utility_harness_mode])
    if getattr(args, "install_utility_harness_dependencies", False):
        installer_args.append("--install-utility-harness-dependencies")


def append_existing_pack_args(installer_args: list[str], args: argparse.Namespace) -> None:
    for pack in args.add_pack:
        installer_args.extend(["--add-pack", pack])
    for pack in args.remove_pack:
        installer_args.extend(["--remove-pack", pack])
    for pack in args.set_pack:
        installer_args.extend(["--set-pack", pack])


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.action == "gui":
        from scripts.install_enhancer_web_gui import main as gui_main

        return gui_main([])

    from scripts.install_enhancer import main as installer_main

    return installer_main(translate_to_installer_args(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
