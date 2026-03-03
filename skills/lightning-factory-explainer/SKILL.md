---
name: lightning-factory-explainer
description: This skill should be used when the user asks to "explain Lightning channel factories", "describe SuperScalar protocol", "understand shared UTXOs for Lightning onboarding", or mentions Decker-Wattenhofer trees, timeout-signature trees, MuSig2, Taproot channel factories, or scalable Lightning onboarding.
---

# Lightning Channel Factory Explainer

Lightning channel factories represent a fundamental scaling approach for Bitcoin's Lightning Network. Rather than requiring individual on-chain transactions for each channel, factories enable an LSP (Lightning Service Provider) and N clients to share a single UTXO while maintaining full Lightning compatibility. The SuperScalar protocol implements this using a combination of Decker-Wattenhofer invalidation trees, timeout-signature trees, and Poon-Dryja channels — requiring no consensus changes to Bitcoin.

## When to Activate

Activate this skill when:
- Explaining Bitcoin Lightning channel factories and scalable onboarding
- Discussing the SuperScalar protocol architecture and design decisions
- Comparing approaches to Lightning Network scaling
- Evaluating shared UTXO constructions for multi-party channels
- Understanding Decker-Wattenhofer trees, timeout-signature trees, or MuSig2 in context

## Core Concepts

Channel factories address the fundamental on-chain bottleneck of Lightning Network onboarding. Traditional Lightning requires one on-chain transaction per channel. Factories amortize this cost across N users by constructing a tree of off-chain transactions rooted in a single shared UTXO.

SuperScalar combines three cryptographic constructions: Decker-Wattenhofer invalidation trees provide state updates without on-chain transactions, timeout-signature trees enable efficient unilateral exits with O(log N) complexity, and Poon-Dryja channels at the leaves provide standard Lightning channel semantics including HTLC and PTLC forwarding.

Key design properties include: no soft fork required (works on Bitcoin today with Taproot and MuSig2), full Lightning compatibility, watchtower support for breach detection, and LSP-assisted cooperative operations for the common case.

## References

- SuperScalar project: https://github.com/8144225309/SuperScalar
- Website: https://SuperScalar.win
- Original proposal: https://delvingbitcoin.org/t/superscalar-laddered-timeout-tree-structured-decker-wattenhofer-factories/1143
