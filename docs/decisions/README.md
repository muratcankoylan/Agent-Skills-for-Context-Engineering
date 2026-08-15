# Architecture decision records

These records capture durable implementation choices for the autonomous research organization. They explain trade-offs and consequences; executable policy, schemas, tests, and merged Git history remain authoritative.

Decision records are append-only in strictly increasing number. Once accepted, an ADR is byte-immutable. A later accepted decision may point backward to one lower-numbered decision with explicit `Supersedes: ADR-NNNN` metadata rather than rewriting the earlier status, scope, or rationale. One accepted ADR may have at most one accepted direct successor; a further change supersedes that successor. Generated views derive the acyclic supersession chain.

An ADR's recorded status is authoritative only when that exact file is reachable from the protected default branch. Copies on proposal branches carry no decision authority; human merge is the acceptance event.

A specification terminal decision is one-purpose and revision-bound. Its ADR metadata uses `Lifecycle transition: SPEC-NNN@revision -> amended|superseded|retired -> SPEC-NNN@next-revision|none`. The replacement must be the next revision of the same specification, or `none` for retirement. A broad program ADR or a decision for another revision cannot authorize the transition.

The dependency-ordered implementation contracts live in the [specification program](../specs/README.md).

## Records

- [ADR-0001: Machine-testable, deny-by-default authority](0001-machine-testable-constitution.md)
- [ADR-0002: Treat the corpus inventory as a checked derived view](0002-derived-corpus-inventory.md)
- [ADR-0003: Publish allowlisted projections, not redacted private records](0003-allowlisted-public-projections.md)
- [ADR-0004: Make schemas, identity, and frozen bytes runtime-neutral](0004-runtime-neutral-artifact-contracts.md)
- [ADR-0005: Publish one machine-checked specification program](0005-canonical-specification-program.md)
- [ADR-0006: Validate the complete public release boundary](0006-validate-public-release-boundary.md)
