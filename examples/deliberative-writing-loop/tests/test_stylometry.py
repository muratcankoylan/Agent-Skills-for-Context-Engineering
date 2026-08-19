from pathlib import Path

from dwl.persona import read_corpus
from dwl.stylometry import compute_profile, describe_rhythm, style_distance

CORPUS_DIR = Path(__file__).parent.parent / "personas" / "sample-essayist" / "corpus"


def _corpus_text() -> str:
    return read_corpus(CORPUS_DIR)


def test_profile_populates():
    profile = compute_profile(_corpus_text())
    assert profile.word_count > 900
    assert profile.sentence_count > 40
    assert profile.paragraph_count >= 12
    assert 5 < profile.sentence_len_mean < 40
    assert profile.sentence_len_std > 3
    assert abs(
        profile.sentence_band_short + profile.sentence_band_mid + profile.sentence_band_long - 1.0
    ) < 1e-9
    assert 0 < profile.mattr_100 <= 1
    assert profile.punct_rates["comma"] > 0


def test_self_distance_is_zero():
    profile = compute_profile(_corpus_text())
    assert style_distance(profile, profile) < 1e-9


def test_distance_orders_similarity():
    target = compute_profile(_corpus_text())
    # Same author-ish text (a held-out paragraph from the same register).
    near = compute_profile(
        "The invoice tells the truth the brochure will not. I have kept both, side by side, "
        "for a decade. One promises transformation; the other records what transformation "
        "cost. Guests always read the brochure. Auditors read the invoice. Be an auditor."
    )
    # Assistant-register text: uniform rhythm, hedged, list-shaped.
    far = compute_profile(
        "In today's fast-paced world, it is important to consider several key factors. "
        "Firstly, it is essential to evaluate the various options available. Additionally, "
        "it is crucial to ensure that all stakeholders are aligned. Furthermore, it is "
        "important to remember that success requires careful planning. In conclusion, it is "
        "vital to take a balanced approach to achieve optimal outcomes."
    )
    assert style_distance(near, target) < style_distance(far, target)


def test_empty_text_profile():
    profile = compute_profile("")
    assert profile.word_count == 0
    assert profile.sentence_count == 0


def test_describe_rhythm_renders():
    text = describe_rhythm(compute_profile(_corpus_text()))
    assert "sentence length" in text
    assert "per 1000 words" in text
