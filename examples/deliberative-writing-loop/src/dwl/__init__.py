"""Deliberative Writing Loop (DWL).

An inference-time writing harness that decomposes long-form writing into
persona compilation, hierarchical planning, contract-bound paragraph drafting,
sentence-level critique with deterministic gates, and trace compaction.

No fine-tuning. Any chat-completion model works through the adapter layer.
"""

__version__ = "0.1.0"
