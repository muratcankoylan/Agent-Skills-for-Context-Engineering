"""Explicit, private credential files without shell or ambient-environment semantics.

Supported syntax is blank lines, whole-line comments, and KEY=literal assignments.
Keys are uppercase service identifiers. Values are empty, unquoted tokens, or
single/double-quoted literals. Quoted spaces are literal. Export prefixes, inline
comments, multiline values, backslash escapes, dollar expansion, backticks and
process substitutions are rejected. Nothing is evaluated or put in os.environ.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
import os
from pathlib import Path
import re
import stat
import unicodedata

from .contracts import ENV, ServiceError

MAX_FILE_BYTES = 65536
MAX_CONFIG_BYTES = 262144
MAX_VALUE_BYTES = 4096
MAX_KEYS = 1024
_KEY = re.compile(ENV)


def _file_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _file_policy(info, maximum, private, prefix):
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or (private and (stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid()))):
        raise ServiceError(prefix + "_FILE_UNSAFE")
    if info.st_size > maximum:
        raise ServiceError(prefix + "_FILE_TOO_LARGE")


def _literal(raw):
    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for char in raw):
        raise ServiceError("ENV_VALUE_INVALID")
    if any(char in raw for char in ("$", "`", "\\")) or "<(" in raw or ">(" in raw:
        raise ServiceError("ENV_VALUE_INVALID")
    if raw.startswith(("'", '"')):
        if len(raw) < 2 or raw[-1] != raw[0] or raw[0] in raw[1:-1]:
            raise ServiceError("ENV_FILE_SYNTAX")
        value = raw[1:-1]
    else:
        if any(char.isspace() or char in "#'\"" for char in raw):
            raise ServiceError("ENV_FILE_SYNTAX")
        value = raw
    if len(value.encode("utf-8")) > MAX_VALUE_BYTES:
        raise ServiceError("ENV_VALUE_TOO_LARGE")
    return value


def _parse(body):
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeError:
        raise ServiceError("ENV_FILE_ENCODING") from None
    values = {}
    # CRLF is a line ending, not a value escape. Bare CR remains invalid.
    for line in text.replace("\r\n", "\n").split("\n"):
        if any(unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for char in line):
            raise ServiceError("ENV_FILE_SYNTAX")
        line = line.strip(" ")
        if not line or line.startswith("#"):
            continue
        key, separator, raw = line.partition("=")
        if not separator or not _KEY.fullmatch(key):
            raise ServiceError("ENV_FILE_SYNTAX")
        if key in values:
            raise ServiceError("ENV_FILE_DUPLICATE_KEY")
        if len(values) >= MAX_KEYS:
            raise ServiceError("ENV_FILE_TOO_MANY_KEYS")
        values[key] = _literal(raw)
    return values


def _stable_bytes(path: Path, *, maximum: int, private: bool, prefix: str) -> bytes:
    """One non-following, single-link, stable read for both configuration surfaces."""
    descriptors = []
    try:
        if not isinstance(path, Path):
            raise ServiceError(prefix + "_FILE_INVALID")
        path = path.absolute()
        if ".." in path.parts or len(path.parts) < 2:
            raise ServiceError(prefix + "_FILE_UNSAFE")
        if not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")):
            raise ServiceError(prefix + "_FILE_UNSUPPORTED")
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        close_exec = getattr(os, "O_CLOEXEC", 0)
        parent = os.open(path.anchor, directory_flags | close_exec)
        descriptors.append(parent)
        directories = []
        for name in path.parts[1:-1]:
            child = os.open(name, directory_flags | close_exec, dir_fd=parent)
            descriptors.append(child)
            info = os.fstat(child)
            directories.append((parent, name, child, info.st_dev, info.st_ino, info.st_mode))
            parent = child
        name = path.name
        named_before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _file_policy(named_before, maximum, private, prefix)
        file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | close_exec,
                          dir_fd=parent)
        descriptors.append(file_fd)
        before = os.fstat(file_fd)
        _file_policy(before, maximum, private, prefix)
        if _file_identity(before) != _file_identity(named_before):
            raise ServiceError(prefix + "_FILE_CHANGED")
        pieces, count = [], 0
        while True:
            piece = os.read(file_fd, min(8192, maximum + 1 - count))
            if not piece:
                break
            pieces.append(piece)
            count += len(piece)
            if count > maximum:
                raise ServiceError(prefix + "_FILE_TOO_LARGE")
        after = os.fstat(file_fd)
        named_after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if (count != before.st_size or _file_identity(before) != _file_identity(after)
                or _file_identity(before) != _file_identity(named_after)):
            raise ServiceError(prefix + "_FILE_CHANGED")
        for base, directory_name, child, device, inode, mode in directories:
            opened = os.fstat(child)
            named = os.stat(directory_name, dir_fd=base, follow_symlinks=False)
            if any((value.st_dev, value.st_ino, value.st_mode) != (device, inode, mode)
                   for value in (opened, named)):
                raise ServiceError(prefix + "_FILE_CHANGED")
        return b"".join(pieces)
    except ServiceError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError):
        raise ServiceError(prefix + "_FILE_UNSAFE") from None
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass  # Closing owned descriptors cannot replace a sanitized error.


def read_env_file(path: Path) -> dict[str, str]:
    """Read a stable owned0600 file; absolute traversal never follows symlinks.

    Relative paths are anchored to the caller's current directory without
    resolving symlinks. The file and every traversed directory binding are
    rechecked after reading. Failures contain only fixed codes, never file data.
    """
    return _parse(_stable_bytes(path, maximum=MAX_FILE_BYTES, private=True, prefix="ENV"))


def read_config_file(path: Path) -> str:
    """Bounded stable UTF-8 text, not config acceptance or authority validation.

    Packaged read-only files may have a different owner and public read bits.
    Regular-file, single-link and non-symlink requirements remain unchanged.
    """
    body = _stable_bytes(path, maximum=MAX_CONFIG_BYTES, private=False, prefix="CONFIG")
    try:
        return body.decode("utf-8", errors="strict")
    except UnicodeError:
        raise ServiceError("CONFIG_FILE_ENCODING") from None


def credential_reader(values: dict[str, str], allowed_names: Collection[str]) -> Callable[[str], str]:
    """Capture only explicit allowed names; blanks never fall back to the process."""
    if (not isinstance(values, dict) or not isinstance(allowed_names, Collection)
            or isinstance(allowed_names, (str, bytes)) or len(allowed_names) > MAX_KEYS):
        raise ServiceError("ENV_CREDENTIAL_POLICY_INVALID")
    if any(not isinstance(name, str) or not _KEY.fullmatch(name) for name in allowed_names):
        raise ServiceError("ENV_CREDENTIAL_POLICY_INVALID")
    allowed = frozenset(allowed_names)
    selected = {name: values.get(name) for name in allowed}

    def read(name: str) -> str:
        if not isinstance(name, str) or name not in allowed:
            raise ServiceError("ENV_CREDENTIAL_NOT_ALLOWED")
        value = selected[name]
        if not isinstance(value, str) or not value.strip():
            raise ServiceError("CREDENTIAL_UNAVAILABLE")
        return value

    return read
