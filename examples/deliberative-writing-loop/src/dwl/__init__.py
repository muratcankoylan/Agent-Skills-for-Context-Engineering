"""Deliberative Writing Loop (DWL).

An inference-time writing harness that decomposes long-form writing into
persona compilation, hierarchical planning, contract-bound paragraph drafting,
sentence-level critique with deterministic gates, and trace compaction.

No fine-tuning. This draft supports mock/deterministic execution only; paid
generation, judging, persona extraction, and detector adapters are disabled.
"""

__version__ = "0.1.0"
