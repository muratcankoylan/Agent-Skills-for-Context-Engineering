from dwl.memory import RunMemory, distinctive_grams


def test_distinctive_grams_skip_function_word_runs():
    grams = distinctive_grams("it was the end of the day")
    # every 4-gram here is nearly all stopwords except "end"/"day" singletons
    assert all(sum(1 for t in g if t in ("end", "day")) <= 2 for g in grams)


def test_spent_phrase_detection():
    memory = RunMemory()
    memory.commit_paragraph(0, "The polished nail by the door held three houses of work.", "s", [])
    hits = memory.repeated_phrases_in("Again the polished nail by the door held everything.")
    assert any("polished nail" in phrase for phrase in hits)
    assert memory.repeated_phrases_in("A completely different sentence about carpentry.") == []


def test_lesson_promotion_needs_repetition():
    memory = RunMemory()
    memory.observe_finding("opener_run", "avoid opener runs")
    assert memory.lessons == []
    memory.observe_finding("opener_run", "avoid opener runs")
    assert memory.lessons == ["avoid opener runs"]
    # No duplicates on further repeats.
    memory.observe_finding("opener_run", "avoid opener runs")
    assert len(memory.lessons) == 1


def test_render_context_structure():
    memory = RunMemory()
    memory.commit_paragraph(0, "First paragraph text here.", "Establishes the premise.", ["claim one"])
    memory.commit_paragraph(1, "Second paragraph text follows the first.", "Develops the premise.", [])
    context = memory.render_context()
    assert "P1: Establishes the premise." in context
    assert "PREVIOUS PARAGRAPH" in context
    assert "Second paragraph text follows the first." in context
    assert "claim one" in context
    # Older paragraph text is NOT in context verbatim.
    assert "First paragraph text here." not in context


def test_render_context_compacts_under_pressure():
    memory = RunMemory()
    for i in range(30):
        memory.commit_paragraph(i, f"Paragraph {i} body text sentence number {i}.", f"Summary {i} " + "x" * 300, [])
    context = memory.render_context(max_chars=2500)
    assert len(context) <= 3200  # compaction happened (verbatim tail + ledger kept)
    assert "PREVIOUS PARAGRAPH" in context


def test_roundtrip_serialization():
    memory = RunMemory()
    memory.commit_paragraph(0, "The polished nail by the door held.", "summary", ["c1"])
    memory.observe_finding("k", "lesson", threshold=1)
    restored = RunMemory.from_dict(memory.to_dict())
    assert restored.claims == ["c1"]
    assert restored.lessons == ["lesson"]
    assert restored.spent_phrases == memory.spent_phrases
