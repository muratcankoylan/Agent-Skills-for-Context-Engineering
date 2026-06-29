#!/usr/bin/env python3
"""Validate platform compatibility for the published Agent Skills corpus.

This script checks the parts of Cursor, Claude Code, Codex, and Open Plugins
compatibility that are deterministic from the repository contents:

- Published skills are strict-YAML parseable and match Agent Skills naming rules.
- Open Plugins and Claude marketplace manifests discover the same skill set.
- Local/manual install layouts preserve `skill-name/SKILL.md` under the platform
  skill roots documented by Cursor, Claude Code, and Codex.
- If the upstream `agentskills` CLI from `skills-ref` is installed, each skill is
  validated with the reference Agent Skills validator as well.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from skill_frontmatter import parse_frontmatter


ROOT = Path(__file__).resolve().parents[2]
PLATFORM_SKILL_ROOTS = [
    ".cursor/skills",
    ".claude/skills",
    ".codex/skills",
    ".agents/skills",
]


def error(message: str, errors: list[str]) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        error(f"{path.relative_to(ROOT)}: {exc}", errors)
        return {}
    if not isinstance(data, dict):
        error(f"{path.relative_to(ROOT)}: expected JSON object", errors)
        return {}
    return data


def published_skill_dirs() -> list[Path]:
    return sorted(path for path in (ROOT / "skills").iterdir() if (path / "SKILL.md").exists())


def validate_skill_dir(skill_dir: Path, errors: list[str]) -> None:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        error(f"{skill_dir}: missing SKILL.md", errors)
        return
    data, issues = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
    for issue in issues:
        error(f"{skill_file.relative_to(ROOT)}: {issue}", errors)
    name = str(data.get("name", ""))
    if name != skill_dir.name:
        error(f"{skill_file.relative_to(ROOT)}: name {name!r} does not match directory {skill_dir.name!r}", errors)


def validate_manifests(skill_names: list[str], errors: list[str]) -> None:
    plugin_dir = ROOT / ".plugin"
    plugin_path = plugin_dir / "plugin.json"
    plugin = load_json(plugin_path, errors)
    unexpected = sorted(path.name for path in plugin_dir.iterdir() if path.name != "plugin.json")
    if unexpected:
        error(f".plugin/ must contain only plugin.json, found: {unexpected}", errors)

    raw_skills = plugin.get("skills")
    if isinstance(raw_skills, str):
        skill_paths = [raw_skills]
    elif isinstance(raw_skills, list) and all(isinstance(item, str) for item in raw_skills):
        skill_paths = list(raw_skills)
    else:
        error(".plugin/plugin.json: skills must be a string or list of strings", errors)
        skill_paths = []

    discovered: set[str] = set()
    for raw_path in skill_paths:
        path = Path(raw_path)
        if not raw_path.startswith("./"):
            error(f".plugin/plugin.json: skill path must start with './': {raw_path}", errors)
            continue
        if path.is_absolute() or ".." in path.parts:
            error(f".plugin/plugin.json: skill path escapes plugin root: {raw_path}", errors)
            continue
        full_path = ROOT / raw_path
        if not full_path.exists():
            error(f".plugin/plugin.json: skill path does not exist: {raw_path}", errors)
            continue
        if (full_path / "SKILL.md").exists():
            discovered.add(full_path.name)
        elif full_path.is_dir():
            discovered.update(path.name for path in full_path.iterdir() if (path / "SKILL.md").exists())
        else:
            error(f".plugin/plugin.json: skill path is not a directory: {raw_path}", errors)
    if sorted(discovered) != skill_names:
        error(f".plugin/plugin.json: discovered skills {sorted(discovered)} != corpus {skill_names}", errors)

    marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json", errors)
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        error(".claude-plugin/marketplace.json: expected exactly one bundled plugin", errors)
        return
    entry = plugins[0]
    if not isinstance(entry, dict):
        error(".claude-plugin/marketplace.json: plugin entry must be an object", errors)
        return
    if entry.get("name") != plugin.get("name"):
        error(".claude-plugin/marketplace.json: plugin name differs from .plugin/plugin.json", errors)
    if entry.get("source") != "./":
        error(".claude-plugin/marketplace.json: source must be './'", errors)
    claude_skill_paths = entry.get("skills")
    if not isinstance(claude_skill_paths, list) or not all(isinstance(item, str) for item in claude_skill_paths):
        error(".claude-plugin/marketplace.json: skills must be a list of strings", errors)
        return
    claude_names = []
    for raw_path in claude_skill_paths:
        if not raw_path.startswith("./"):
            error(f".claude-plugin/marketplace.json: skill path must start with './': {raw_path}", errors)
            continue
        path = ROOT / raw_path
        if not (path / "SKILL.md").exists():
            error(f".claude-plugin/marketplace.json: skill path missing SKILL.md: {raw_path}", errors)
            continue
        claude_names.append(path.name)
    if sorted(claude_names) != skill_names:
        error(f".claude-plugin/marketplace.json: discovered skills {sorted(claude_names)} != corpus {skill_names}", errors)


def validate_platform_install_layouts(skill_dirs: list[Path], errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="skill-platform-compat-") as tmp:
        root = Path(tmp)
        for platform_root in PLATFORM_SKILL_ROOTS:
            target_root = root / platform_root
            target_root.mkdir(parents=True, exist_ok=True)
            for skill_dir in skill_dirs:
                target = target_root / skill_dir.name
                shutil.copytree(skill_dir, target)
                validate_skill_dir(target, errors)


def run_reference_validator(skill_dirs: list[Path], require: bool, errors: list[str]) -> None:
    agentskills = shutil.which("agentskills")
    if agentskills is None:
        if require:
            error("agentskills CLI not found; install with `python -m pip install skills-ref`", errors)
        return

    for skill_dir in skill_dirs:
        completed = subprocess.run(
            [agentskills, "validate", str(skill_dir)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
            error(f"agentskills validate {skill_dir.relative_to(ROOT)} failed: {message}", errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate cross-platform Agent Skills compatibility")
    parser.add_argument(
        "--require-reference-validator",
        action="store_true",
        help="Fail if the official agentskills CLI from skills-ref is unavailable.",
    )
    args = parser.parse_args()

    errors: list[str] = []
    skill_dirs = published_skill_dirs()
    skill_names = sorted(path.name for path in skill_dirs)
    if not skill_dirs:
        error("no published skills found under skills/", errors)

    for skill_dir in skill_dirs:
        validate_skill_dir(skill_dir, errors)
    validate_manifests(skill_names, errors)
    validate_platform_install_layouts(skill_dirs, errors)
    run_reference_validator(skill_dirs, args.require_reference_validator, errors)

    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1

    print(
        "Platform compatibility passed: "
        f"{len(skill_dirs)} skills, {len(PLATFORM_SKILL_ROOTS)} local install layouts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
