"""Fail-closed release preflight shared by the container and native unit templates.

The host must still enforce a read-only source mount. These checks do not attest
mount isolation, dependency provenance, GitHub permissions or scientific quality.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def verify_release(environment: dict[str, str]) -> Path:
    expected = environment.get("RESEARCH_RELEASE_COMMIT", "")
    if not re.fullmatch(r"[a-f0-9]{40}", expected):
        raise ValueError("PINNED_RELEASE_COMMIT_REQUIRED")
    mcp_profile = environment.get("RESEARCH_INSTALL_MCP", "0")
    if mcp_profile not in ("0", "1"):
        raise ValueError("INVALID_MCP_DEPENDENCY_PROFILE")
    configured = environment.get("RESEARCH_RELEASE_DIR", "")
    root = Path(configured)
    if (not root.is_absolute() or root.resolve() != root or not root.is_dir()
            or not (root / ".git").is_dir() or (root / ".git").is_symlink()):
        raise ValueError("STANDALONE_RELEASE_CLONE_REQUIRED")
    if os.access(root, os.W_OK) or os.access(root / ".git", os.W_OK):
        raise ValueError("READ_ONLY_RELEASE_REQUIRED")
    git_environment = {"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1",
                       "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0"}

    def git(*args: str) -> str:
        result = subprocess.run(["git", "-c", f"safe.directory={root}", "-c", "core.fsmonitor=false",
                                 "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
                                env=git_environment, capture_output=True, text=True, timeout=15, check=False)
        if result.returncode:
            raise ValueError("RELEASE_GIT_CHECK_FAILED")
        return result.stdout.strip()

    if git("rev-parse", "HEAD") != expected or git("rev-parse", "--show-toplevel") != str(root):
        raise ValueError("RELEASE_COMMIT_MISMATCH")
    if git("status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"):
        raise ValueError("RELEASE_CLONE_NOT_CLEAN")

    def verify_lock(variable: str, source_relative: str, code: str) -> None:
        lock = Path(environment.get(variable, ""))
        source_lock = root / source_relative
        if (not lock.is_absolute() or lock.is_symlink() or not lock.is_file()
                or source_lock.is_symlink() or not source_lock.is_file()
                or lock.stat().st_size > 262144 or source_lock.stat().st_size > 262144
                or hashlib.sha256(lock.read_bytes()).digest() != hashlib.sha256(source_lock.read_bytes()).digest()):
            raise ValueError(code)

    verify_lock("RESEARCH_DEPENDENCY_LOCK", "requirements-dev.txt", "RUNTIME_DEPENDENCY_LOCK_MISMATCH")
    verify_lock("RESEARCH_CODEX_DEPENDENCY_LOCK", "researcher/service/deploy/requirements-codex-linux.txt",
                "CODEX_RUNTIME_DEPENDENCY_LOCK_MISMATCH")
    # Binding a lock is not permission to activate any MCP tool or endpoint.
    if mcp_profile == "1" or environment.get("RESEARCH_MCP_DEPENDENCY_LOCK"):
        verify_lock("RESEARCH_MCP_DEPENDENCY_LOCK", "researcher/service/requirements-mcp.txt",
                    "MCP_RUNTIME_DEPENDENCY_LOCK_MISMATCH")
    return root


def verify_sdk_startup(root: Path, sdk_python: str) -> None:
    """Run a clean, bounded startup probe only after the release has been verified.

    Native-tool sandbox compatibility is a separate gate. No credential or app
    state reaches this fixture; no source/model request is made by preflight.
    """
    spec = importlib.util.spec_from_file_location("release_codex_preflight", root / "researcher/service/codex_preflight.py")
    if spec is None or spec.loader is None:
        raise ValueError("CODEX_RUNTIME_PREFLIGHT_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="research-sdk-start-", dir="/tmp") as parent:
        try:
            result = module.run_preflight(sdk_python=sdk_python, workspace_parent=Path(parent).resolve(),
                                          timeout_seconds=30, profile="tool_free")
        except module.PreflightError:
            raise ValueError("CODEX_RUNTIME_STARTUP_FAILED") from None
    if result["status"] != "passed":
        raise ValueError("CODEX_RUNTIME_STARTUP_FAILED")


def main() -> int:
    try:
        if os.geteuid() == 0:
            raise ValueError("NONROOT_RUNTIME_REQUIRED")
        root = verify_release(dict(os.environ))
        arguments = sys.argv[1:]
        module = "researcher.service"
        if arguments[:1] == ["organization"]:
            module = "researcher.service.organization"
            arguments = arguments[1:]
        if (arguments.count("--repo") != 1 or any(arg.startswith("--repo=") for arg in arguments)
                or arguments[arguments.index("--repo") + 1] != str(root)):
            raise ValueError("RELEASE_ARGUMENT_MISMATCH")
        sdk_python = os.environ.get("RESEARCH_CODEX_PYTHON", sys.executable)
        if arguments.count("--sdk-python") > 1 or any(arg.startswith("--sdk-python=") for arg in arguments):
            raise ValueError("CODEX_RUNTIME_ARGUMENT_MISMATCH")
        if "--sdk-python" in arguments and arguments[arguments.index("--sdk-python") + 1] != sdk_python:
            raise ValueError("CODEX_RUNTIME_ARGUMENT_MISMATCH")
        # Keep read-only inspection/API available when the agent runtime is
        # unhealthy. Only this entrypoint admits model work; retrieval workers
        # and deterministic commands are not agents.
        if module == "researcher.service.organization" and arguments[:1] in (["cycle"], ["serve"]):
            verify_sdk_startup(root, sdk_python)
        if module == "researcher.service.organization" and "--sdk-python" not in arguments:
            arguments = [*arguments, "--sdk-python", sdk_python]
        os.umask(0o077)
        os.environ["PYTHONPATH"] = str(root)
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        # Git needs only this reviewed root, never a wildcard safe.directory.
        os.environ["GIT_CONFIG_COUNT"] = "1"
        os.environ["GIT_CONFIG_KEY_0"] = "safe.directory"
        os.environ["GIT_CONFIG_VALUE_0"] = str(root)
        os.chdir(root)
        os.execv(sys.executable, [sys.executable, "-B", "-m", module, *arguments])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, ValueError) and re.fullmatch(r"[A-Z_]+", str(error)) else "RELEASE_PREFLIGHT_FAILED"
        print(json.dumps({"error": code}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
