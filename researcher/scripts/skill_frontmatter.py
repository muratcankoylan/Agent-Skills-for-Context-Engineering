"""Shared SKILL.md frontmatter parsing for researcher validation scripts."""

from __future__ import annotations

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
    # A closing fence is a line that is exactly "---" (optionally CR-terminated).
    # Searching for "\n---" matches both LF and CRLF inputs because CRLF contains
    # a trailing "\n" before the fence.
    end = text.find("\n---", delimiter_len)
    if end == -1:
        return None, text

    inner = text[delimiter_len:end].rstrip("\r")
    body = text[end + 4 :]
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
        if isinstance(value, str):
            normalized[str(key)] = value
        else:
            normalized[str(key)] = str(value)

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
    name = str(data.get("name", "")).strip()
    description = str(data.get("description", "")).strip()

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
    if yaml is None:
        escaped = description.replace("\\", "\\\\").replace('"', '\\"')
        lines = [f"name: {name}", f'description: "{escaped}"']
        for key, value in extra.items():
            escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key}: "{escaped_value}"')
        return "---\n" + "\n".join(lines) + "\n---\n"

    payload: dict[str, str] = {"name": name, "description": description}
    payload.update(extra)
    dumped = yaml.safe_dump(
        payload,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    ).strip()
    return f"---\n{dumped}\n---\n"
