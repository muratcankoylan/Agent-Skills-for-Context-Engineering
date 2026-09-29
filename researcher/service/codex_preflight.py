"""Credential-free pinned SDK startup and optional native-sandbox diagnostics.

No thread, turn, model listing, provider request or deployment authority is
created. Native checks execute only fixed local fixture commands. Passing is a
prerequisite, not host-file containment or production acceptance. The tool-free
profile deliberately does not claim that message execution was tested.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from researcher.service.codex_config_boundary import (
    ConfigBoundaryError, verify_config_boundary, verify_system_config,
)

VERSION = "0.159.0"
MAX_OUTPUT = 16384
CHECKS = ("dependencies", "runtime_identity", "app_server", "native_noop",
          "read_only_denies_write", "workspace_write_allows_write", "workspace_denies_sibling")
ERRORS = frozenset({"INVALID_INPUT", "UNSUPPORTED_PLATFORM", "SDK_MISSING", "VERSION_MISMATCH",
    "APP_SERVER_FAILED", "NATIVE_SANDBOX_UNAVAILABLE", "NATIVE_NAMESPACE_DENIED",
    "READ_ONLY_WRITE_ALLOWED", "WORKSPACE_WRITE_FAILED", "OUTSIDE_WRITE_ALLOWED",
    "INVALID_COMMAND_RESULT", "TIMEOUT", "OUTPUT_LIMIT", "INVALID_RESULT", "CHILD_FAILED",
    "CONFIG_BOUNDARY_UNVERIFIED"})


class PreflightError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _result(profile):
    return {"schema": "codex-runtime-preflight/v1", "authority": "none", "profile": profile,
            "status": "blocked", "failure_code": None,
            "checks": dict.fromkeys(CHECKS, "not_run"), "sdk_version": None,
            "runtime_version": None,
            "platform": {"linux": "linux", "darwin": "macos"}.get(sys.platform, "unsupported"),
            "fixture": True, "provider_calls": 0, "production_ready": False,
            "tool_free_message_execution_verified": False,
            "native_tool_execution_verified": False, "host_file_containment_verified": False}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def _validate_result(value, profile):
    base = _result(profile)
    if type(value) is not dict or set(value) != set(base):
        raise PreflightError("INVALID_RESULT")
    for key in ("schema", "authority", "profile", "platform", "fixture", "provider_calls",
                "production_ready", "tool_free_message_execution_verified", "host_file_containment_verified"):
        if type(value[key]) is not type(base[key]) or value[key] != base[key]:
            raise PreflightError("INVALID_RESULT")
    if (value["status"] not in ("passed", "blocked", "unknown")
            or value["failure_code"] not in ERRORS | {None}
            or type(value["checks"]) is not dict or set(value["checks"]) != set(CHECKS)
            or any(item not in ("passed", "failed", "not_run") for item in value["checks"].values())
            or value["sdk_version"] not in (None, VERSION) or value["runtime_version"] not in (None, VERSION)
            or type(value["native_tool_execution_verified"]) is not bool):
        raise PreflightError("INVALID_RESULT")
    expected = CHECKS if profile == "native_tools" else CHECKS[:3]
    passed = all(value["checks"][key] == "passed" for key in expected)
    if (value["status"] == "passed") != (passed and value["failure_code"] is None):
        raise PreflightError("INVALID_RESULT")
    if (value["native_tool_execution_verified"] != (profile == "native_tools" and value["status"] == "passed")
            or profile == "tool_free" and any(value["checks"][key] != "not_run" for key in CHECKS[3:])
            or value["status"] == "passed" and (value["sdk_version"] != VERSION or value["runtime_version"] != VERSION)):
        raise PreflightError("INVALID_RESULT")
    return value


def _private_directory(value):
    try:
        path = Path(value)
        info = path.lstat()
        if (not path.is_absolute() or path.resolve(strict=True) != path or not stat.S_ISDIR(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid()):
            raise ValueError()
        return path
    except (OSError, TypeError, ValueError):
        raise PreflightError("INVALID_INPUT") from None


def _namespace_failure(value):
    # Classification only. Never return the potentially sensitive exception text.
    try:
        text = str(value)[:8192].lower()
    except Exception:
        return False
    return "no permissions to create a new namespace" in text or "creating new namespace failed" in text


def _runtime_identity(initialized):
    # Same legacy metadata shape supported by the pinned SDK initialize method.
    # Platform details follow the version token and are never included in output.
    actual = initialized.serverInfo.version if initialized.serverInfo else None
    if not actual:
        agent = getattr(initialized, "userAgent", None)
        if isinstance(agent, str) and len(agent) <= 1024:
            pieces = agent.strip().split("/", 1) if "/" in agent else agent.strip().split(maxsplit=1)
            actual = pieces[1] if len(pieces) == 2 else None
    if not isinstance(actual, str) or len(actual) > 1024 or not actual.split() or actual.split()[0] != VERSION:
        raise PreflightError("VERSION_MISMATCH")


_WRITE = ("import errno,pathlib,sys\n"
          "try:\n pathlib.Path(sys.argv[1]).write_bytes(b'codex-preflight\\n')\n"
          "except OSError as e:\n"
          " if e.errno not in (errno.EACCES,errno.EPERM,errno.EROFS): raise\n"
          " print('WRITE_DENIED')\n"
          "else:\n print('WRITE_OK')\n")


def _native_checks(client, workspace, sibling, response_model, checks):
    read_only = {"type": "readOnly", "networkAccess": False}
    writable = {"type": "workspaceWrite", "networkAccess": False, "writableRoots": [],
                "excludeSlashTmp": True, "excludeTmpdirEnvVar": True}

    def command(policy, code, *args):
        result = client.request("command/exec", {
            "command": [sys.executable, "-I", "-B", "-c", code, *map(str, args)],
            "cwd": str(workspace), "sandboxPolicy": policy, "timeoutMs": 5000,
            "outputBytesCap": 8192, "env": {"PATH": "/usr/bin:/bin", "LANG": "C"}},
            response_model=response_model)
        if (type(result.exit_code) is not int or not isinstance(result.stdout, str)
                or not isinstance(result.stderr, str) or len(result.stdout) > 8192 or len(result.stderr) > 8192):
            raise PreflightError("INVALID_COMMAND_RESULT")
        if _namespace_failure(result.stderr):
            raise PreflightError("NATIVE_NAMESPACE_DENIED")
        return result.exit_code, result.stdout

    stage = "native_noop"
    try:
        if command(read_only, "print('NATIVE_OK')") != (0, "NATIVE_OK\n"):
            raise PreflightError("NATIVE_SANDBOX_UNAVAILABLE")
        checks[stage] = "passed"
        stage = "read_only_denies_write"
        denied = workspace / "readonly-proof.txt"
        if command(read_only, _WRITE, denied) != (0, "WRITE_DENIED\n") or denied.exists():
            raise PreflightError("READ_ONLY_WRITE_ALLOWED")
        checks[stage] = "passed"
        stage = "workspace_write_allows_write"
        allowed = workspace / "write-proof.txt"
        if (command(writable, _WRITE, allowed) != (0, "WRITE_OK\n")
                or not allowed.is_file() or allowed.is_symlink() or allowed.read_bytes() != b"codex-preflight\n"):
            raise PreflightError("WORKSPACE_WRITE_FAILED")
        checks[stage] = "passed"
        stage = "workspace_denies_sibling"
        outside = sibling / "outside-proof.txt"
        if command(writable, _WRITE, outside) != (0, "WRITE_DENIED\n") or outside.exists():
            raise PreflightError("OUTSIDE_WRITE_ALLOWED")
        checks[stage] = "passed"
    except Exception as error:
        checks[stage] = "failed"
        if isinstance(error, PreflightError):
            raise
        code = "NATIVE_NAMESPACE_DENIED" if _namespace_failure(error) else "NATIVE_SANDBOX_UNAVAILABLE"
        raise PreflightError(code) from None


def _child(profile, directory):
    result = _result(profile)
    client = None
    stage = "dependencies"
    try:
        verify_config_boundary()
        for package in ("openai-codex", "openai-codex-cli-bin"):
            if importlib.metadata.version(package) != VERSION:
                raise PreflightError("VERSION_MISMATCH")
        result["sdk_version"] = VERSION
        result["checks"][stage] = "passed"
        from openai_codex.client import CodexClient, CodexConfig
        from openai_codex.generated.v2_all import CommandExecResponse
        # Trusted repository configuration, never project/user settings or a caller command.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from researcher.service.codex_worker import _config, _deny
        root = Path(directory)
        stage = "app_server"
        overrides = _config({"model": "preflight-no-model", "sandbox": "read_only", "reasoning_effort": "low"},
                            "http://127.0.0.1:9/v1", str(root / "codex"))
        client = CodexClient(CodexConfig(cwd=str(root / "workspace"), config_overrides=overrides,
                                       experimental_api=False), approval_handler=_deny)
        client.start()
        initialized = client.initialize()
        result["checks"][stage] = "passed"
        stage = "runtime_identity"
        # Do not mistake installed wheel metadata for observed running runtime identity.
        _runtime_identity(initialized)
        result["runtime_version"] = VERSION
        result["checks"][stage] = "passed"
        if profile == "native_tools":
            _native_checks(client, root / "workspace", root / "sibling", CommandExecResponse, result["checks"])
        result["status"] = "passed"
        result["native_tool_execution_verified"] = profile == "native_tools"
    except ConfigBoundaryError:
        result["checks"][stage] = "failed"
        result["failure_code"] = "CONFIG_BOUNDARY_UNVERIFIED"
    except (ImportError, importlib.metadata.PackageNotFoundError):
        result["checks"][stage] = "failed"
        result["failure_code"] = "SDK_MISSING"
    except Exception as error:
        if not any(value == "failed" for value in result["checks"].values()):
            result["checks"][stage] = "failed"
        result["failure_code"] = error.code if isinstance(error, PreflightError) else "APP_SERVER_FAILED"
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                result["status"] = "blocked"
                result["native_tool_execution_verified"] = False
                result["failure_code"] = "APP_SERVER_FAILED"
    return result


def _stop(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def _execute(command, env, cwd, timeout):
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
    output = bytearray()
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise PreflightError("TIMEOUT")
                for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                    data = os.read(key.fileobj.fileno(), 4096)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    output.extend(data)
                    if len(output) > MAX_OUTPUT:
                        raise PreflightError("OUTPUT_LIMIT")
        process.wait(timeout=max(0.001, deadline - time.monotonic()))
        if process.returncode != 0:
            raise PreflightError("CHILD_FAILED")
        return bytes(output)
    except subprocess.TimeoutExpired:
        raise PreflightError("TIMEOUT") from None
    finally:
        _stop(process)
        process.stdout.close()


def run_preflight(*, sdk_python, workspace_parent, timeout_seconds=30, profile="native_tools"):
    """Return sanitized evidence; invalid inputs raise only a safe PreflightError.

    sdk_python is an explicit trusted executable; its venv symlink is retained so
    dependency discovery stays in that venv. The parent must already be private.
    No credential or caller-selected command is accepted. Same-UID filesystem
    mutation/host-file read isolation is outside this diagnostic's threat model.
    """
    if type(profile) is not str or profile not in ("tool_free", "native_tools") or (
            type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 120):
        raise PreflightError("INVALID_INPUT")
    parent = _private_directory(workspace_parent)
    try:
        python = Path(sdk_python)
        if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
            raise ValueError()
    except (OSError, TypeError, ValueError):
        raise PreflightError("INVALID_INPUT") from None
    result = _result(profile)
    if result["platform"] == "unsupported":
        result["failure_code"] = "UNSUPPORTED_PLATFORM"
        return result
    try:
        verify_system_config()
        with tempfile.TemporaryDirectory(prefix="codex-preflight-", dir=parent) as fixture:
            root = Path(fixture)
            for name in ("home", "codex", "tmp", "workspace", "sibling"):
                (root / name).mkdir(mode=0o700)
            env = {"PATH": str(python.parent) + ":/usr/bin:/bin", "HOME": str(root / "home"),
                   "CODEX_HOME": str(root / "codex"), "TMPDIR": str(root / "tmp"), "LANG": "C", "TZ": "UTC"}
            raw = _execute([str(python), "-I", "-B", str(Path(__file__).resolve()),
                            "--child", profile, str(root)], env, root / "workspace", timeout_seconds)
            def pairs(items):
                value = {}
                for key, item in items:
                    if key in value:
                        raise ValueError()
                    value[key] = item
                return value
            try:
                parsed = json.loads(raw, object_pairs_hook=pairs,
                                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                return _validate_result(parsed, profile)
            except (ValueError, TypeError, RecursionError):
                raise PreflightError("INVALID_RESULT") from None
    except ConfigBoundaryError:
        result["failure_code"] = "CONFIG_BOUNDARY_UNVERIFIED"
        return result
    except (PreflightError, OSError) as error:
        result["failure_code"] = error.code if isinstance(error, PreflightError) else "CHILD_FAILED"
        result["status"] = "unknown" if result["failure_code"] == "TIMEOUT" else "blocked"
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-python", required=True)
    parser.add_argument("--workspace-parent", required=True)
    parser.add_argument("--profile", choices=("tool_free", "native_tools"), required=True)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        result = run_preflight(**vars(args))
    except PreflightError as error:
        result = _result(args.profile)
        result["failure_code"] = error.code
    print(_json(result).decode("ascii"))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child" and sys.argv[2] in ("tool_free", "native_tools"):
        print(_json(_child(sys.argv[2], sys.argv[3])).decode("ascii"))
    else:
        raise SystemExit(main())
