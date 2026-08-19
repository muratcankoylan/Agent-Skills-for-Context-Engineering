import json
from pathlib import Path

import pytest

from dwl.adapters.base import MockAdapter
from dwl.persona import Persona, compile_persona

CORPUS_DIR = Path(__file__).parent.parent / "personas" / "sample-essayist" / "corpus"

TACIT = {
    "voice": "Skeptical, concrete, first-person; treats the reader as a peer.",
    "argument_moves": ["Open with a strong claim, then complicate it."],
    "sentence_moves": ["Follow a long sentence with a short verdict."],
    "vocabulary": "Trade and ledger imagery; plain register.",
    "never_do": ["Never hedge with 'perhaps' stacking."],
    "signature_risks": ["Overdoing aphorisms until they become fortune cookies."],
}


def test_deterministic_compile_without_adapter():
    persona = compile_persona("sample", CORPUS_DIR, adapter=None)
    assert persona.style.word_count > 900
    assert persona.tacit == {}
    assert persona.exemplars
    tags = {e["tag"] for e in persona.exemplars}
    assert "opening" in tags and "closing" in tags
    assert persona.corpus_hash == compile_persona("sample", CORPUS_DIR).corpus_hash


def test_compile_with_llm_tacit_layer():
    adapter = MockAdapter(responses=[json.dumps(TACIT)])
    persona = compile_persona("sample", CORPUS_DIR, adapter=adapter)
    assert persona.tacit["voice"].startswith("Skeptical")
    rules = persona.rules_block()
    assert "NEVER DO" in rules
    assert "RHYTHM TARGETS" in rules
    assert "ARGUMENT MOVES" in rules


def test_compile_rejects_non_json_tacit():
    adapter = MockAdapter(responses=["I cannot produce JSON, sorry."])
    with pytest.raises(ValueError):
        compile_persona("sample", CORPUS_DIR, adapter=adapter)


def test_persona_save_load_roundtrip(tmp_path):
    adapter = MockAdapter(responses=[json.dumps(TACIT)])
    persona = compile_persona("sample", CORPUS_DIR, adapter=adapter)
    path = tmp_path / "persona.json"
    persona.save(path)
    restored = Persona.load(path)
    assert restored.name == persona.name
    assert restored.style.to_dict() == persona.style.to_dict()
    assert restored.tacit == persona.tacit
    assert restored.corpus_text == persona.corpus_text


def test_exemplar_block_filters_by_tag():
    persona = compile_persona("sample", CORPUS_DIR)
    block = persona.exemplar_block(tags=["opening"], limit=1)
    assert "[opening]" in block
