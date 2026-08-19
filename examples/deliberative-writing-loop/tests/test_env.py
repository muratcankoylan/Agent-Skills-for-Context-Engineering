import os

from dwl.env import find_env_file, key_status, load_env, mask, parse_env_text


def test_parse_basic_and_comments():
    values = parse_env_text(
        """# a comment

ANTHROPIC_API_KEY=sk-ant-123
export OPENAI_API_KEY=sk-oai-456
PANGRAM_API_KEY=
   # indented comment
"""
    )
    assert values["ANTHROPIC_API_KEY"] == "sk-ant-123"
    assert values["OPENAI_API_KEY"] == "sk-oai-456"
    assert values["PANGRAM_API_KEY"] == ""


def test_parse_quotes_and_inline_comments():
    values = parse_env_text(
        """QUOTED="value with spaces"
SINGLE='single quoted'
INLINE=bare-value # trailing note
HASH_IN_QUOTES="keep # this"
"""
    )
    assert values["QUOTED"] == "value with spaces"
    assert values["SINGLE"] == "single quoted"
    assert values["INLINE"] == "bare-value"
    assert values["HASH_IN_QUOTES"] == "keep # this"


def test_parse_ignores_malformed_lines():
    values = parse_env_text("NOEQUALS\n=novalue\nGOOD=yes")
    assert values == {"GOOD": "yes"}


def test_load_env_does_not_override_real_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DWL_TEST_KEY=from-file\nDWL_TEST_NEW=fresh\n", encoding="utf-8")
    monkeypatch.setenv("DWL_TEST_KEY", "from-shell")
    monkeypatch.delenv("DWL_TEST_NEW", raising=False)
    applied = load_env(env_file)
    assert os.environ["DWL_TEST_KEY"] == "from-shell"
    assert os.environ["DWL_TEST_NEW"] == "fresh"
    assert set(applied) == {"DWL_TEST_NEW"}


def test_load_env_override_flag(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DWL_TEST_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("DWL_TEST_KEY", "from-shell")
    load_env(env_file, override=True)
    assert os.environ["DWL_TEST_KEY"] == "from-file"


def test_load_env_skips_blank_placeholders(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DWL_TEST_BLANK=\n", encoding="utf-8")
    monkeypatch.delenv("DWL_TEST_BLANK", raising=False)
    assert load_env(env_file) == {}
    assert "DWL_TEST_BLANK" not in os.environ


def test_load_env_missing_file_is_not_an_error(tmp_path):
    assert load_env(tmp_path / "nope.env") == {}


def test_find_env_file_searches_parents(tmp_path):
    (tmp_path / ".env").write_text("K=v\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_env_file(nested) == (tmp_path / ".env").resolve()
    assert find_env_file(tmp_path / "sibling-missing") is not None


def test_mask_never_reveals_full_secret():
    assert mask("sk-ant-abcdefghij") == "...ghij"
    assert mask("") == "<unset>"
    assert mask("abc") == "***"


def test_key_status_reports_all_three_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-wxyz")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PANGRAM_API_KEY", raising=False)
    status = key_status()
    assert status["ANTHROPIC_API_KEY"] == "...wxyz"
    assert status["OPENAI_API_KEY"] == "<unset>"
    assert set(status) == {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PANGRAM_API_KEY"}
