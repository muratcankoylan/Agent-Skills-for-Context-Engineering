#!/bin/bash
# Digital Brain installer, macOS/Linux with Python 3. No GNU realpath dependency.
# Policy: new destinations only; never overwrite or remove an existing entry.
# Custom parents must exist. User/project modes may create .claude/skills only.
# Symlinks, source overlap, traversal and broad targets fail before copying.
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Python 3 is required for safe, portable installation.' >&2
    exit 1
fi
BRAIN_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

printf '%s\n' 'Digital Brain Installer' 'New destinations only. Existing installations are never overwritten.' '' \
    '1) User-wide      - ~/.claude/skills/' \
    '2) Current project - ./.claude/skills/' \
    '3) Custom existing parent directory'
IFS= read -r -p 'Enter choice [1-3]: ' choice
custom_path=''
case "$choice" in
    1|2) ;;
    3) IFS= read -r -p 'Enter custom parent path (literal, no ~ expansion): ' custom_path ;;
    *) printf '%s\n' 'Invalid choice.' >&2; exit 1 ;;
esac

# Directory-fd operations avoid following destination aliases between checks and
# writes. This protects ordinary local use, not hostile same-UID source mutation.
python3 - "$choice" "$custom_path" "$BRAIN_DIR" "$(pwd -P)" "${HOME:-}" <<'PY'
import os
import stat
import sys

NAME = "digital-brain"
DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
MAX_ENTRIES = 2048
MAX_BYTES = 16 * 1024 * 1024


class UnsafeInstall(Exception):
    pass


def absolute(value, base=None):
    if not value or len(value) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise UnsafeInstall("INVALID_PATH")
    if ".." in value.split("/"):
        raise UnsafeInstall("PATH_TRAVERSAL")
    if not os.path.isabs(value):
        if base is None:
            raise UnsafeInstall("ABSOLUTE_ANCHOR_REQUIRED")
        value = os.path.join(base, value)
    # POSIX permits special treatment of exactly two leading slashes. This
    # local-only installer treats all leading slash spellings as one root.
    return "/" + os.path.normpath(value).lstrip("/")


def descend(start, components):
    current = os.dup(start)
    try:
        for component in components:
            child = os.open(component, DIRECTORY, dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def open_directory(path):
    anchor = os.open("/", DIRECTORY)
    try:
        return descend(anchor, [part for part in path.split("/") if part])
    finally:
        os.close(anchor)


def snapshot(source):
    entries = []
    total = 0

    def visit(directory, prefix):
        nonlocal total
        if len(prefix) > 32:
            raise UnsafeInstall("SOURCE_TOO_LARGE")
        for name in sorted(os.listdir(directory)):
            relative = prefix + (name,)
            if relative == ("scripts", "install.sh"):
                continue
            if any(ord(c) < 32 or ord(c) == 127 for c in name):
                raise UnsafeInstall("UNSAFE_SOURCE_ENTRY")
            info = os.stat(name, dir_fd=directory, follow_symlinks=False)
            is_directory = stat.S_ISDIR(info.st_mode)
            if not is_directory and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
                raise UnsafeInstall("UNSAFE_SOURCE_ENTRY")
            total += 0 if is_directory else info.st_size
            if len(entries) >= MAX_ENTRIES or total > MAX_BYTES:
                raise UnsafeInstall("SOURCE_TOO_LARGE")
            identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode)
            entries.append((relative, is_directory, identity))
            if is_directory:
                child = os.open(name, DIRECTORY, dir_fd=directory)
                try:
                    visit(child, relative)
                finally:
                    os.close(child)

    visit(source, ())
    if not any(parts == ("SKILL.md",) and not directory for parts, directory, _ in entries):
        raise UnsafeInstall("SOURCE_SKILL_MISSING")
    return entries


def install():
    mode, custom, source_path, project, home = sys.argv[1:]
    source_path, project = absolute(source_path), absolute(project)
    home = absolute(home) if home else None
    anchor = home if mode == "1" else project
    if mode == "1" and home is None:
        raise UnsafeInstall("HOME_REQUIRED")
    if mode != "3" and anchor == "/":
        raise UnsafeInstall("BROAD_TARGET")
    parent = absolute(custom, project) if mode == "3" else os.path.join(anchor, ".claude", "skills")
    target = os.path.join(parent, NAME)
    if parent == "/" or target in (home, project):
        raise UnsafeInstall("BROAD_TARGET")
    if os.path.commonpath((target, source_path)) in (target, source_path):
        raise UnsafeInstall("SOURCE_TARGET_OVERLAP")

    source = open_directory(source_path)
    parent_fd = None
    created = False
    try:
        entries = snapshot(source)  # Reject unsafe source entries before any writes.
        if mode == "3":
            parent_fd = open_directory(parent)
        else:
            parent_fd = open_directory(anchor)
            for component in (".claude", "skills"):
                try:
                    os.mkdir(component, mode=0o700, dir_fd=parent_fd)
                except FileExistsError:
                    pass
                child = os.open(component, DIRECTORY, dir_fd=parent_fd)
                os.close(parent_fd)
                parent_fd = child
        # Exclusive mkdir refuses directories, files and dangling symlinks alike.
        try:
            os.mkdir(NAME, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            raise UnsafeInstall("DESTINATION_EXISTS_NO_OVERWRITE") from None
        created = True
        destination = os.open(NAME, DIRECTORY, dir_fd=parent_fd)
        try:
            for parts, is_directory, identity in entries:
                target_parent = descend(destination, parts[:-1])
                try:
                    if is_directory:
                        os.mkdir(parts[-1], mode=0o700, dir_fd=target_parent)
                        continue
                    source_parent = descend(source, parts[:-1])
                    try:
                        reader = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=source_parent)
                    finally:
                        os.close(source_parent)
                    with os.fdopen(reader, "rb") as incoming:
                        info = os.fstat(incoming.fileno())
                        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode) != identity:
                            raise UnsafeInstall("SOURCE_CHANGED")
                        writer = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                         0o700 if info.st_mode & 0o100 else 0o600, dir_fd=target_parent)
                        with os.fdopen(writer, "wb") as outgoing:
                            remaining = info.st_size
                            while remaining:
                                chunk = incoming.read(min(65536, remaining))
                                if not chunk:
                                    raise UnsafeInstall("SOURCE_CHANGED")
                                outgoing.write(chunk)
                                remaining -= len(chunk)
                            if incoming.read(1):
                                raise UnsafeInstall("SOURCE_CHANGED")
                finally:
                    os.close(target_parent)
            if snapshot(source) != entries:
                raise UnsafeInstall("SOURCE_CHANGED")
        finally:
            os.close(destination)
    except BaseException:
        if created:
            print("Installation failed; the new partial destination was retained. No existing entry was removed.", file=sys.stderr)
        raise
    finally:
        os.close(source)
        if parent_fd is not None:
            os.close(parent_fd)
    print("Installation complete: " + target)
    print("Start with identity/voice.md and identity/brand.md in the installed copy.")


try:
    install()
except UnsafeInstall as error:
    print("Installation refused: " + str(error), file=sys.stderr)
    sys.exit(1)
except OSError:
    print("Installation refused: path missing, unsafe, inaccessible, or an I/O operation failed.", file=sys.stderr)
    sys.exit(1)
PY
