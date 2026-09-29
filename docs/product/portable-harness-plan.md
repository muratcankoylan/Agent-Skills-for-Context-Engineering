# Portable self-improving research harness: working plan

Audience: maintainers, agent/runtime implementers and research-paper reviewers. Date: 2026-09-07. This plan records intended work, not production readiness or a claim of autonomous scientific capability.

## Objective and boundaries

Build on this repository's source/evidence, freeze, evaluation and journal primitives to support a runtime-independent research-to-proposal loop. Codex is one operator, not the product runtime. The product should reduce human editorial work while preserving independent evaluation, inspectable failures, bounded spending and explicit repository authority.

The integration checkout contains uncommitted work. Preserve the original checkout and unrelated changes. This task authorizes research, local implementation and tests; it does not authorize commits, pushes, merges, cloud activation or bypassing the current paid-provider acceptance gate. The existing observation heartbeat was paused during source changes and restored with its original scope at handoff.

## Research questions and competing hypotheses

1. Does a bounded archive of candidates outperform a simpler incumbent loop enough to justify its cost? Compare DGM/ADAS/AlphaEvolve evidence and transfer limitations.
2. Which parts can be deterministic, and which need a model or independent domain judgment? Avoid using structural tests as a scientific-quality metric.
3. Can an editable surface, immutable evaluator and sealed evaluation population prevent the most likely self-improvement failures? Examine reward hacking, adaptive holdout reuse and selection bias.
4. What is the smallest portable execution interface compatible with current owner contracts? Compare a local single-writer process, distributed workflow service and runtime-native agent orchestration.
5. What results would support a publishable contribution rather than a systems demo? Specify controls, ablations, uncertainty, cost and human-review burden before experiments.

Primary evidence classes: research papers with methods/limitations, first-party reference implementations, official execution/security documentation, current repository code and reproducible local measurements. Discovery sources are not accepted scientific evidence.

## Stages

| Stage | Status | Exit evidence |
| --- | --- | --- |
| Audit and primary-source discovery | complete | Artifact freeze/CAS and source replay are reusable; experiment/acceptance owners remain missing |
| Targeted research and design | complete | ADAS, DGM and AlphaEvolve primary methods reviewed; evaluator co-evolution reconciled as between-epoch change, never candidate-controlled scoring |
| Implement portable vertical loop | complete | Data-only candidate/evidence freeze, strict complete campaign import, bounded progression, stable public errors and inert results implemented |
| Adversarial and reproducibility verification | complete | 1,078 full-suite tests pass; 37 lifecycle tests pass on both Python 3.11/3.12; real forward/reverse experiments replay and resume exactly |
| OSS/paper/deployment handoff | complete | Research synthesis, proposed paper protocol and deployment gates written; 143 publication checks pass, prospective secret scan is clean, original bounded observation schedule restored |

Exactly one stage is active while this bounded milestone is underway. Completion of these stages is not production activation. There is no available plan-update tool in this environment; this versioned document is the durable plan.

This bounded milestone is complete. The larger autonomous production product is not: remaining owner, provider, isolation, semantic-evaluation, packaging, operator and canary gates are tracked in the [architecture/runbook](portable-harness.md) and [measured results](portable-harness-results.md).

## Initial verification strategy

Use narrow deterministic tests before broad suites. Exercise real frozen data and explicit negative controls. Test candidate attempts to alter evaluator, budget, selected population, permissions or evidence; missing/partial results; stale manifests; duplicate completion; restart after intent; and misleading success labels. Do not run untrusted generated code on the host. Retain original failures and distinguish replay from fresh execution.

The research paper must report the full attempted population and costs, not only winners. A functioning deterministic loop is a systems result, not proof of general scientific discovery or autonomous repository improvement. Production readiness requires separate accepted provider/executor, persistence, auth, recovery and deployment evidence.

## Selected first slice

Implement a runtime-independent, zero-model packet-policy experiment runner. It imports complete source campaigns through replay verification, freezes the complete experimental population and fixed budgets, restricts candidates to a data-only packet policy, freezes/materializes candidates through the existing CAS boundary, evaluates both incumbent and variant, and emits an immutable proposal/no-improvement/rejection report. No generated Python or shell runs on the host. All attempted variants remain visible; exact resume revalidates inputs and deterministic outputs. Unknown in-flight outcomes remain stopped rather than being silently repeated.

This is a finite development experiment on context capacity. It does not create registered production experiment kinds, write experiment events into the research-run journal, expose hidden tests, activate the amended SPEC-003 successor, or grant merge authority. It is deliberately a small executable bridge to the owner-contract work, not another accepted-state service.

The larger architecture is a single-writer coordinator with replaceable research/proposer/evaluator/executor adapters and a separate authority kernel. A population archive, distributed queue or new hosted platform must justify itself against that baseline before adoption. Evaluator revisions are separately versioned experiments with independent anchors and exposure accounting, not edits an evaluated candidate can make during its own run.
