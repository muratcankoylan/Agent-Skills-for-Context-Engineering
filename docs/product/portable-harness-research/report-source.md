# Research record: portable research improvement loops

Research date: 2026-09-07. Canonical working synthesis for the [architecture and runbook](../portable-harness.md). Status: engineering research, not a systematic literature review or an empirical claim of general autonomous improvement. The claim ledger accompanies this record.

## Questions and method

We compared fixed-incumbent improvement, archive search and evaluator co-evolution; asked which require evidence absent from this repository; and prioritized measurement corruption, adaptive overfitting and deployment authority. One Parallel Search discovery request was followed by primary paper methods/appendix inspection, reference-repository inspection and three targeted architecture/evaluation/adversarial reviews. We stopped when the first implementation decision was resolved. No literature-search completeness or state-of-the-art ranking is claimed. RQGM's HTML endpoint failed; its PDF was inspected instead.

## Evidence that changes the design

- **Reported method:** ADAS separates the candidate space, search procedure and evaluation. Its Meta Agent Search uses validation feedback and reports separate test/transfer results. **Our judgment:** preserve these interfaces but start with finite enumeration; the paper does not show that archive search improves this repository's research quality. [Hu, Lu and Clune, ADAS, v2](https://arxiv.org/html/2408.08435v2).
- **Reported failure:** DGM's reward-hacking appendix describes removal of logging markers being rewarded without correcting the underlying hallucinated-tool behavior. **Our judgment:** evaluator-code immutability alone is insufficient; measurement inputs and the evaluated population must also be bound and independently reconstructed. Its coding results do not establish general scientific capability. [Zhang et al., DGM, v2, Appendix H](https://arxiv.org/html/2505.22954v2).
- **Reported constraint:** AlphaEvolve relies on automated evaluation and supports staged evaluators; the authors identify tasks needing manual experiments as a limitation. **Our judgment:** begin with exact-byte/provenance/coverage invariants; model-judged research merit remains a separate validation problem. [Novikov et al., AlphaEvolve, v1, Sections 2 and 6](https://arxiv.org/html/2506.13131v1).
- **Reported method with qualifications:** RQGM holds evaluator behavior fixed within epochs, selects replacements using independent anchors and invalidates dependent utility history. Its posterior-quantile selection is not our paired superiority test, and epoch-local claims do not establish global improvement. **Our judgment:** an evaluator revision is a separately evaluated candidate, never a mid-run scoring change. [Iacob et al., RQGM, v2, Sections 3 and Appendices F/G](https://arxiv.org/pdf/2606.26294).
- **Established under stated mathematical assumptions:** adaptive feedback can undermine ordinary holdout reuse. The reusable-holdout paper's guarantees require its specific mechanisms and assumptions. **Our judgment:** keep an exposure ledger and a sealed final evaluation; ordinary versioned fixtures do not inherit reusable-holdout guarantees. [Dwork et al., v2](https://arxiv.org/html/1506.02629v2).

These sources support a disciplined improvement process, not unrestricted self-modification. DGM motivates archive exploration; its cost and proxy limitations argue for measuring against an incumbent loop first. RQGM challenges permanently fixed evaluators, not fixed scoring within one experiment. Both are compatible with a smaller trusted authority/evaluation boundary and separately reviewed evaluator epochs.

## Repository evidence and design choice

Inspection found reusable source capture/replay, strict context records, editable-surface candidate freezing and private content-addressed storage. It did not find accepted production WorkOrderSpec/ExperimentSpec/EvaluationObservation/PromotionRecord ownership. Current organization events cover research-run transitions, not these new experiment records. A schema-valid candidate is not an authorized production action.

We therefore implemented a private proposal experiment rather than inventing accepted schemas. Two predeclared data policies are evaluated on the entire frozen development population. The fixed evaluator reconstructs every score and checks source text, provenance, lane/failure visibility, selection accounting and byte ceilings. The candidate cannot execute or change the evaluator. This finite, deliberately non-novel workload tests lifecycle integrity before adding model generation or executable candidates.

## What would change the recommendation

Archive search needs a repeatable, cost-matched gain on independent research needs. Automatic code application needs accepted owner contracts plus externally enforced isolation and rollback evidence. Automated semantic evaluation needs calibration against blinded independent judgments and downstream tasks. None can be inferred from packet capacity or a successful JSON replay.

## Sources

1. Hu, Lu and Clune. [Automated Design of Agentic Systems](https://arxiv.org/html/2408.08435v2), arXiv:2408.08435v2, 2025-03-02.
2. Zhang et al. [Darwin Gödel Machine](https://arxiv.org/html/2505.22954v2), arXiv:2505.22954v2, 2025-09-26. [Author reference implementation](https://github.com/jennyzzt/dgm), inspected for execution boundaries, not imported.
3. Novikov et al. [AlphaEvolve](https://arxiv.org/html/2506.13131v1), arXiv:2506.13131v1, 2025-06-16.
4. Iacob et al. [The Red Queen Gödel Machine](https://arxiv.org/pdf/2606.26294), arXiv:2606.26294v2, 2026-06-29; preliminary preprint.
5. Dwork et al. [Generalization in Adaptive Data Analysis and Holdout Reuse](https://arxiv.org/html/1506.02629v2), arXiv:1506.02629v2, 2015-09-25.

Accessed 2026-09-07. Reported empirical results were not independently reproduced. No paper's performance numbers are used as measurements of this project.
