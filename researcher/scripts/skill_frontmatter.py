"""Shared SKILL.md frontmatter parsing for researcher validation scripts."""

from __future__ import annotations

import json
import re
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is stdlib-adjacent in CI via setup
    yaml = None  # type: ignore[assignment]

MIN_DESCRIPTION_LENGTH = 20
YAML_INDICATOR_ONLY = re.compile(r"^[>|]?-?$")


def strip_bom(text: str) -> str:
    return text[1:] if text.startswith("\ufeff") else text


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_inner, body). Inner block excludes --- delimiters."""
    text = strip_bom(text)
    if not (text.startswith("---\n") or text.startswith("---\r\n")):
        return None, text

    delimiter_len = 5 if text.startswith("---\r\n") else 4
    match = re.search(r"(?m)^---\s*$", text[delimiter_len:])
    if match is None:
        return None, text

    end = delimiter_len + match.start()
    inner = text[delimiter_len:end].rstrip("\r")
    body = text[delimiter_len + match.end() :]
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    return inner, body


def parse_frontmatter(text: str) -> tuple[dict[str, Any], list[str]]:
    """Parse SKILL.md frontmatter with strict YAML when available."""
    issues: list[str] = []
    inner, _body = split_frontmatter(text)
    if inner is None:
        return {}, ["missing or invalid frontmatter delimiters"]

    if yaml is None:
        return _parse_frontmatter_fallback(inner, issues)

    try:
        data = yaml.safe_load(inner)
    except yaml.YAMLError as exc:
        issues.append(f"invalid YAML frontmatter: {exc}")
        return {}, issues

    if not isinstance(data, dict):
        issues.append("frontmatter must be a YAML mapping")
        return {}, issues

    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        normalized[str(key)] = value

    _validate_required_fields(normalized, issues)
    return normalized, issues


def _parse_frontmatter_fallback(inner: str, issues: list[str]) -> tuple[dict[str, Any], list[str]]:
    """Line-based fallback when PyYAML is unavailable."""
    data: dict[str, Any] = {}
    in_description = False
    description_lines: list[str] = []

    for raw in inner.splitlines():
        line = raw.rstrip("\r")
        if in_description:
            if re.match(r"^[A-Za-z0-9_-]+:", line):
                data["description"] = " ".join(description_lines).strip()
                in_description = False
            else:
                trimmed = line.strip()
                if trimmed and trimmed not in (">", ">-", "|", "|-"):
                    description_lines.append(trimmed)
                continue

        if not line.strip() or line.startswith(" "):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key == "description" and value in (">", ">-", "|", "|-", ""):
            in_description = True
            continue
        data[key] = value

    if in_description:
        data["description"] = " ".join(description_lines).strip()

    _validate_required_fields(data, issues)
    return data, issues


def _validate_required_fields(data: dict[str, Any], issues: list[str]) -> None:
    raw_name = data.get("name", "")
    raw_description = data.get("description", "")

    if raw_name and not isinstance(raw_name, str):
        issues.append(f"name must be a string, got {type(raw_name).__name__}")
        name = ""
    else:
        name = str(raw_name).strip()

    if raw_description and not isinstance(raw_description, str):
        issues.append(f"description must be a string, got {type(raw_description).__name__}")
        description = ""
    else:
        description = str(raw_description).strip()

    if not name:
        issues.append("missing name")
    if not description:
        issues.append("missing description")
    elif len(description) < MIN_DESCRIPTION_LENGTH:
        issues.append(f"description too short ({len(description)} chars)")
    elif YAML_INDICATOR_ONLY.match(description):
        issues.append("description parsed as YAML indicator only")


def format_frontmatter(name: str, description: str, **extra: str) -> str:
    """Render a standards-compliant frontmatter block."""
    lines = [f"name: {name}", f"description: {json.dumps(description, ensure_ascii=False)}"]
    for key, value in extra.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    return "---\n" + "\n".join(lines) + "\n---\n"
