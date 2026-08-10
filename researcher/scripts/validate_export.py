#!/usr/bin/env python3
"""Plan, render, and validate allowlisted public export projections."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from build_inventory import DuplicateKeyError, parse_json_text, pretty_json
    from export_policy import (
        DEFAULT_POLICY_PATH,
        ExportBoundaryError,
        ExportPolicy,
        check_staging,
        plan_export,
        render_export,
        write_private_json,
    )
except ModuleNotFoundError:  # Imported as researcher.scripts.validate_export.
    from researcher.scripts.build_inventory import DuplicateKeyError, parse_json_text, pretty_json
    from researcher.scripts.export_policy import (
        DEFAULT_POLICY_PATH,
        ExportBoundaryError,
        ExportPolicy,
        check_staging,
        plan_export,
        render_export,
        write_private_json,
    )


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = parse_json_text(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        raise ExportBoundaryError("PARSE_ERROR", f"{label} could not be loaded") from exc
    if not isinstance(value, dict):
        raise ExportBoundaryError("PARSE_ERROR", f"{label} must be a JSON object")
    return value


def load_canaries(path: Path | None) -> list[str]:
    if path is None:
        return []
    try:
        return [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, UnicodeError) as exc:
        raise ExportBoundaryError("PARSE_ERROR", "canary file could not be loaded") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="create an immutable private ExportPlan")
    plan_parser.add_argument("--request", type=Path, required=True)
    plan_parser.add_argument("--private-root", type=Path, required=True)
    plan_parser.add_argument("--plan-out", type=Path, required=True)

    render_parser = subparsers.add_parser("render", help="render a plan into a fresh public staging tree")
    render_parser.add_argument("--plan", type=Path, required=True)
    render_parser.add_argument("--private-root", type=Path, required=True)
    render_parser.add_argument("--staging-dir", type=Path, required=True)
    render_parser.add_argument("--receipt-out", type=Path, required=True)
    render_parser.add_argument("--canary-file", type=Path)

    check_parser = subparsers.add_parser("check", help="validate an existing public staging tree")
    check_parser.add_argument("--staging-dir", type=Path, required=True)
    check_parser.add_argument("--canary-file", type=Path)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        policy = ExportPolicy.load(args.policy)
        if args.command == "plan":
            request = load_json_object(args.request, "ExportRequest")
            plan = plan_export(request, args.private_root, policy)
            write_private_json(args.plan_out, plan)
            print(
                json.dumps(
                    {
                        "result": "planned",
                        "export_id": plan["id"],
                        "entry_count": len(plan["entries"]),
                        "policy_version": policy.version,
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "render":
            plan = load_json_object(args.plan, "ExportPlan")
            canaries = load_canaries(args.canary_file)
            manifest, receipt = render_export(
                plan, args.private_root, args.staging_dir, policy, canaries=canaries
            )
            try:
                write_private_json(args.receipt_out, receipt)
            except Exception:
                # The staging tree was created by this command and is not yet
                # externally visible. Remove it if the private audit receipt
                # cannot be persisted, so a supported render is never orphaned.
                import shutil

                shutil.rmtree(args.staging_dir, ignore_errors=True)
                raise
            print(
                json.dumps(
                    {
                        "result": "rendered",
                        "export_id": manifest["id"],
                        "entry_count": len(manifest["entries"]),
                        "policy_version": policy.version,
                    },
                    sort_keys=True,
                )
            )
            return 0
        canaries = load_canaries(args.canary_file)
        validation = check_staging(args.staging_dir, policy, canaries=canaries)
        print(pretty_json(validation), end="")
        return 0
    except ExportBoundaryError as exc:
        print(f"[{exc.code}] {exc.safe_message}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[IO_ERROR] {exc.__class__.__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
