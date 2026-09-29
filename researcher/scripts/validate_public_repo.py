#!/usr/bin/env python3
"""Fail closed on tracked files that expose developer-local or credential material.

This deterministic gate complements, rather than replaces, Gitleaks. It owns
repository-specific invariants that entropy-based scanners do not reliably
model: public files cannot contain workstation paths, credential-bearing file
names, or private-key blocks. Only Git-tracked paths are release inputs.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]

LOCAL_PATH_PATTERNS = (
    re.compile(
        r"(?<![A-Za-z0-9])/(?:mnt/[a-z]/)?(?:Users|home)/[A-Za-z0-9._-]+(?:/|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9])/(?:private/(?:var|tmp)|var/folders)/[^\s`'\"]+",
        re.IGNORECASE,
    ),
    re.compile(r"(?i)(?:[A-Z]:\\|\\\\)[Uu]sers\\[A-Za-z0-9._-]+\\"),
)
PRIVATE_KEY_PATTERN = re.compile(
    "-----BEGIN "
    + r"(?:(?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY|PGP PRIVATE KEY BLOCK)"
    + "-----"
)
ALLOWED_ENV_EXAMPLES = {".env.example", ".env.sample", ".env.template"}
FORBIDDEN_EXACT_NAMES = {
    "credentials.json",
    "service-account.json",
    "service_account.json",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
}
FORBIDDEN_SUFFIXES = {".key", ".p12", ".pfx", ".pem"}
FORBIDDEN_TRACKED_PREFIXES = (
    ".cursor/",
    ".specstory/",
    "Private/",
    "dashboard/",
    "outputs/",
    "researcher/artifacts/private/",
    "researcher/benchmarks/effectiveness/results/",
    "researcher/benchmarks/router/results/",
    "researcher/benchmarks/sdk-runner/dist/",
    "researcher/benchmarks/sdk-runner/node_modules/",
    "researcher/exports/private/",
    "researcher/exports/staging/",
    "researcher/queue/.locks/",
    "researcher/reports/jsonl-quarantine/",
    "researcher/reports/logs/",
    "researcher/reports/snapshots/",
    "researcher/schemas/reports/runtime/",
)
FORBIDDEN_TRACKED_PATHS = {
    "researcher/queue/done.jsonl",
    "researcher/queue/inbox.jsonl",
    "researcher/queue/parked.jsonl",
    "researcher/queue/quarantine.jsonl",
    "researcher/reports/effectiveness-history.jsonl",
    "researcher/reports/loop-events.jsonl",
    "researcher/reports/loop-failures.jsonl",
    "researcher/reports/parked-review.md",
    "researcher/reports/router-history.jsonl",
    "researcher/reports/skill-health-history.jsonl",
    "researcher/reports/skill-health.json",
    "researcher/reports/status.md",
}
PUBLIC_RUN_PATH = "researcher/runs/README.md"
PUBLIC_SEED_RUN_PREFIX = "researcher/runs/20260515-035228-executable-autonomous-research-frameworks/"
FORBIDDEN_TRACKED_PREFIX_KEYS = tuple(prefix.casefold() for prefix in FORBIDDEN_TRACKED_PREFIXES)
FORBIDDEN_TRACKED_PATH_KEYS = frozenset(path.casefold() for path in FORBIDDEN_TRACKED_PATHS)
TEXT_SUFFIXES = {
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".html",
    ".in",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".lock",
    ".md",
    ".py",
    ".rst",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
TEXT_EXACT_NAMES = {".gitattributes", ".gitignore", "Dockerfile", "LICENSE", "Makefile"}
NON_TEXT_CONTROL_BYTES = frozenset(range(0x00, 0x09)) | frozenset({0x0B}) | frozenset(
    range(0x0E, 0x20)
) | frozenset({0x7F})


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    path: str
    line: int | None
    message: str


def tracked_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed: {detail}")
    return sorted(path.decode("utf-8") for path in result.stdout.split(b"\0") if path)


def _safe_path(root: Path, relative: str) -> tuple[Path | None, Finding | None]:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts or relative != posix.as_posix():
        return None, Finding("TRACKED_PATH_ESCAPE", relative, None, "tracked path is not normalized")
    lexical = root / relative
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None, Finding("TRACKED_PATH_ESCAPE", relative, None, "tracked path escapes or is missing")
    if lexical.is_symlink() or not resolved.is_file():
        return None, Finding("TRACKED_PATH_ESCAPE", relative, None, "tracked input is not a regular file")
    return resolved, None


def _forbidden_name(path: PurePosixPath) -> str | None:
    name = path.name.lower()
    if name == ".env" or (name.startswith(".env.") and name not in ALLOWED_ENV_EXAMPLES):
        return "environment file"
    if name in FORBIDDEN_EXACT_NAMES:
        return "credential or secret file"
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return "private key or certificate container"
    return None


def _is_forbidden_runtime_path(relative: str) -> bool:
    policy_path = relative.casefold()
    if policy_path in FORBIDDEN_TRACKED_PATH_KEYS or policy_path.startswith(
        FORBIDDEN_TRACKED_PREFIX_KEYS
    ):
        return True
    if not policy_path.startswith("researcher/runs/"):
        return False
    return relative != PUBLIC_RUN_PATH and not relative.startswith(PUBLIC_SEED_RUN_PREFIX)


def _is_text_like(path: PurePosixPath) -> bool:
    name = path.name
    return (
        name in TEXT_EXACT_NAMES
        or name.casefold().startswith(".env.")
        or path.suffix.casefold() in TEXT_SUFFIXES
    )


def validate_public_tree(root: Path, paths: Sequence[str]) -> list[Finding]:
    root = root.resolve()
    findings: list[Finding] = []
    seen: set[str] = set()
    for relative in sorted(paths):
        if relative in seen:
            findings.append(Finding("DUPLICATE_TRACKED_PATH", relative, None, "path appears more than once"))
            continue
        seen.add(relative)
        normalized = PurePosixPath(relative)
        if _is_forbidden_runtime_path(relative):
            findings.append(
                Finding(
                    "FORBIDDEN_PRIVATE_PATH",
                    relative,
                    None,
                    "local drafting or private root cannot be tracked",
                )
            )
        forbidden = _forbidden_name(normalized)
        if forbidden:
            findings.append(Finding("FORBIDDEN_CREDENTIAL_FILE", relative, None, forbidden))
        path, path_finding = _safe_path(root, relative)
        if path_finding:
            findings.append(path_finding)
            continue
        assert path is not None
        body = path.read_bytes()
        if _is_text_like(normalized) and any(byte in NON_TEXT_CONTROL_BYTES for byte in body):
            findings.append(
                Finding(
                    "NON_UTF8_TEXT_FILE",
                    relative,
                    None,
                    "tracked text-like file contains a non-text control byte",
                )
            )
            continue
        if b"\0" in body:
            continue
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            if _is_text_like(normalized):
                findings.append(
                    Finding(
                        "NON_UTF8_TEXT_FILE",
                        relative,
                        None,
                        "tracked text-like file is not valid UTF-8",
                    )
                )
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in LOCAL_PATH_PATTERNS):
                findings.append(
                    Finding(
                        "PRIVATE_LOCAL_PATH",
                        relative,
                        line_number,
                        "tracked text contains a developer-local absolute path",
                    )
                )
            if PRIVATE_KEY_PATTERN.search(line):
                findings.append(
                    Finding(
                        "PRIVATE_KEY_MATERIAL",
                        relative,
                        line_number,
                        "tracked text contains a private-key block header",
                    )
                )
    return sorted(findings)


def print_findings(findings: Iterable[Finding]) -> None:
    for finding in findings:
        location = f"{finding.path}:{finding.line}" if finding.line else finding.path
        print(f"[{finding.code}] {location}: {finding.message}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        paths = tracked_paths(root)
        findings = validate_public_tree(root, paths)
    except (OSError, RuntimeError) as exc:
        print(f"[PUBLIC_REPO_SCAN_FAILED] {exc}", file=sys.stderr)
        return 1
    if findings:
        print_findings(findings)
        print(f"Public repository validation failed: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    print(f"Public repository validation passed: {len(paths)} tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
