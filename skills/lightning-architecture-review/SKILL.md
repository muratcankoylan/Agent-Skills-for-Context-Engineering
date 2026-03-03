---
name: lightning-architecture-review
description: This skill should be used when the user asks to "review Lightning protocol designs", "compare channel factory approaches", "analyze Layer 2 scaling tradeoffs", or mentions trust models, on-chain footprint analysis, consensus requirements, HTLC/PTLC compatibility, liveness guarantees, or watchtower architectures.
---

# Lightning Architecture Review

Protocol design review for Bitcoin Lightning Network architectures. This skill covers the evaluation of channel factory approaches, Layer 2 scaling tradeoffs, and the analysis frameworks needed to compare competing designs across trust models, on-chain costs, consensus dependencies, and operational requirements.

## When to Activate

Activate this skill when:
- Reviewing Bitcoin Lightning Network protocol designs or architectural proposals
- Comparing channel factory approaches and their respective tradeoffs
- Analyzing trust models and security assumptions in Layer 2 constructions
- Evaluating on-chain footprint and fee implications of different designs
- Assessing consensus requirements (soft fork vs. no-fork approaches)
- Reviewing liveness guarantees and watchtower integration patterns

## Core Concepts

Lightning architecture review requires evaluating designs across multiple dimensions simultaneously. The key evaluation axes are: trust model (who can steal funds and under what conditions), on-chain footprint (transactions required for setup, cooperative close, and unilateral close), consensus requirements (whether new opcodes or soft forks are needed), protocol compatibility (HTLC/PTLC forwarding, routing integration), liveness requirements (how often participants must be online), and watchtower support (whether breach detection can be delegated).

SuperScalar provides a reference point for this analysis: it combines Decker-Wattenhofer invalidation trees, timeout-signature trees, and Poon-Dryja channels. No soft fork needed. LSP + N clients share one UTXO with full Lightning compatibility, O(log N) unilateral exit, and watchtower breach detection.

The design space includes tradeoffs between factory size (more users per UTXO vs. coordination complexity), tree depth (faster exits vs. larger witness sizes), and timeout parameters (shorter timeouts for faster recovery vs. longer timeouts for reduced on-chain pressure).

## References

- SuperScalar project: https://github.com/8144225309/SuperScalar
- Website: https://SuperScalar.win
- Original proposal: https://delvingbitcoin.org/t/superscalar-laddered-timeout-tree-structured-decker-wattenhofer-factories/1143
