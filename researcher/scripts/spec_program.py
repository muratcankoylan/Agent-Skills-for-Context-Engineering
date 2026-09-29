#!/usr/bin/env python3
"""Read-only, non-authoritative specification and delivery-plan coverage audit.

This is not the lifecycle validator, an evidence grader, or an executor. Local
headers and checked Markdown boxes cannot establish protected-default authority
or completed work. Every criterion remains unassessed. ``plan`` prints a blank,
deliberately invalid template; ``check`` validates coverage and source bindings,
not the truth or sufficiency of the proposed verification prose.

Reads are bounded and reject aliases/nonregular files. Cooperative local files
are assumed: these checks are not isolation from hostile same-UID replacement.
Reading may update access times, but this module does not write or repair files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

if __package__:
    from .build_inventory import (
        contains_raw_html_block,
        markdown_level_two_sections,
        visible_unfenced_lines,
    )
    from .schema_contract import ContractError, canonicalize, parse_json_strict
    from .validate_spec_lifecycle import (
        SPEC_PATH_RE,
        STAGE_RANK,
        TERMINAL_STATUSES,
        parse_spec_revision,
    )
else:
    from build_inventory import (
        contains_raw_html_block,
        markdown_level_two_sections,
        visible_unfenced_lines,
    )
    from schema_contract import ContractError, canonicalize, parse_json_strict
    from validate_spec_lifecycle import (
        SPEC_PATH_RE,
        STAGE_RANK,
        TERMINAL_STATUSES,
        parse_spec_revision,
    )


ROOT = Path(__file__).resolve().parents[2]
MAX_SPECS = 128
MAX_DIRECTORY_ENTRIES = 256
MAX_SPEC_BYTES = 262144
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_PLAN_BYTES = 4 * 1024 * 1024
MAX_CRITERIA = 128
MAX_TOTAL_CRITERIA = 4096
MAX_TEXT_BYTES = 8192
_SPEC_ID = re.compile(r"SPEC-[0-9]{3}\Z")
_BINDING = re.compile(r"(SPEC-[0-9]{3})@([1-9][0-9]*)\Z")
_CHECKBOX = re.compile(r" {0,3}[-+*] \[([ xX])\] (.+)\Z")
_SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")


class ProgramError(ValueError):
    def __init__(self, code: str, message: str, path: str = ""):
        super().__init__(message)
        self.code, self.path = code, path


def _text(value: Any, maximum: int = MAX_TEXT_BYTES) -> bool:
    if type(value) is not str or not value.strip():
        return False
    try:
        return len(value.encode("utf-8")) <= maximum and "\x00" not in value
    except UnicodeError:
        return False


def _root(root: Path) -> Path:
    try:
        path = Path(root).absolute()
        if path.resolve(strict=True) != path or not stat.S_ISDIR(path.lstat().st_mode):
            raise OSError
        return path
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        raise ProgramError(
            "UNSAFE_ROOT", "root must be an existing unaliased directory"
        ) from exc


def _path(root: Path, relative: str, *, directory: bool = False) -> Path:
    if (
        not _text(relative, 1024)
        or "\\" in relative
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise ProgramError(
            "UNSAFE_PATH", "path must be canonical and repository-relative"
        )
    path = root
    try:
        parts = relative.split("/")
        for index, part in enumerate(parts):
            path /= part
            mode = path.lstat().st_mode
            want_dir = index < len(parts) - 1 or directory
            if stat.S_ISLNK(mode) or not (
                stat.S_ISDIR(mode) if want_dir else stat.S_ISREG(mode)
            ):
                raise OSError
        if path.resolve(strict=True) != path:
            raise OSError
        if not directory and path.lstat().st_nlink != 1:
            raise OSError
        return path
    except (OSError, ValueError, RuntimeError) as exc:
        raise ProgramError(
            "UNSAFE_PATH",
            "path must resolve to an existing unaliased regular file or directory",
            relative,
        ) from exc


def _signature(info: os.stat_result) -> tuple:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _read(root: Path, relative: str, maximum: int) -> bytes:
    path = _path(root, relative)
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise OSError
        if before.st_size > maximum:
            raise ProgramError(
                "INPUT_TOO_LARGE", "file exceeds its byte limit", relative
            )
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            if _signature(os.fstat(fd)) != _signature(before):
                raise OSError
            chunks, count = [], 0
            while True:
                chunk = os.read(fd, min(65536, maximum + 1 - count))
                if not chunk:
                    break
                count += len(chunk)
                chunks.append(chunk)
                if count > maximum:
                    raise ProgramError(
                        "INPUT_TOO_LARGE", "file exceeds its byte limit", relative
                    )
            if (
                _signature(os.fstat(fd)) != _signature(before)
                or _signature(path.lstat()) != _signature(before)
                or count != before.st_size
            ):
                raise OSError
        finally:
            os.close(fd)
        return b"".join(chunks)
    except OSError as exc:
        raise ProgramError(
            "SOURCE_CHANGED",
            "file changed or became unavailable while reading",
            relative,
        ) from exc


def _criteria(spec_id: str, body: str) -> list[dict]:
    # The shared section helper strips HTML comments before interpreting code
    # spans. Do not let it silently erase a visible comment literal. We do not
    # implement a second inline Markdown parser: conservatively reject mixed
    # comment/code-span syntax in an unfenced paragraph, including wrapped spans.
    unfenced = "\n".join(visible_unfenced_lines(body.splitlines()))
    for paragraph in re.split(r"\n[ \t]*\n", unfenced):
        if "`" in paragraph and ("<!--" in paragraph or "-->" in paragraph):
            raise ProgramError(
                "INVALID_ACCEPTANCE_MARKDOWN",
                "comment syntax and code spans in one unfenced paragraph are unsupported",
                spec_id,
            )
    sections, malformed = markdown_level_two_sections(body)
    candidates = sections.get("Acceptance criteria", [])
    if malformed or len(candidates) != 1:
        raise ProgramError(
            "INVALID_ACCEPTANCE_MARKDOWN",
            "exactly one visible, well-formed Acceptance criteria section is required",
            spec_id,
        )
    lines = visible_unfenced_lines(candidates[0])
    if contains_raw_html_block("\n".join(lines)):
        raise ProgramError(
            "INVALID_ACCEPTANCE_MARKDOWN",
            "raw HTML is unsupported in acceptance criteria",
            spec_id,
        )
    items: list[dict] = []
    paragraph_gap = True
    for line in lines:
        if not line.strip():
            paragraph_gap = True
            continue
        match = _CHECKBOX.fullmatch(line)
        if match:
            items.append(
                {"text": match[2].strip(), "source_checked": match[1].lower() == "x"}
            )
            paragraph_gap = False
        elif (
            items
            and line.startswith("  ")
            and not line.lstrip().startswith(("- ", "+ ", "* ", ">", "#"))
        ):
            items[-1]["text"] += ("\n\n" if paragraph_gap else "\n") + line.strip()
            paragraph_gap = False
        elif re.match(r"\s*(?:[-+*]|[0-9]+[.)]|>)\s", line):
            raise ProgramError(
                "INVALID_ACCEPTANCE_MARKDOWN",
                "acceptance items must be checkboxes with explicit indented continuations",
                spec_id,
            )
        elif items and not paragraph_gap:
            # CommonMark permits lazy unindented paragraph continuation inside
            # the same list item. Dropping it would lose requirement text.
            items[-1]["text"] += "\n" + line.strip()
        if len(items) > MAX_CRITERIA:
            raise ProgramError(
                "TOO_MANY_CRITERIA",
                "acceptance section exceeds its item limit",
                spec_id,
            )
    if not items:
        raise ProgramError(
            "NO_ACCEPTANCE_CRITERIA", "no visible acceptance criteria found", spec_id
        )
    seen = set()
    for item in items:
        if not _text(item["text"]):
            raise ProgramError(
                "INVALID_ACCEPTANCE_MARKDOWN",
                "criterion text is empty or exceeds its UTF-8 byte limit",
                spec_id,
            )
        digest = hashlib.sha256(item["text"].encode("utf-8")).hexdigest()
        if digest in seen:
            raise ProgramError(
                "DUPLICATE_CRITERION",
                "duplicate criterion text cannot have distinct coverage identities",
                spec_id,
            )
        seen.add(digest)
        item.update(
            id=f"{spec_id}:ac:{digest}",
            text_digest=f"sha256:{digest}",
            state="unassessed",
        )
    return items


def _dependencies(record) -> tuple[list[str], dict[str, int]]:
    value = record.metadata.get("Depends on")
    dependencies = (
        [] if value == "none" else value.split(", ") if type(value) is str else []
    )
    if (
        value is None
        or len(set(dependencies)) != len(dependencies)
        or any(not _SPEC_ID.fullmatch(item) for item in dependencies)
    ):
        raise ProgramError(
            "INVALID_DEPENDENCIES",
            "dependency metadata must contain unique canonical spec IDs",
            record.path,
        )
    bound = record.metadata.get("Dependency revisions", "none")
    revisions = {}
    for item in [] if bound == "none" else bound.split(", "):
        match = _BINDING.fullmatch(item)
        if not match or match[1] in revisions or len(match[2]) > 16:
            raise ProgramError(
                "INVALID_DEPENDENCIES",
                "dependency revision bindings are malformed or repeated",
                record.path,
            )
        revisions[match[1]] = int(match[2])
        if revisions[match[1]] > 2**53 - 1:
            raise ProgramError(
                "INVALID_DEPENDENCIES",
                "dependency revision exceeds the integer-only range",
                record.path,
            )
    if revisions and set(revisions) != set(dependencies):
        raise ProgramError(
            "INVALID_DEPENDENCIES",
            "declared revision bindings must cover the direct dependencies",
            record.path,
        )
    return dependencies, revisions


def _topological(specs: dict[str, dict]) -> list[str]:
    remaining = {key: set(item["dependencies"]) for key, item in specs.items()}
    if any(deps - specs.keys() for deps in remaining.values()):
        raise ProgramError(
            "MISSING_DEPENDENCY",
            "a specification dependency is absent from the current program",
        )
    order = []
    while remaining:
        ready = sorted(key for key, deps in remaining.items() if not deps)
        if not ready:
            raise ProgramError(
                "DEPENDENCY_CYCLE", "specification dependency graph contains a cycle"
            )
        for key in ready:
            order.append(key)
            del remaining[key]
        for deps in remaining.values():
            deps.difference_update(ready)
    return order


def build_program(root: Path) -> dict:
    """Observe current spec bytes without consulting Git or granting authority."""
    root = _root(root)
    directory = _path(root, "docs/specs", directory=True)
    paths = []
    for count, path in enumerate(directory.iterdir(), 1):
        if count > MAX_DIRECTORY_ENTRIES:
            raise ProgramError(
                "TOO_MANY_FILES", "specification directory exceeds its entry limit"
            )
        if (
            not path.name.startswith("SPEC-")
            or not path.name.endswith(".md")
            or path.name == "SPEC-TEMPLATE.md"
        ):
            continue
        relative = path.relative_to(root).as_posix()
        if not SPEC_PATH_RE.fullmatch(relative):
            raise ProgramError(
                "INVALID_SPEC_PATH", "specification filename is malformed", relative
            )
        paths.append(relative)
    if not paths or len(paths) > MAX_SPECS:
        raise ProgramError(
            "INVALID_SPEC_COUNT",
            "program must contain a bounded nonempty specification set",
        )
    specs, total_bytes, total_criteria = {}, 0, 0
    for relative in sorted(paths):
        body = _read(root, relative, MAX_SPEC_BYTES)
        total_bytes += len(body)
        if total_bytes > MAX_SOURCE_BYTES:
            raise ProgramError(
                "INPUT_TOO_LARGE", "program source bytes exceed their combined limit"
            )
        try:
            # Reuse the temporal validator's parser on the bounded byte snapshot;
            # its unbounded path-reading loader is deliberately not used here.
            record = parse_spec_revision(relative, body, allow_legacy=False)
        except ValueError as exc:
            raise ProgramError(
                "INVALID_SPEC", "specification header or encoding is invalid", relative
            ) from exc
        if (
            not Path(relative).name.startswith(record.spec_id + "-")
            or record.spec_id in specs
            or record.metadata["Revision"] != str(record.revision)
            or record.revision > 2**53 - 1
            or not _text(record.title)
        ):
            raise ProgramError(
                "INVALID_SPEC_IDENTITY",
                "specification identity is duplicated or noncanonical",
                relative,
            )
        dependencies, revisions = _dependencies(record)
        criteria = _criteria(record.spec_id, body.decode("utf-8"))
        total_criteria += len(criteria)
        if total_criteria > MAX_TOTAL_CRITERIA:
            raise ProgramError(
                "TOO_MANY_CRITERIA",
                "program criterion count exceeds its combined limit",
            )
        specs[record.spec_id] = dict(
            id=record.spec_id,
            title=record.title,
            path=relative,
            revision=record.revision,
            status=record.status,
            source_digest=record.digest,
            dependencies=dependencies,
            dependency_revisions=revisions,
            blockers=[],
            criteria=criteria,
        )
    order = _topological(specs)
    for item in specs.values():
        blockers = [{"code": "default_branch_authority_unverified", "dependency": None}]
        if item["status"] in TERMINAL_STATUSES:
            blockers.append(
                {"code": "terminal_revision_not_active", "dependency": None}
            )
        elif STAGE_RANK[item["status"]] < STAGE_RANK["accepted"]:
            blockers.append({"code": "implementation_not_accepted", "dependency": None})
        for dependency in item["dependencies"]:
            target = specs[dependency]
            if target["status"] in TERMINAL_STATUSES:
                code = "dependency_terminal_revision"
            elif STAGE_RANK[target["status"]] < STAGE_RANK["accepted"]:
                code = "dependency_not_accepted"
            else:
                code = None
            if code:
                blockers.append({"code": code, "dependency": dependency})
            if (
                dependency in item["dependency_revisions"]
                and item["dependency_revisions"][dependency] != target["revision"]
            ):
                blockers.append(
                    {"code": "dependency_revision_mismatch", "dependency": dependency}
                )
        item["blockers"] = blockers
    return {
        "schema": "spec-program-observation/v1",
        "authority": "none",
        "production_ready": False,
        "topological_order": order,
        "specs": [specs[key] for key in sorted(specs)],
    }


def _snapshot(plan: Any) -> dict:
    if type(plan) is not dict:
        raise ProgramError(
            "INVALID_PLAN_JSON", "plan must be an integer-only JSON object"
        )
    pending, count = [(plan, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > 24 or count > 100000:
            raise ProgramError("PLAN_TOO_LARGE", "plan exceeds structural limits")
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ProgramError("INVALID_PLAN_JSON", "object keys must be strings")
            pending.extend((value, depth + 1) for value in item.values())
        elif type(item) is list:
            pending.extend((value, depth + 1) for value in item)
        elif type(item) not in {str, int, bool, type(None)}:
            raise ProgramError(
                "INVALID_PLAN_JSON", "plan must contain only integer-only JSON values"
            )
    try:
        body = canonicalize(plan)
        if len(body) > MAX_PLAN_BYTES:
            raise ProgramError(
                "PLAN_TOO_LARGE", "plan exceeds its canonical byte limit"
            )
        return parse_json_strict(body.decode("utf-8"))
    except (ContractError, RecursionError, UnicodeError) as exc:
        raise ProgramError(
            "INVALID_PLAN_JSON", "plan must contain bounded integer-only UTF-8 JSON"
        ) from exc


def validate_plan(plan: Any, root: Path) -> list[dict]:
    """Check exact coverage/bindings and planning fields, never completion."""
    findings = []

    def finding(code, path, message):
        findings.append({"code": code, "path": path, "message": message})

    def keys(value, expected, path):
        valid = type(value) is dict and set(value) == set(expected)
        if not valid:
            finding(
                "PLAN_KEYS_INVALID",
                path,
                "object must have exactly the declared fields",
            )
        return valid

    def text_field(value, path):
        if not _text(value):
            finding(
                "PLAN_TEXT_INVALID",
                path,
                "planning text must be nonblank bounded UTF-8",
            )

    def covered(items, expected, path):
        if type(items) is not list or len(items) != len(expected):
            finding(
                "PLAN_COVERAGE_INVALID",
                path,
                "list must cover every current identity exactly once",
            )
            return {}
        indexed = {}
        for item in items:
            if (
                type(item) is not dict
                or type(item.get("id")) is not str
                or item["id"] in indexed
            ):
                finding(
                    "PLAN_COVERAGE_INVALID",
                    path,
                    "identities must be unique declared strings",
                )
                return {}
            indexed[item["id"]] = item
        if set(indexed) != {item["id"] for item in expected}:
            finding(
                "PLAN_COVERAGE_INVALID",
                path,
                "list contains missing or extra identities",
            )
            return {}
        return indexed

    try:
        value = _snapshot(plan)
        program = build_program(root)
        root = _root(root)
        if not keys(value, program, "plan"):
            return findings
        for key in set(program) - {"schema", "specs"}:
            if canonicalize(value[key]) != canonicalize(program[key]):
                finding(
                    "PLAN_SOURCE_DRIFT",
                    key,
                    "field must equal the current non-authoritative program observation",
                )
        if value["schema"] != "spec-execution-plan/v1":
            finding("PLAN_SCHEMA_INVALID", "schema", "unknown plan schema")
        indexed = covered(value["specs"], program["specs"], "specs")
        for expected in program["specs"]:
            spec_id = expected["id"]
            if spec_id not in indexed:
                continue
            item = indexed[spec_id]
            if not keys(
                item, set(expected) | {"objective", "code_paths", "slices"}, spec_id
            ):
                continue
            for key in set(expected) - {"criteria"}:
                if canonicalize(item[key]) != canonicalize(expected[key]):
                    finding(
                        "PLAN_SOURCE_DRIFT",
                        f"{spec_id}.{key}",
                        "source or derived field differs from the current specification",
                    )
            text_field(item["objective"], f"{spec_id}.objective")
            paths = item["code_paths"]
            if (
                type(paths) is not list
                or len(paths) > 128
                or any(type(p) is not str for p in paths)
                or len(set(paths)) != len(paths)
            ):
                finding(
                    "PLAN_PATHS_INVALID",
                    f"{spec_id}.code_paths",
                    "code paths must be a bounded unique list; empty means no existing touchpoint",
                )
            else:
                for path in paths:
                    try:
                        _path(root, path)
                    except ProgramError:
                        finding(
                            "PLAN_PATHS_INVALID",
                            f"{spec_id}.code_paths",
                            "code path is absent, aliased, nonregular, or outside root",
                        )
            slices = item["slices"]
            if type(slices) is not list or not 1 <= len(slices) <= 16:
                finding(
                    "PLAN_SLICES_INVALID",
                    f"{spec_id}.slices",
                    "one to sixteen ordered slices are required",
                )
            else:
                seen = set()
                for index, entry in enumerate(slices):
                    location = f"{spec_id}.slices[{index}]"
                    if not keys(
                        entry,
                        {"id", "deliverable", "verification", "rollback"},
                        location,
                    ):
                        continue
                    name = entry["id"]
                    if not _text(name, 64) or not _SLUG.fullmatch(name) or name in seen:
                        finding(
                            "PLAN_SLICES_INVALID",
                            location,
                            "slice ID must be a unique bounded slug",
                        )
                    else:
                        seen.add(name)
                    for key in ("deliverable", "verification", "rollback"):
                        text_field(entry[key], f"{location}.{key}")
            criteria = covered(
                item["criteria"], expected["criteria"], f"{spec_id}.criteria"
            )
            for criterion in expected["criteria"]:
                entry = criteria.get(criterion["id"])
                if entry is None or not keys(
                    entry, set(criterion) | {"verification_method"}, criterion["id"]
                ):
                    continue
                for key in criterion:
                    if canonicalize(entry[key]) != canonicalize(criterion[key]):
                        finding(
                            "PLAN_CRITERION_DRIFT",
                            criterion["id"],
                            "criterion identity/text/checkbox/state must match the unassessed source observation",
                        )
                text_field(
                    entry["verification_method"],
                    criterion["id"] + ".verification_method",
                )
    except ProgramError as exc:
        finding(exc.code, exc.path or "plan", str(exc))
    return sorted(
        findings, key=lambda item: (item["path"], item["code"], item["message"])
    )


def _template(root: Path) -> dict:
    program = build_program(root)
    program["schema"] = "spec-execution-plan/v1"
    for item in program["specs"]:
        item.update(
            objective="",
            code_paths=[],
            slices=[
                {
                    "id": "first-slice",
                    "deliverable": "",
                    "verification": "",
                    "rollback": "",
                }
            ],
        )
        for criterion in item["criteria"]:
            criterion["verification_method"] = ""
    return program


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ProgramError(
            "INVALID_ARGUMENTS",
            "expected plan or check with --root and a repository-relative plan path",
        )


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(add_help=False)
    parser.add_argument("command", choices=("plan", "check"))
    parser.add_argument("plan_path", nargs="?")
    parser.add_argument("--root", type=Path, default=ROOT)
    try:
        args = parser.parse_args(argv)
        if args.command == "plan":
            if args.plan_path is not None:
                raise ProgramError(
                    "INVALID_ARGUMENTS",
                    "plan prints a blank invalid template; it takes no output path",
                )
            result, exit_code = _template(args.root), 0
        else:
            if args.plan_path is None:
                raise ProgramError(
                    "INVALID_ARGUMENTS",
                    "check requires a repository-relative plan path",
                )
            body = _read(_root(args.root), args.plan_path, MAX_PLAN_BYTES)
            try:
                value = parse_json_strict(body.decode("utf-8"))
            except (ContractError, RecursionError, UnicodeError) as exc:
                raise ProgramError(
                    "INVALID_PLAN_JSON",
                    "plan file must be strict integer-only UTF-8 JSON",
                ) from exc
            findings = validate_plan(value, args.root)
            result = {
                "authority": "none",
                "production_ready": False,
                "findings": findings,
            }
            exit_code = 1 if findings else 0
    except ProgramError as exc:
        result = {
            "authority": "none",
            "production_ready": False,
            "findings": [{"code": exc.code, "path": exc.path, "message": str(exc)}],
        }
        exit_code = 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
