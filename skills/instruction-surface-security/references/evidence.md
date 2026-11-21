# Research evidence and limits

## Mind Viruses

Papadopoulos et al. study self-propagating instructions in a small coding collaboration and a chain of agents with context resets. Their experiments motivate observing durable state and transfer separately. They do not evaluate the activation gate in this skill. [Mind Viruses, arXiv v1](https://arxiv.org/abs/2608.10218v1)

| Observation | Interpretation for the skill |
| --- | --- |
| In §3.3.2 Table 3, 88% and 12% are storage shares among already-infected agents. The reported onward infection success rates are 55% for the injected `SOUL.md` group and 17% for the other-files group. (`claim-instruction-surface-storage-observation`) | Measure what reaches the effective instruction context after restart. The comparison is observational and specific to the tested harness. [Table 3](https://arxiv.org/pdf/2608.10218v1#page=15) |
| In Appendix C, a defensive warning in the Claude Haiku 4.5 action-chain setup yielded no spread beyond the first hop across 15 generations and more than 150 candidates. First-hop action execution still occurred in rare cases. The mutator received full interaction rollouts and was aware of the warning. (`claim-instruction-surface-warning-scope`) | Treat the warning as a measured layer in the tested setup. Measure the initial side effect independently of persistence and onward transfer. [Appendix C](https://arxiv.org/html/2608.10218v1#A3) |
| Figure 6 reports transfer and goal retention separately. In §4 and Appendix F, themes vary by generator and their removal has variable effects across experiments. | Grade actual writes, loads, and scoped behavior as separate outcomes. Use authority and effect as decision criteria. [Figure 6](https://arxiv.org/html/2608.10218v1#S3.SS2) · [§4](https://arxiv.org/html/2608.10218v1#S4) · [Appendix F](https://arxiv.org/html/2608.10218v1#A6) |

The paper includes more than one communication topology and discusses a hybrid installer case. Its modeled collaborations still leave questions about specialized roles, independent permissions, and host-specific load and recovery behavior. Treat these as evaluation dimensions for the target runtime. [§2.1, §3.3.2, and §6](https://arxiv.org/html/2608.10218v1)

## What this skill adds to the collection

| Primary source | Applicable result or principle |
| --- | --- |
| [Saltzer and Schroeder, The Protection of Information in Computer Systems](https://www.cs.virginia.edu/~evans/cs551/saltzer/) | Complete mediation and fail-safe defaults are established design principles. Apply them to consumption of effective instructions and capability changes. |
| [SLSA v1.2 artifact verification](https://slsa.dev/spec/v1.2/verifying-artifacts) | Verify the artifact against independently configured trust roots and expectations. A matching digest alone establishes identity of bytes. |
| [CaMeL](https://arxiv.org/abs/2503.18813v2) and [Can CaMeLs Talk?](https://arxiv.org/abs/2610.05640v1) | Separate trusted control from untrusted data and preserve provenance across delegation. Multi-CaMeL shows why independently protected agents can lose protection at the handoff. |
| [SkillGuard](https://arxiv.org/abs/2606.03024v2) | Skill permissions can govern both context influence and action side effects. The effective surface in this skill also includes platform instruction discovery and persisted state outside packages. |
| [AgentDojo](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) | Evaluate authorized task utility alongside independently observed security properties. Add the post-reload checks needed for persistent state. |

The proposed contribution is an operator workflow that connects loader discovery, authorization of a reviewed revision, activation, and fresh-session verification. It extends the repository's locked editable surfaces and deterministic-first evaluation patterns in two ways.

- **Reviewed instruction activation.** Compare the effective load set and capability changes, bind approval to the exact snapshot and scope, and verify the snapshot at use. Validate against changed inputs, stale approval, and scope changes.
- **Fresh-session boundary evaluation.** Independently observe what persists, what actually loads, what bounded behavior follows, and whether the legitimate task succeeds across restart, reload, or delegation.

These mechanisms are proposals for runtime-specific validation.
