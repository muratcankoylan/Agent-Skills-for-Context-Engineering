"""Pre-start admission for the pinned SDK's otherwise ambient host layers.

The first supported policy is an unconfigured host, not an interpretation of
administrator TOML. Refuse policy we cannot honor; never hide or override it.
Private HOME/CODEX_HOME and a clean environment close user/cloud-auth layers in
the caller. This module closes the system directory and macOS preferences.

This is a read-only check, not an OS sandbox or a defense against an administrator
changing policy between inspection and startup. Production uses an immutable,
reviewed filesystem image. There is deliberately no environment-variable bypass.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import stat
import sys

POLICY = "empty-host-config-v1"


class ConfigBoundaryError(ValueError):
    def __init__(self):
        super().__init__("CODEX_CONFIG_BOUNDARY_UNVERIFIED")


def _trusted_directory(path):
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) & 0o022):
        raise ConfigBoundaryError()


def _system_layer(etc):
    # macOS /etc -> private/etc is expected. Its link and the entire resolved
    # ancestor chain must remain administrator-owned, never caller-writable.
    info = etc.lstat()
    if info.st_uid != 0:
        raise ConfigBoundaryError()
    real = etc.resolve(strict=True)
    for directory in (real, *real.parents):
        _trusted_directory(directory)
    target = real / "codex"
    try:
        target.lstat()
    except FileNotFoundError:
        return
    _trusted_directory(target)
    # A conservative namespace closure also covers managed hooks, skills and
    # future files, rather than silently accepting unknown configuration keys.
    with os.scandir(target) as entries:
        if next(entries, None) is not None:
            raise ConfigBoundaryError()


def _macos_preferences_present():
    """Read presence only, using the OS API rather than guessed plist paths.

    CopyAppValue includes forced/managed application preferences. Explicit
    current/any user and host scopes conservatively reject stored domain values
    too. Nothing is decoded, logged, synchronized or written back to MDM.
    """
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    pointer = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [pointer, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFStringCreateWithCString.restype = pointer
    cf.CFRelease.argtypes = [pointer]
    cf.CFRelease.restype = None
    cf.CFPreferencesCopyAppValue.argtypes = [pointer, pointer]
    cf.CFPreferencesCopyAppValue.restype = pointer
    cf.CFPreferencesCopyValue.argtypes = [pointer, pointer, pointer, pointer]
    cf.CFPreferencesCopyValue.restype = pointer
    allocated = []

    def string(value):
        result = cf.CFStringCreateWithCString(None, value, 0x08000100)  # UTF-8
        if not result:
            raise ConfigBoundaryError()
        allocated.append(result)
        return result

    def found(value):
        if value:
            cf.CFRelease(value)
            return True
        return False

    try:
        domain = string(b"com.openai.codex")
        users = [pointer.in_dll(cf, name).value for name in
                 ("kCFPreferencesCurrentUser", "kCFPreferencesAnyUser")]
        hosts = [pointer.in_dll(cf, name).value for name in
                 ("kCFPreferencesCurrentHost", "kCFPreferencesAnyHost")]
        if not all(users + hosts):
            raise ConfigBoundaryError()
        for name in (b"config_toml_base64", b"requirements_toml_base64"):
            key = string(name)
            if found(cf.CFPreferencesCopyAppValue(key, domain)):
                return True
            for user in users:
                for host in hosts:
                    if found(cf.CFPreferencesCopyValue(key, domain, user, host)):
                        return True
        return False
    finally:
        for value in reversed(allocated):
            cf.CFRelease(value)


def verify_system_config():
    """Cheap parent-process refusal; this is not the complete startup gate."""
    try:
        if sys.platform not in ("linux", "darwin"):
            raise ConfigBoundaryError()
        _system_layer(Path("/etc"))
    except Exception:
        raise ConfigBoundaryError() from None


def verify_config_boundary():
    """Complete pre-SDK gate, inside the supervisor's deadline-bounded child.

    CoreFoundation may use IPC to the preferences service. Keeping it in the
    child means a stalled OS service cannot hang the caller outside its deadline.
    """
    try:
        verify_system_config()
        if sys.platform == "darwin" and _macos_preferences_present():
            raise ConfigBoundaryError()
    except Exception:
        # Never include system paths, configuration values or native errors.
        raise ConfigBoundaryError() from None
