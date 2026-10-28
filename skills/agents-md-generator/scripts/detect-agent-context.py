#!/usr/bin/env python3
"""Build a deterministic, read-only evidence index for AGENTS.md generation."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional


SCHEMA_VERSION = 2
MAX_MANIFEST_BYTES = 2 * 1024 * 1024

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".next",
    ".nuxt",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".yarn",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}

MANIFEST_NAMES = {
    "Cargo.toml",
    "Gemfile",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "deno.json",
    "deno.jsonc",
    "go.mod",
    "mix.exs",
    "package.json",
    "pom.xml",
    "pubspec.yaml",
    "pyproject.toml",
    "requirements.txt",
    "settings.gradle",
    "settings.gradle.kts",
}

LOCKFILE_MANAGERS = {
    "Cargo.lock": "cargo",
    "Pipfile.lock": "pipenv",
    "bun.lock": "bun",
    "bun.lockb": "bun",
    "composer.lock": "composer",
    "deno.lock": "deno",
    "go.sum": "go",
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "poetry.lock": "poetry",
    "pubspec.lock": "flutter",
    "uv.lock": "uv",
    "yarn.lock": "yarn",
}

ENVIRONMENT_NAMES = {
    ".mise.toml",
    ".nvmrc",
    ".python-version",
    ".ruby-version",
    ".tool-versions",
    "Dockerfile",
    "Justfile",
    "Makefile",
    "Taskfile.yml",
    "Taskfile.yaml",
    "compose.yml",
    "compose.yaml",
    "docker-compose.yml",
    "docker-compose.yaml",
}

ROOT_CI_NAMES = {
    ".circleci/config.yml",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
}

ROOT_DOC_NAMES = {
    "CONTRIBUTING.md",
    "DEVELOPMENT.md",
    "README.md",
    "SECURITY.md",
}

SOURCE_DIRECTORY_NAMES = {
    "app",
    "apps",
    "backend",
    "cmd",
    "components",
    "frontend",
    "internal",
    "lib",
    "packages",
    "services",
    "src",
    "tests",
}

LEGACY_INSTRUCTION_FILES = {
    ".clinerules": "cline",
    ".cursorrules": "cursor",
    ".kilocoderules": "kilo-code",
    ".roorules": "roo-code",
    ".windsurfrules": "windsurf",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan project metadata and agent instruction sources without reading "
            "secrets or arbitrary source contents."
        )
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository or project root to scan (default: current directory).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=8,
        help="Maximum project traversal depth (default: 8).",
    )
    parser.add_argument(
        "--include-global",
        action="store_true",
        help="Also report known user-level instruction/config paths. Contents are never read.",
    )
    parser.add_argument(
        "--config-path",
        "--mcp-path",
        dest="config_paths",
        action="append",
        default=[],
        help="Additional agent or MCP config path to report (repeatable; contents are not read).",
    )
    return parser.parse_args()


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def add_unique(items: list[dict[str, Any]], item: dict[str, Any]) -> None:
    key = (item.get("path"), item.get("tool"), item.get("kind"))
    if not any(
        (entry.get("path"), entry.get("tool"), entry.get("kind")) == key
        for entry in items
    ):
        items.append(item)


def classify_instruction(relative: str) -> Optional[dict[str, Any]]:
    path = Path(relative)
    name = path.name
    padded = f"/{relative}/"

    if name == "AGENTS.override.md":
        return {"tool": "codex", "kind": "override", "deprecated": False}
    if name == "AGENTS.md":
        return {"tool": "shared", "kind": "instructions", "deprecated": False}
    if name == "CLAUDE.local.md":
        return {"tool": "claude-code", "kind": "local-instructions", "deprecated": False}
    if name == "CLAUDE.md":
        return {"tool": "claude-code", "kind": "instructions", "deprecated": False}
    if name == "GEMINI.md":
        return {"tool": "gemini", "kind": "instructions", "deprecated": False}
    if relative == ".github/copilot-instructions.md":
        return {"tool": "github-copilot", "kind": "instructions", "deprecated": False}
    if relative.startswith(".github/instructions/") and name.endswith(".instructions.md"):
        return {"tool": "github-copilot", "kind": "path-instructions", "deprecated": False}
    if "/.claude/rules/" in padded and path.suffix == ".md":
        return {"tool": "claude-code", "kind": "scoped-rule", "deprecated": False}
    if "/.cursor/rules/" in padded and path.suffix in {".md", ".mdc"}:
        return {"tool": "cursor", "kind": "scoped-rule", "deprecated": False}
    if "/.windsurf/rules/" in padded and path.suffix == ".md":
        return {"tool": "windsurf", "kind": "scoped-rule", "deprecated": False}
    if "/.roo/rules/" in padded and path.suffix in {".md", ".txt"}:
        return {"tool": "roo-code", "kind": "scoped-rule", "deprecated": False}
    if (
        ".roo" in path.parts
        and any(part.startswith("rules-") for part in path.parts)
        and path.suffix in {".md", ".txt"}
    ):
        return {"tool": "roo-code", "kind": "mode-rule", "deprecated": False}
    if "/.kilocode/rules/" in padded or "/.kilo/rules/" in padded:
        if path.suffix in {".md", ".txt"}:
            return {"tool": "kilo-code", "kind": "scoped-rule", "deprecated": False}
    if name in LEGACY_INSTRUCTION_FILES:
        return {
            "tool": LEGACY_INSTRUCTION_FILES[name],
            "kind": "legacy-instructions",
            "deprecated": name == ".cursorrules",
        }
    if name.startswith(".roorules"):
        return {"tool": "roo-code", "kind": "mode-rule", "deprecated": False}
    if name.startswith(".kilocoderules"):
        return {"tool": "kilo-code", "kind": "mode-rule", "deprecated": False}
    if "/.clinerules/" in padded and path.suffix in {".md", ".txt"}:
        return {"tool": "cline", "kind": "scoped-rule", "deprecated": False}
    return None


def classify_config(relative: str) -> Optional[dict[str, str]]:
    config_paths = {
        ".claude/settings.json": ("claude-code", "settings"),
        ".codex/config.toml": ("codex", "settings"),
        ".cursor/mcp.json": ("cursor", "mcp"),
        ".cline/mcp_settings.json": ("cline", "mcp"),
        ".kilocode/mcp.json": ("kilo-code", "mcp"),
        ".kilocode/config.json": ("kilo-code", "settings"),
        ".kilo/config.json": ("kilo-code", "settings"),
        ".mcp.json": ("shared", "mcp"),
        ".roo/mcp.json": ("roo-code", "mcp"),
        ".roo/mcp_settings.json": ("roo-code", "mcp"),
        ".vscode/mcp.json": ("vscode", "mcp"),
        ".kilocodemodes": ("kilo-code", "modes"),
        "cline_mcp_settings.json": ("cline", "mcp"),
        "opencode.json": ("opencode", "settings"),
        "opencode.jsonc": ("opencode", "settings"),
    }
    match = config_paths.get(relative)
    if not match:
        normalized = f"/{relative}"
        match = next(
            (
                value
                for config_path, value in config_paths.items()
                if normalized.endswith(f"/{config_path}")
            ),
            None,
        )
    if not match:
        return None
    return {"tool": match[0], "kind": match[1]}


def walk_project(root: Path, max_depth: int) -> list[Path]:
    files: list[Path] = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_current = current_path.relative_to(root)
        depth = 0 if relative_current == Path(".") else len(relative_current.parts)

        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
        )
        if depth >= max_depth:
            directories.clear()

        for filename in sorted(filenames):
            files.append(current_path / filename)
    return files


def read_json(path: Path, errors: list[str]) -> Optional[dict[str, Any]]:
    try:
        if path.is_symlink():
            errors.append(f"Skipped symlinked manifest: {path}")
            return None
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            errors.append(f"Skipped oversized manifest: {path}")
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"Could not parse {path}: {exc.__class__.__name__}")
        return None
    return data if isinstance(data, dict) else None


def read_selected_text(path: Path, errors: list[str]) -> Optional[str]:
    """Read only an already-selected public manifest, never arbitrary source."""
    try:
        if path.is_symlink():
            errors.append(f"Skipped symlinked manifest: {path}")
            return None
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            errors.append(f"Skipped oversized manifest: {path}")
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Could not read {path}: {exc.__class__.__name__}")
        return None


def is_nonempty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def select_js_manager(
    manifest: str,
    data: dict[str, Any],
    lockfiles: list[dict[str, str]],
    warnings: list[str],
) -> Optional[str]:
    manifest_parent = Path(manifest).parent
    candidates: list[tuple[int, str]] = []
    for entry in lockfiles:
        if entry["manager"] not in {"bun", "npm", "pnpm", "yarn"}:
            continue
        lock_parent = Path(entry["path"]).parent
        if lock_parent == manifest_parent or lock_parent in manifest_parent.parents:
            candidates.append((len(lock_parent.parts), entry["manager"]))

    nearest: list[str] = []
    if candidates:
        nearest_depth = max(depth for depth, _ in candidates)
        nearest = sorted(
            {manager for depth, manager in candidates if depth == nearest_depth}
        )

    declared = data.get("packageManager")
    if isinstance(declared, str):
        match = re.match(r"^(npm|pnpm|yarn|bun)(?:@|$)", declared)
        if match:
            manager = match.group(1)
            if nearest and manager not in nearest:
                warnings.append(
                    f"packageManager in {manifest} declares {manager}, but its nearest "
                    f"lockfile indicates {', '.join(nearest)}; verify before using commands."
                )
                return None
            return manager

    if nearest:
        if len(nearest) == 1:
            return nearest[0]
        warnings.append(
            f"Could not choose a JavaScript package manager for {manifest}; "
            f"nearest lockfiles disagree: {', '.join(nearest)}."
        )
        return None

    warnings.append(
        f"Could not verify a JavaScript package manager for {manifest}; "
        "add packageManager metadata or a lockfile."
    )
    return None


def add_signal(
    signals: list[dict[str, Any]],
    category: str,
    name: str,
    evidence: list[str],
    marker: Optional[str] = None,
) -> None:
    paths = sorted(set(evidence + ([marker] if marker else [])))
    if not paths:
        return
    existing = next(
        (
            item
            for item in signals
            if item["category"] == category and item["name"] == name
        ),
        None,
    )
    if existing:
        existing["evidence"] = sorted(set(existing["evidence"] + paths))
        if marker and evidence:
            existing["confidence"] = "strong"
        return
    signals.append(
        {
            "category": category,
            "name": name,
            "confidence": "strong" if marker and evidence else "declared",
            "evidence": paths,
        }
    )


def dependency_names(data: dict[str, Any], sections: tuple[str, ...]) -> set[str]:
    names: set[str] = set()
    for section in sections:
        values = data.get(section)
        if isinstance(values, dict):
            names.update(key.lower() for key in values if isinstance(key, str))
    return names


def detect_technology_signals(
    root: Path,
    manifests: list[str],
    project_paths: set[str],
    errors: list[str],
) -> list[dict[str, Any]]:
    """Detect declared frameworks and tools from selected public manifests."""
    signals: list[dict[str, Any]] = []

    js_rules = {
        "next": ("framework", "Next.js"),
        "nuxt": ("framework", "Nuxt"),
        "@sveltejs/kit": ("framework", "SvelteKit"),
        "@remix-run/react": ("framework", "Remix"),
        "astro": ("framework", "Astro"),
        "@angular/core": ("framework", "Angular"),
        "react": ("ui-library", "React"),
        "vue": ("ui-framework", "Vue"),
        "svelte": ("ui-framework", "Svelte"),
        "@nestjs/core": ("backend-framework", "NestJS"),
        "express": ("backend-framework", "Express"),
        "fastify": ("backend-framework", "Fastify"),
        "koa": ("backend-framework", "Koa"),
        "vitest": ("test-tool", "Vitest"),
        "jest": ("test-tool", "Jest"),
        "@playwright/test": ("test-tool", "Playwright"),
        "cypress": ("test-tool", "Cypress"),
        "eslint": ("quality-tool", "ESLint"),
        "prettier": ("quality-tool", "Prettier"),
        "typescript": ("language-tool", "TypeScript"),
    }
    composer_rules = {
        "laravel/framework": ("backend-framework", "Laravel"),
        "symfony/framework-bundle": ("backend-framework", "Symfony"),
        "drupal/core-recommended": ("cms", "Drupal"),
        "joomla/cms": ("cms", "Joomla"),
        "roots/wordpress": ("cms", "WordPress"),
        "pestphp/pest": ("test-tool", "Pest"),
        "phpunit/phpunit": ("test-tool", "PHPUnit"),
        "laravel/pint": ("quality-tool", "Laravel Pint"),
        "friendsofphp/php-cs-fixer": ("quality-tool", "PHP CS Fixer"),
        "phpstan/phpstan": ("quality-tool", "PHPStan"),
        "vimeo/psalm": ("quality-tool", "Psalm"),
    }
    text_rules: dict[str, list[tuple[str, str, str]]] = {
        "pyproject.toml": [
            (r"(?im)^\s*(?:django\s*=|['\"]django(?:\[.*?\])?(?:[<>=!~][^'\"]*)?['\"])", "backend-framework", "Django"),
            (r"(?im)^\s*(?:flask\s*=|['\"]flask(?:\[.*?\])?(?:[<>=!~][^'\"]*)?['\"])", "backend-framework", "Flask"),
            (r"(?im)^\s*(?:fastapi\s*=|['\"]fastapi(?:\[.*?\])?(?:[<>=!~][^'\"]*)?['\"])", "backend-framework", "FastAPI"),
            (r"(?im)^\s*(?:pytest\s*=|['\"]pytest(?:\[.*?\])?(?:[<>=!~][^'\"]*)?['\"]|\[tool\.pytest)", "test-tool", "pytest"),
            (r"(?im)^\s*(?:ruff\s*=|['\"]ruff(?:[<>=!~][^'\"]*)?['\"]|\[tool\.ruff)", "quality-tool", "Ruff"),
            (r"(?im)^\s*(?:black\s*=|['\"]black(?:[<>=!~][^'\"]*)?['\"]|\[tool\.black)", "quality-tool", "Black"),
        ],
        "requirements.txt": [
            (r"(?im)^django(?:\[.*?\])?\s*(?:[<>=!~]|$)", "backend-framework", "Django"),
            (r"(?im)^flask(?:\[.*?\])?\s*(?:[<>=!~]|$)", "backend-framework", "Flask"),
            (r"(?im)^fastapi(?:\[.*?\])?\s*(?:[<>=!~]|$)", "backend-framework", "FastAPI"),
            (r"(?im)^pytest(?:\[.*?\])?\s*(?:[<>=!~]|$)", "test-tool", "pytest"),
            (r"(?im)^ruff\s*(?:[<>=!~]|$)", "quality-tool", "Ruff"),
        ],
        "Gemfile": [(r"(?m)^\s*gem\s+['\"]rails['\"]", "backend-framework", "Rails")],
        "pom.xml": [(r"org\.springframework\.boot", "backend-framework", "Spring Boot")],
        "build.gradle": [(r"org\.springframework\.boot", "backend-framework", "Spring Boot")],
        "build.gradle.kts": [(r"org\.springframework\.boot", "backend-framework", "Spring Boot")],
        "go.mod": [
            (r"github\.com/gin-gonic/gin", "backend-framework", "Gin"),
            (r"github\.com/gofiber/fiber", "backend-framework", "Fiber"),
            (r"github\.com/labstack/echo", "backend-framework", "Echo"),
        ],
        "Cargo.toml": [
            (r"(?m)^\s*axum\s*=", "backend-framework", "Axum"),
            (r"(?m)^\s*actix-web\s*=", "backend-framework", "Actix Web"),
            (r"(?m)^\s*rocket\s*=", "backend-framework", "Rocket"),
        ],
        "pubspec.yaml": [(r"(?m)^\s*flutter:\s*$", "app-framework", "Flutter")],
    }

    for relative in manifests:
        path = root / relative
        if path.name == "package.json":
            data = read_json(path, errors)
            if data:
                dependencies = dependency_names(data, ("dependencies", "devDependencies", "peerDependencies"))
                for dependency, (category, name) in js_rules.items():
                    if dependency in dependencies:
                        add_signal(signals, category, name, [relative])
        elif path.name == "composer.json":
            data = read_json(path, errors)
            if data:
                dependencies = dependency_names(data, ("require", "require-dev"))
                for dependency, (category, name) in composer_rules.items():
                    if dependency in dependencies:
                        marker = None
                        if name == "Laravel":
                            candidate = (Path(relative).parent / "artisan").as_posix()
                            marker = candidate if candidate in project_paths else None
                        add_signal(signals, category, name, [relative], marker)
        elif path.name in text_rules:
            content = read_selected_text(path, errors)
            if content is not None:
                for pattern, category, name in text_rules[path.name]:
                    if re.search(pattern, content):
                        marker = None
                        if name == "Flutter":
                            candidate = (Path(relative).parent / "lib/main.dart").as_posix()
                            marker = candidate if candidate in project_paths else None
                        add_signal(signals, category, name, [relative], marker)

    return sorted(signals, key=lambda item: (item["category"], item["name"]))


def extract_commands(
    root: Path,
    manifests: list[str],
    lockfiles: list[dict[str, str]],
    errors: list[str],
    warnings: list[str],
) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []

    for relative in manifests:
        path = root / relative
        if path.name == "package.json":
            data = read_json(path, errors)
            scripts = data.get("scripts") if data else None
            js_manager = (
                select_js_manager(relative, data, lockfiles, warnings)
                if data
                else None
            )
            if isinstance(scripts, dict) and js_manager:
                for name in sorted(scripts):
                    if isinstance(scripts[name], str):
                        commands.append(
                            {
                                "runner": js_manager,
                                "name": name,
                                "command": f"{js_manager} run {name}",
                                "source": relative,
                            }
                        )
        elif path.name == "composer.json":
            data = read_json(path, errors)
            scripts = data.get("scripts") if data else None
            if isinstance(scripts, dict):
                for name in sorted(scripts):
                    commands.append(
                        {
                            "runner": "composer",
                            "name": name,
                            "command": f"composer run-script {name}",
                            "source": relative,
                        }
                    )

    makefile = root / "Makefile"
    if makefile.is_symlink():
        errors.append(f"Skipped symlinked command file: {makefile}")
    elif makefile.is_file():
        try:
            if makefile.stat().st_size > MAX_MANIFEST_BYTES:
                errors.append(f"Skipped oversized command file: {makefile}")
                return sorted(commands, key=lambda item: (item["source"], item["name"]))
            targets = set()
            for line in makefile.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.-]*):(?:\s|$)", line)
                if match and not match.group(1).startswith("."):
                    targets.add(match.group(1))
            for target in sorted(targets):
                commands.append(
                    {
                        "runner": "make",
                        "name": target,
                        "command": f"make {target}",
                        "source": "Makefile",
                    }
                )
        except (OSError, UnicodeError) as exc:
            errors.append(f"Could not parse {makefile}: {exc.__class__.__name__}")

    return sorted(commands, key=lambda item: (item["source"], item["name"]))


def detect_global_sources(
    home: Path, codex_home: Optional[Path] = None
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    instructions: list[dict[str, Any]] = []
    configs: list[dict[str, str]] = []

    codex_root = codex_home or home / ".codex"
    candidates = [
        (codex_root / "AGENTS.override.md", "codex", "override"),
        (codex_root / "AGENTS.md", "codex", "instructions"),
        (home / ".claude/CLAUDE.md", "claude-code", "instructions"),
        (home / ".claude/CLAUDE.local.md", "claude-code", "local-instructions"),
        (home / ".copilot/copilot-instructions.md", "github-copilot", "instructions"),
    ]
    codex_override = is_nonempty_file(codex_root / "AGENTS.override.md")
    for path, tool, kind in candidates:
        if is_nonempty_file(path):
            entry: dict[str, Any] = {
                "scope": "global",
                "tool": tool,
                "kind": kind,
                "path": str(path),
                "deprecated": False,
            }
            if tool == "codex":
                entry["active"] = kind == "override" or not codex_override
                if kind == "instructions" and codex_override:
                    entry["shadowed_by"] = str(codex_root / "AGENTS.override.md")
            instructions.append(entry)

    rule_roots = [
        (home / ".claude/rules", "claude-code"),
        (home / ".copilot/instructions", "github-copilot"),
        (home / ".roo/rules", "roo-code"),
        (home / ".kilocode/rules", "kilo-code"),
    ]
    for rule_root, tool in rule_roots:
        if rule_root.is_dir():
            for path in sorted(rule_root.rglob("*.md")):
                if path.is_file():
                    instructions.append(
                        {
                            "scope": "global",
                            "tool": tool,
                            "kind": "scoped-rule",
                            "path": str(path),
                            "deprecated": False,
                        }
                    )

    config_candidates = [
        (codex_root / "config.toml", "codex", "settings"),
        (home / ".claude/settings.json", "claude-code", "settings"),
        (home / ".roo/mcp_settings.json", "roo-code", "mcp"),
        (home / ".cline/cline_mcp_settings.json", "cline", "mcp"),
        (home / ".config/cline/cline_mcp_settings.json", "cline", "mcp"),
    ]
    for path, tool, kind in config_candidates:
        if path.is_file():
            configs.append(
                {"scope": "global", "tool": tool, "kind": kind, "path": str(path)}
            )

    return instructions, configs


def build_report(
    root: Path,
    max_depth: int,
    include_global: bool,
    config_paths: Optional[list[str]] = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    instructions: list[dict[str, Any]] = []
    configs: list[dict[str, str]] = []
    manifests: list[str] = []
    lockfiles: list[dict[str, str]] = []
    environments: list[str] = []
    ci: list[str] = []
    docs: list[str] = []

    project_files = walk_project(root, max_depth)
    project_paths = {relative_path(path, root) for path in project_files}
    for path in project_files:
        relative = relative_path(path, root)
        parts = Path(relative).parts

        instruction = classify_instruction(relative)
        if instruction:
            add_unique(
                instructions,
                {"scope": "project", "path": relative, **instruction},
            )

        config = classify_config(relative)
        if config:
            configs.append({"scope": "project", "path": relative, **config})

        if path.name in MANIFEST_NAMES:
            manifests.append(relative)
        if path.name in LOCKFILE_MANAGERS:
            lockfiles.append(
                {"path": relative, "manager": LOCKFILE_MANAGERS[path.name]}
            )
        if path.name in ENVIRONMENT_NAMES or relative == ".devcontainer/devcontainer.json":
            environments.append(relative)
        if relative in ROOT_CI_NAMES or (
            relative.startswith(".github/workflows/")
            and path.suffix in {".yaml", ".yml"}
        ):
            ci.append(relative)
        if relative in ROOT_DOC_NAMES or (
            len(parts) <= 3
            and parts[0] in {"deploy", "docs"}
            and path.suffix.lower() == ".md"
        ):
            docs.append(relative)

    instructions.sort(key=lambda item: (item["scope"], item["path"], item["tool"]))
    configs.sort(key=lambda item: (item["scope"], item["path"], item["tool"]))
    manifests = sorted(set(manifests))
    lockfiles = sorted(lockfiles, key=lambda item: item["path"])
    environments = sorted(set(environments))
    ci = sorted(set(ci))
    docs = sorted(set(docs))

    instruction_paths = {entry["path"] for entry in instructions if entry["scope"] == "project"}
    for path in sorted(instruction_paths):
        if path.endswith("AGENTS.override.md") and is_nonempty_file(root / path):
            sibling = str(Path(path).with_name("AGENTS.md")).replace("\\", "/")
            if sibling in instruction_paths:
                warnings.append(
                    f"{path} shadows {sibling} for Codex in the same directory."
                )
    if ".cursorrules" in instruction_paths:
        warnings.append(".cursorrules is legacy; prefer scoped rules under .cursor/rules/.")

    if include_global:
        configured_codex_home = os.environ.get("CODEX_HOME")
        global_instructions, global_configs = detect_global_sources(
            Path.home(),
            Path(configured_codex_home).expanduser().resolve()
            if configured_codex_home
            else None,
        )
        instructions.extend(global_instructions)
        configs.extend(global_configs)
        instructions.sort(key=lambda item: (item["scope"], item["path"], item["tool"]))
        configs.sort(key=lambda item: (item["scope"], item["path"], item["tool"]))

    opencode_config = os.environ.get("OPENCODE_CONFIG")
    external_configs = list(config_paths or [])
    if opencode_config:
        external_configs.append(opencode_config)
    for raw_path in external_configs:
        external = Path(raw_path).expanduser().resolve()
        if external.is_file():
            configs.append(
                {
                    "scope": "external",
                    "tool": "opencode" if raw_path == opencode_config else "custom",
                    "kind": "settings" if raw_path == opencode_config else "agent-config",
                    "path": str(external),
                }
            )
        else:
            warnings.append(f"Configured agent path does not exist: {external}")
    configs.sort(key=lambda item: (item["scope"], item["path"], item["tool"]))

    source_directories = sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and entry.name in SOURCE_DIRECTORY_NAMES
    )
    commands = extract_commands(root, manifests, lockfiles, errors, warnings)
    technology_signals = detect_technology_signals(
        root, manifests, project_paths, errors
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "scan": {
            "max_depth": max_depth,
            "include_global": include_global,
            "ignored_directories": sorted(IGNORED_DIRECTORIES),
        },
        "instruction_sources": instructions,
        "agent_configs": configs,
        "project_evidence": {
            "manifests": manifests,
            "lockfiles": lockfiles,
            "environments": environments,
            "ci": ci,
            "docs": docs,
            "source_directories": source_directories,
        },
        "declared_commands": commands,
        "technology_signals": technology_signals,
        "warnings": sorted(set(warnings)),
        "errors": sorted(set(errors)),
    }


def print_entries(title: str, entries: list[Any]) -> None:
    print(title)
    if not entries:
        print("  - (none)")
        return
    for entry in entries:
        if isinstance(entry, dict):
            if "command" in entry:
                print(
                    f"  - {entry['command']} "
                    f"(source={entry['source']}, name={entry['name']})"
                )
                continue
            if "evidence" in entry:
                print(
                    f"  - {entry['name']} (category={entry['category']}, "
                    f"confidence={entry['confidence']}, "
                    f"evidence={', '.join(entry['evidence'])})"
                )
                continue
            details = ", ".join(
                f"{key}={value}"
                for key, value in entry.items()
                if key not in {"path", "deprecated"}
            )
            legacy = ", legacy" if entry.get("deprecated") else ""
            suffix = f" ({details}{legacy})" if details or legacy else ""
            print(f"  - {entry['path']}{suffix}")
        else:
            print(f"  - {entry}")


def print_text(report: dict[str, Any]) -> None:
    evidence = report["project_evidence"]
    print("Agent context evidence report")
    print(f"Root: {report['root']}")
    print(f"Schema: {report['schema_version']}")
    print()
    print_entries("Instruction sources:", report["instruction_sources"])
    print()
    print_entries("Agent configuration:", report["agent_configs"])
    print()
    print_entries("Manifests:", evidence["manifests"])
    print_entries("Lockfiles:", evidence["lockfiles"])
    print_entries("Environment files:", evidence["environments"])
    print_entries("CI files:", evidence["ci"])
    print_entries("Documentation:", evidence["docs"])
    print_entries("Source directories:", evidence["source_directories"])
    print()
    print_entries("Declared commands:", report["declared_commands"])
    print()
    print_entries("Technology signals:", report["technology_signals"])
    if report["warnings"]:
        print()
        print_entries("Warnings:", report["warnings"])
    if report["errors"]:
        print()
        print_entries("Non-fatal errors:", report["errors"])


def main() -> int:
    args = parse_args()
    if args.max_depth < 0:
        print("error: --max-depth must be zero or greater", file=sys.stderr)
        return 2

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: root directory does not exist: {root}", file=sys.stderr)
        return 2

    report = build_report(root, args.max_depth, args.include_global, args.config_paths)
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
