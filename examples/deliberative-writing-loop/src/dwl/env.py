"""Minimal .env loader (stdlib only, no python-dotenv dependency).

Precedence rule, deliberately one-directional: variables already present in the
real environment are never overwritten. A platform-injected secret or an
exported shell variable therefore always beats a stale local .env file, which is
the safe direction for credentials.
"""

from __future__ import annotations

import os
from pathlib import Path

_MASK_TAIL = 4


def parse_env_text(text: str) -> dict[str, str]:
    """Parse KEY=value lines. Supports `export` prefixes, quotes, and comments.

    Blank values are kept as empty strings so a placeholder in .env.example does
    not masquerade as a configured key.
    """
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        else:
            # Strip trailing inline comments only on unquoted values.
            hash_index = value.find(" #")
            if hash_index != -1:
                value = value[:hash_index].rstrip()
        values[key] = value
    return values


def find_env_file(start: Path | None = None, filename: str = ".env") -> Path | None:
    """Search the start directory and its parents for an env file."""
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def load_env(path: Path | None = None, override: bool = False) -> dict[str, str]:
    """Load an env file into os.environ. Returns the keys actually applied.

    Missing files are not an error: keys may legitimately come from the real
    environment instead.
    """
    env_path = path or find_env_file()
    if env_path is None or not env_path.is_file():
        return {}
    applied: dict[str, str] = {}
    for key, value in parse_env_text(env_path.read_text(encoding="utf-8")).items():
        if not value:
            continue
        if not override and os.environ.get(key):
            continue
        os.environ[key] = value
        applied[key] = value
    return applied


def mask(value: str) -> str:
    """Render a secret for logs: last 4 characters only, never the full value."""
    if not value:
        return "<unset>"
    if len(value) <= _MASK_TAIL:
        return "*" * len(value)
    return f"...{value[-_MASK_TAIL:]}"


def key_status() -> dict[str, str]:
    """Masked presence report for the keys this project reads."""
    return {
        name: mask(os.environ.get(name, ""))
        for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PANGRAM_API_KEY")
    }
