from dwl.textseg import ngrams, split_paragraphs, split_sentences, words


def test_split_sentences_basic():
    text = "The test is simple. Ask the question! Did it work? It did."
    assert split_sentences(text) == [
        "The test is simple.",
        "Ask the question!",
        "Did it work?",
        "It did.",
    ]


def test_split_sentences_abbreviations():
    text = "Dr. Smith arrived at noon. He left by three."
    assert len(split_sentences(text)) == 2


def test_split_sentences_quotes():
    text = 'He said "stop." Then he left.'
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert sentences[0].endswith('"stop."')


def test_split_paragraphs():
    text = "First para line one.\nStill first.\n\nSecond para."
    paragraphs = split_paragraphs(text)
    assert len(paragraphs) == 2
    assert paragraphs[1] == "Second para."


def test_words_contractions_kept():
    assert words("It's the builder's day-off.") == ["it's", "the", "builder's", "day-off"]


def test_ngrams():
    tokens = ["a", "b", "c"]
    assert ngrams(tokens, 2) == [("a", "b"), ("b", "c")]
    assert ngrams(tokens, 4) == []
