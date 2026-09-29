from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.service.contracts import ServiceError
from researcher.service.environment import credential_reader, read_config_file, read_env_file


class EnvironmentFileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.path = self.root / "synthetic.env"

    def write(self, text=b"KEY=synthetic-value\n", mode=0o600):
        if self.path.exists():
            self.path.chmod(0o600)
        self.path.write_bytes(text.encode() if isinstance(text, str) else text)
        self.path.chmod(mode)
        return self.path

    def failure(self, text, code=None):
        self.write(text)
        with self.assertRaises(ServiceError) as caught:
            read_env_file(self.path)
        if code:
            self.assertEqual(caught.exception.code, code)
        self.assertRegex(str(caught.exception), r"^ENV_[A-Z_]+$")
        self.assertNotIn(str(self.path), str(caught.exception))

    def test_literals_empty_comments_urls_and_unicode(self):
        self.write("""# Synthetic only; ignored comment $text

EMPTY=
SINGLE='space preserved '
DOUBLE=" literal spaces "
URL=https://example.org/api?a=one&b=two
EMAIL=example@example.org
UNICODE=café
UNSELECTED=optional-value
""")
        self.assertEqual(read_env_file(self.path), {
            "EMPTY": "", "SINGLE": "space preserved ", "DOUBLE": " literal spaces ",
            "URL": "https://example.org/api?a=one&b=two", "EMAIL": "example@example.org",
            "UNICODE": "café", "UNSELECTED": "optional-value"})

    def test_crlf_and_no_final_newline(self):
        self.write(b"A=one\r\nB='two'")
        self.assertEqual(read_env_file(self.path), {"A": "one", "B": "two"})

    def test_empty_file_and_comment_only_are_valid(self):
        for text in (b"", b"\n# No selected credentials\n"):
            self.write(text)
            self.assertEqual(read_env_file(self.path), {})

    def test_duplicate_even_empty_is_rejected(self):
        for text in ("KEY=\nKEY=value", "KEY=value\nKEY=value"):
            self.failure(text, "ENV_FILE_DUPLICATE_KEY")

    def test_invalid_identifiers_and_export(self):
        for key in ("lower", "_KEY", "1KEY", "A-B", "A" * 97, "export KEY", "KEY "):
            with self.subTest(key=key):
                self.failure(key + "=synthetic", "ENV_FILE_SYNTAX")

    def test_shell_substitutions_escapes_and_backticks_rejected(self):
        for value in ("$TOKEN", "${TOKEN}", "$(echo synthetic)", "`echo synthetic`",
                      "<(echo)", ">(echo)", r"literal\n", '"$TOKEN"', "'$TOKEN'"):
            with self.subTest(value=value):
                self.failure("KEY=" + value)

    def test_inline_comments_malformed_quotes_and_multiline_rejected(self):
        for value in ("value # comment", "value#comment", "'value' # comment",
                      "'unterminated", '"unterminated', "'a'b'", 'unquoted"quote',
                      "'two\nlines'", '"two\nlines"', "two words"):
            with self.subTest(value=value):
                self.failure("KEY=" + value)

    def test_controls_unicode_format_and_non_utf8_rejected(self):
        for value in ("\x00", "\t", "\r", "\x7f", "\x85", "\u200b", "\u2028", "\u2029"):
            with self.subTest(value=value):
                self.failure("KEY='before" + value + "after'")
        self.failure(b"KEY=\xff", "ENV_FILE_ENCODING")

    def test_utf8_value_budget_and_file_budget(self):
        self.write("KEY=" + "a" * 4096)
        self.assertEqual(len(read_env_file(self.path)["KEY"]), 4096)
        self.failure("KEY=" + "a" * 4097, "ENV_VALUE_TOO_LARGE")
        self.failure("KEY=" + "é" * 2049, "ENV_VALUE_TOO_LARGE")
        self.failure(b"#" + b"a" * 65536, "ENV_FILE_TOO_LARGE")

    def test_permissions_must_be_exactly_owner_read_write(self):
        for mode in (0o644, 0o640, 0o400, 0o700, 0o660, 0o1600):
            with self.subTest(mode=oct(mode)):
                self.write(mode=mode)
                with self.assertRaisesRegex(ServiceError, "ENV_FILE_UNSAFE"):
                    read_env_file(self.path)

    def test_foreign_owner_is_rejected(self):
        self.write()
        with patch("researcher.service.environment.os.getuid", return_value=os.getuid() + 1):
            with self.assertRaisesRegex(ServiceError, "ENV_FILE_UNSAFE"):
                read_env_file(self.path)

    def test_leaf_symlink_and_ancestor_symlink_rejected(self):
        self.write()
        alias = self.root / "alias.env"
        alias.symlink_to(self.path)
        parent_alias = self.root / "directory-alias"
        actual = self.root / "actual"
        actual.mkdir()
        nested = actual / "synthetic.env"
        nested.write_text("KEY=synthetic")
        nested.chmod(0o600)
        parent_alias.symlink_to(actual, target_is_directory=True)
        for candidate in (alias, parent_alias / "synthetic.env"):
            with self.assertRaisesRegex(ServiceError, "ENV_FILE_UNSAFE"):
                read_env_file(candidate)

    def test_hardlink_directory_and_fifo_are_rejected_without_read(self):
        self.write()
        hard = self.root / "hard.env"
        os.link(self.path, hard)
        fifo = self.root / "pipe.env"
        os.mkfifo(fifo, 0o600)
        with patch("researcher.service.environment.os.read", side_effect=AssertionError("must not read")):
            for candidate in (self.path, hard, fifo, self.root):
                with self.assertRaisesRegex(ServiceError, "ENV_FILE_UNSAFE"):
                    read_env_file(candidate)

    def test_missing_file_and_parent_traversal_errors_do_not_echo_path(self):
        for candidate in (self.path, self.root / ".." / self.root.name / "synthetic.env"):
            with self.assertRaises(ServiceError) as caught:
                read_env_file(candidate)
            self.assertEqual(str(caught.exception), "ENV_FILE_UNSAFE")

    def test_relative_path_anchors_without_symlink_resolution(self):
        self.write()
        with patch("researcher.service.environment.os.getcwd", return_value=str(self.root)):
            self.assertEqual(read_env_file(Path("synthetic.env")), {"KEY": "synthetic-value"})

    def test_same_size_mutation_during_read_is_rejected(self):
        self.write("KEY=old-value\n")
        real_read = os.read
        mutated = False
        def read(fd, count):
            nonlocal mutated
            body = real_read(fd, count)
            if not mutated:
                mutated = True
                self.path.write_text("KEY=new-value\n")
            return body
        with patch("researcher.service.environment.os.read", side_effect=read):
            with self.assertRaisesRegex(ServiceError, "ENV_FILE_CHANGED"):
                read_env_file(self.path)

    def test_leaf_replacement_during_read_is_rejected(self):
        self.write()
        replacement = self.root / "replacement.env"
        replacement.write_text("KEY=replacement")
        replacement.chmod(0o600)
        real_read = os.read
        replaced = False
        def read(fd, count):
            nonlocal replaced
            body = real_read(fd, count)
            if not replaced:
                replaced = True
                os.replace(replacement, self.path)
            return body
        with patch("researcher.service.environment.os.read", side_effect=read):
            with self.assertRaisesRegex(ServiceError, "ENV_FILE_CHANGED"):
                read_env_file(self.path)

    def test_ancestor_replacement_during_read_is_rejected(self):
        directory = self.root / "parent"
        directory.mkdir()
        self.path = directory / "synthetic.env"
        self.write()
        real_read = os.read
        replaced = False
        def read(fd, count):
            nonlocal replaced
            body = real_read(fd, count)
            if not replaced:
                replaced = True
                directory.rename(self.root / "old-parent")
                directory.mkdir()
            return body
        with patch("researcher.service.environment.os.read", side_effect=read):
            with self.assertRaisesRegex(ServiceError, "ENV_FILE_CHANGED"):
                read_env_file(self.path)

    def test_success_and_failure_never_mutate_ambient_environment(self):
        with patch.dict(os.environ, {"KEY": "ambient-synthetic"}):
            before = dict(os.environ)
            self.write("KEY=file-synthetic")
            self.assertEqual(read_env_file(self.path)["KEY"], "file-synthetic")
            self.failure("KEY=$(synthetic)")
            self.assertEqual(dict(os.environ), before)


class ConfigurationFileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.path = self.root / "synthetic-config.json"

    def write(self, data=b'{"synthetic":true}', mode=0o644):
        if self.path.exists():
            self.path.chmod(0o600)
        self.path.write_bytes(data)
        self.path.chmod(mode)

    def test_public_or_packaged_readonly_config_needs_no_owner_match(self):
        for mode in (0o644, 0o444, 0o600):
            self.write(mode=mode)
            with patch("researcher.service.environment.os.getuid", side_effect=AssertionError("owner check")):
                self.assertEqual(read_config_file(self.path), '{"synthetic":true}')

    def test_full_size_limit_and_utf8_validation(self):
        self.write(b" " * 262144)
        self.assertEqual(len(read_config_file(self.path)), 262144)
        self.write(b" " * 262145)
        with self.assertRaisesRegex(ServiceError, "CONFIG_FILE_TOO_LARGE"):
            read_config_file(self.path)
        self.write(b"\xff")
        with self.assertRaisesRegex(ServiceError, "CONFIG_FILE_ENCODING"):
            read_config_file(self.path)

    def test_fifo_directory_and_hardlink_reject_without_reading(self):
        self.write()
        hard = self.root / "hard-config.json"
        os.link(self.path, hard)
        fifo = self.root / "pipe-config.json"
        os.mkfifo(fifo, 0o600)
        with patch("researcher.service.environment.os.read", side_effect=AssertionError("must not read")):
            for candidate in (self.path, hard, fifo, self.root):
                with self.assertRaisesRegex(ServiceError, "CONFIG_FILE_UNSAFE"):
                    read_config_file(candidate)

    def test_leaf_and_ancestor_symlinks_reject(self):
        self.write()
        leaf = self.root / "config-alias"
        leaf.symlink_to(self.path)
        ancestor = self.root / "ancestor-alias"
        ancestor.symlink_to(self.root, target_is_directory=True)
        for candidate in (leaf, ancestor / self.path.name):
            with self.assertRaisesRegex(ServiceError, "CONFIG_FILE_UNSAFE"):
                read_config_file(candidate)

    def test_rewrite_during_read_is_rejected(self):
        self.write(b"same length before")
        real_read = os.read
        changed = False
        def read(fd, count):
            nonlocal changed
            data = real_read(fd, count)
            if not changed:
                changed = True
                self.path.write_bytes(b"same length after!")
            return data
        with patch("researcher.service.environment.os.read", side_effect=read):
            with self.assertRaisesRegex(ServiceError, "CONFIG_FILE_CHANGED"):
                read_config_file(self.path)

    def test_replacement_during_read_is_rejected(self):
        self.write()
        replacement = self.root / "replacement-config.json"
        replacement.write_bytes(b'{"replacement":true}')
        real_read = os.read
        changed = False
        def read(fd, count):
            nonlocal changed
            data = real_read(fd, count)
            if not changed:
                changed = True
                os.replace(replacement, self.path)
            return data
        with patch("researcher.service.environment.os.read", side_effect=read):
            with self.assertRaisesRegex(ServiceError, "CONFIG_FILE_CHANGED"):
                read_config_file(self.path)

    def test_failure_never_echoes_path_or_content(self):
        self.path = self.root / "private-query-must-not-appear.json"
        with self.assertRaises(ServiceError) as caught:
            read_config_file(self.path)
        self.assertEqual(str(caught.exception), "CONFIG_FILE_UNSAFE")
        self.write(b"PRIVATE_VALUE_MUST_NOT_APPEAR\xff")
        with self.assertRaises(ServiceError) as caught:
            read_config_file(self.path)
        self.assertEqual(str(caught.exception), "CONFIG_FILE_ENCODING")


class CredentialReaderTests(unittest.TestCase):
    def test_only_selected_names_are_accessible(self):
        read = credential_reader({"ALLOWED": "synthetic", "UNKNOWN": "unselected"}, ["ALLOWED"])
        self.assertEqual(read("ALLOWED"), "synthetic")
        for name in ("UNKNOWN", "UNLISTED", None, []):
            with self.assertRaisesRegex(ServiceError, "ENV_CREDENTIAL_NOT_ALLOWED"):
                read(name)

    def test_blank_missing_and_wrong_type_never_fall_back_to_environment(self):
        with patch.dict(os.environ, {"KEY": "ambient-synthetic"}):
            before = dict(os.environ)
            for value in ({}, {"KEY": ""}, {"KEY": " "}, {"KEY": None}):
                read = credential_reader(value, {"KEY"})
                with self.assertRaisesRegex(ServiceError, "CREDENTIAL_UNAVAILABLE"):
                    read("KEY")
            self.assertEqual(dict(os.environ), before)

    def test_policy_and_values_are_snapshotted(self):
        values, allowed = {"KEY": "original-synthetic"}, ["KEY"]
        read = credential_reader(values, allowed)
        values["KEY"] = "changed-synthetic"
        allowed.append("OTHER")
        self.assertEqual(read("KEY"), "original-synthetic")
        with self.assertRaisesRegex(ServiceError, "ENV_CREDENTIAL_NOT_ALLOWED"):
            read("OTHER")

    def test_invalid_policy_is_sanitized(self):
        for allowed in ("KEY", ["bad-name"], [None], ["A" * 97], ["A"] * 1025):
            with self.assertRaisesRegex(ServiceError, "ENV_CREDENTIAL_POLICY_INVALID"):
                credential_reader({"KEY": "synthetic"}, allowed)


if __name__ == "__main__":
    unittest.main()
