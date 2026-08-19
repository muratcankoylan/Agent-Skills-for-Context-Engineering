from pathlib import Path

from dwl.persona import read_corpus
from dwl.sloplex import SlopProfiler

CORPUS_DIR = Path(__file__).parent.parent / "personas" / "sample-essayist" / "corpus"


def _profiler() -> SlopProfiler:
    return SlopProfiler(read_corpus(CORPUS_DIR))


def test_overused_ngram_flagged():
    # "tapestry" never appears in the corpus; leaning on it repeatedly is overuse.
    text = (
        "The tapestry of options unfolds. Every choice weaves the tapestry further. "
        "A rich tapestry rewards the patient reader. The tapestry never ends."
    )
    report = _profiler().score(text)
    kinds = {finding.kind for finding in report.findings}
    assert "ngram_ratio" in kinds
    assert any("tapestry" in finding.detail for finding in report.findings)


def test_corpus_itself_scores_low():
    corpus = read_corpus(CORPUS_DIR)
    profiler = SlopProfiler(corpus)
    report = profiler.score(corpus[: len(corpus) // 3])
    # A slice of the reference should raise few or no ratio findings.
    ratio_findings = [f for f in report.findings if f.kind == "ngram_ratio"]
    assert len(ratio_findings) <= 2


def test_contrastive_template_flagged():
    text = (
        "The point stands on its own merits. This is not about tools, it's about attention. "
        "The rest follows from that."
    )
    report = _profiler().score(text)
    assert any(finding.kind == "template" for finding in report.findings)


def test_opener_run_flagged():
    text = (
        "Smith's plan was simple. Smith's methods were not. Smith's creditors knew both. "
        "The bank learned last."
    )
    report = _profiler().score(text)
    runs = [f for f in report.findings if f.kind == "opener_run"]
    assert len(runs) == 1
    assert "smith's" in runs[0].detail


def test_cross_paragraph_echo_flagged():
    text = (
        "The polished nail by the door told the story.\n\n"
        "Years later, the polished nail by the door still held."
    )
    report = _profiler().score(text)
    echoes = [f for f in report.findings if f.kind == "echo"]
    assert echoes
    assert "paragraph 1" in echoes[0].detail


def test_clean_text_produces_no_structural_findings():
    text = (
        "The invoice tells the truth. Brochures promise transformation; ledgers record its "
        "price. Guests read one, auditors read the other, and only one of them gets paid "
        "for accuracy."
    )
    report = _profiler().score(text)
    structural = [f for f in report.findings if f.kind in ("opener_run", "echo", "template")]
    assert structural == []
