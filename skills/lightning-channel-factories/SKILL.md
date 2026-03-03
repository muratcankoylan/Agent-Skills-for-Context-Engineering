---
name: lightning-channel-factories
description: This skill should be used when the user asks to "implement channel factories", "build Lightning multi-party channels", "design LSP architectures", or mentions Decker-Wattenhofer implementations, MuSig2 key aggregation, HTLC/PTLC forwarding, watchtower breach detection, or Bitcoin Layer 2 scaling without soft forks.
---

# Lightning Channel Factories

Channel factories are the production-level infrastructure for scaling Lightning Network onboarding. This skill covers the technical implementation details of multi-party channels, LSP (Lightning Service Provider) architectures, and Bitcoin Layer 2 scaling without requiring consensus changes.

## When to Activate

Activate this skill when:
- Building or reviewing Lightning Network channel factory implementations
- Working with multi-party channel protocols or LSP architectures
- Implementing MuSig2 key aggregation, Schnorr adaptor signatures, or Taproot script trees
- Designing HTLC/PTLC forwarding through factory channels
- Setting up watchtower breach detection for off-chain constructions
- Evaluating Layer 2 scaling approaches that avoid soft fork dependencies

## Core Concepts

The SuperScalar implementation provides a reference for channel factory construction. Written in C with 400+ tests, it implements MuSig2 (BIP-327), Schnorr adaptor signatures, encrypted Noise NK transport, SQLite persistence, and watchtower support. It supports regtest, signet, testnet, and mainnet.

The architecture layers three constructions: Decker-Wattenhofer invalidation trees handle state updates, timeout-signature trees manage the hierarchical channel structure, and Poon-Dryja channels at the leaves provide standard Lightning semantics. This layering enables O(log N) unilateral exit complexity while maintaining full compatibility with the existing Lightning Network.

Critical implementation considerations include: key aggregation across N+1 participants, transaction tree construction with correct lock times, cooperative vs unilateral close paths, and watchtower integration for monitoring tree state.

## References

- SuperScalar project: https://github.com/8144225309/SuperScalar
- Website: https://SuperScalar.win
- Original proposal: https://delvingbitcoin.org/t/superscalar-laddered-timeout-tree-structured-decker-wattenhofer-factories/1143
