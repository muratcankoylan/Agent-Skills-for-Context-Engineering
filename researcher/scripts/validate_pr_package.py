#!/usr/bin/env python3
"""Check a prepared PR package without publishing, approving, or merging it.

This is a consistency check, not a signature or release authorization. Live
observation is opt-in and read-only; tests and the default command are offline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any
from urllib.parse import quote


class PackageError(ValueError):
    """A package or observation does not match the reviewed identities."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PackageError(message)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    require(not path.is_symlink() and path.is_file(), "missing or aliased JSON file")
    require(path.stat().st_size <= 2_000_000, "JSON file exceeds package bound")
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    require(type(value) is dict, "expected JSON object")
    return value


def oid(value: Any) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def numbered(rows: Any) -> dict[int, dict[str, Any]]:
    require(type(rows) is list and 0 < len(rows) < 1000, "invalid PR inventory size")
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        require(type(row) is dict, "invalid PR row")
        number = row.get("number")
        require(type(number) is int and number > 0 and number not in result,
                "duplicate or invalid PR number")
        result[number] = row
    return result


def compare_observation(manifest: dict[str, Any], observation: dict[str, Any], *, live: bool = False) -> None:
    require(observation.get("repository") == manifest["repository"], "repository drift")
    expected = numbered(manifest["pull_requests"])
    observed = numbered(observation.get("pull_requests"))
    require(set(expected) == set(observed), "open PR set changed; refresh all dispositions")
    for number, row in expected.items():
        actual = observed[number]
        for prepared, remote in (
            ("observed_head", "headRefOid"),
            ("observed_base_oid", "baseRefOid"),
            ("observed_base_ref", "baseRefName"),
            ("draft", "isDraft"),
        ):
            require(row[prepared] == actual.get(remote), f"PR {number}: {remote} drift")
        require(type(actual.get("isDraft")) is bool, f"PR {number}: invalid draft state")
        require(type(actual.get("baseRefName")) is str and bool(actual["baseRefName"].strip()),
                f"PR {number}: invalid observed base branch")
        # Older saved inventories predate the state field. Live observations
        # explicitly request it and cannot use that compatibility allowance.
        state = actual.get("state") if live else actual.get("state", "OPEN")
        require(state == "OPEN", f"PR {number}: missing open state or no longer open")


def validate_package(package: Path, live: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = read_json(package / "manifest.json")
    require(type(manifest.get("schema_version")) is int and manifest["schema_version"] == 1,
            "unsupported package schema")
    require(manifest.get("mode") == "local_preparation_only", "not a preparation package")
    require(manifest.get("remote_mutations") == [], "unexpected remote mutation claim")
    require(manifest.get("production_ready") is False, "package cannot confer release readiness")
    require(manifest.get("publication_requires_specific_owner_approval") is True,
            "publication approval requirement missing")
    require(type(manifest.get("repository")) is str and re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", manifest["repository"]
    ) is not None, "invalid repository")
    default = manifest.get("protected_default_observed")
    require(oid(default), "invalid default-branch identity")
    default_ref = manifest.get("protected_default_ref")
    require(type(default_ref) is str and bool(default_ref.strip()), "missing default-branch name")
    rows = numbered(manifest.get("pull_requests"))
    order = manifest.get("core_order")
    require(type(order) is list and order and all(type(n) is int for n in order)
            and len(order) == len(set(order)), "invalid core order")
    require(set(order) == {n for n, row in rows.items() if row.get("group") == "core"},
            "core order does not cover exactly the core PRs")
    require(type(manifest.get("separate_first_adoption_pr")) is int
            and manifest["separate_first_adoption_pr"] == order[0], "adoption interval drift")
    previous = None
    previous_head = default
    for number in order:
        row = rows[number]
        dependencies = row.get("depends_on")
        require(type(dependencies) is list and all(type(n) is int and n > 0 for n in dependencies),
                f"PR {number}: invalid dependency identifiers")
        require(row.get("depends_on") == ([] if previous is None else [previous]),
                f"PR {number}: dependency edge drift")
        require(row.get("observed_base_oid") == previous_head, f"PR {number}: base is not predecessor head")
        if previous is None:
            require(row.get("observed_base_ref") == default_ref, "first core base is not default")
        previous, previous_head = number, row.get("observed_head")
    for number, row in rows.items():
        require(oid(row.get("observed_head")) and oid(row.get("observed_base_oid")),
                f"PR {number}: invalid Git identity")
        require(type(row.get("observed_base_ref")) is str and bool(row["observed_base_ref"].strip()),
                f"PR {number}: invalid prepared base branch")
        require(type(row.get("draft")) is bool and row.get("merge_approved") is False,
                f"PR {number}: invalid preparation state")
        require(type(row.get("action")) is str and bool(row["action"])
                and type(row.get("reason")) is str and bool(row["reason"]),
                f"PR {number}: disposition missing")
        if number not in order:
            require(row.get("depends_on") == [], f"PR {number}: unreviewed non-core dependency")

    inventory_name = manifest.get("inventory")
    require(type(inventory_name) is str and re.fullmatch(
        r"\.\./evidence/[A-Za-z0-9_.-]+\.json", inventory_name
    ) is not None, "invalid inventory locator")
    compare_observation(manifest, read_json(package / inventory_name))
    if live is not None:
        require(live.get("default_ref") == default_ref, "repository default branch changed")
        require(live.get("default_oid") == default, "default branch moved; rebase and retest")
        compare_observation(manifest, live, live=True)

    patches = manifest.get("patches")
    require(type(patches) is list and patches, "no prepared patches")
    ids: set[str] = set()
    files: set[str] = set()
    for patch in patches:
        require(type(patch) is dict, "invalid patch entry")
        name, identity = patch.get("file"), patch.get("id")
        require(type(identity) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identity) is not None
                and identity not in ids, "invalid or duplicate patch identity")
        require(type(name) is str and re.fullmatch(r"[A-Za-z0-9_-]+\.patch", name) is not None
                and name not in files, "invalid or duplicate patch filename")
        ids.add(identity)
        files.add(name)
        path = package / name
        require(not path.is_symlink() and path.is_file(), "missing or aliased patch")
        require(path.stat().st_size <= 2_000_000, "patch exceeds package bound")
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == patch.get("sha256"), f"{identity}: digest mismatch")
        headers = [line for line in data.splitlines() if line.startswith(b"diff --git ")]
        require(type(patch.get("file_count")) is int and len(headers) == patch["file_count"] > 0,
                f"{identity}: file count mismatch")
        target, addresses = patch.get("target_pr"), patch.get("addresses_pr")
        require((target is None) != (addresses is None), f"{identity}: ambiguous target")
        number = target if target is not None else addresses
        require(type(number) is int and number in rows, f"{identity}: unknown target")
        expected_base = rows[number]["observed_head"] if target is not None else default
        require(patch.get("base") == expected_base, f"{identity}: base does not match reviewed target")
    require(files == {path.name for path in package.glob("*.patch")}, "unregistered patch file")
    return {
        "schema": "pr-package-consistency/v1", "pull_requests": len(rows),
        "drafts": sum(row["draft"] for row in rows.values()), "patches": len(patches),
        "live_identities_checked": live is not None, "production_ready": False,
        "scope": "metadata, dependency edges and patch bytes; not CI, approval or runtime readiness",
    }


def observe_live(repository: str) -> dict[str, Any]:
    def gh(*arguments: str) -> Any:
        result = subprocess.run(["gh", *arguments], capture_output=True, text=True, timeout=60)
        require(result.returncode == 0, "GitHub observation failed; no readiness result")
        require(len(result.stdout) <= 2_000_000, "GitHub observation exceeds bound")
        return json.loads(result.stdout, object_pairs_hook=unique_object)

    fields = "number,headRefOid,baseRefOid,baseRefName,isDraft,state"
    default_ref = gh("api", f"repos/{repository}")["default_branch"]
    require(type(default_ref) is str and bool(default_ref.strip()), "missing GitHub default branch")
    reference = f"repos/{repository}/git/ref/heads/{quote(default_ref, safe='')}"
    before = gh("api", reference)["object"]["sha"]
    rows = gh("pr", "list", "--repo", repository, "--state", "open", "--limit", "1000", "--json", fields)
    after = gh("api", reference)["object"]["sha"]
    after_ref = gh("api", f"repos/{repository}")["default_branch"]
    require(before == after and default_ref == after_ref, "default branch moved during observation")
    return {"repository": repository, "default_ref": default_ref,
            "default_oid": after, "pull_requests": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--live", action="store_true", help="read current GitHub identities with gh")
    args = parser.parse_args()
    try:
        # Refuse malformed local packages before making even read-only network calls.
        result = validate_package(args.package)
        if args.live:
            manifest = read_json(args.package / "manifest.json")
            result = validate_package(args.package, observe_live(manifest["repository"]))
    except PackageError as exc:
        print(json.dumps({"valid": False, "production_ready": False, "error": str(exc)}))
        return 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        print(json.dumps({"valid": False, "production_ready": False,
                          "error": "PR package or observation failed validation; refresh and inspect locally"}))
        return 1
    print(json.dumps({"valid": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
