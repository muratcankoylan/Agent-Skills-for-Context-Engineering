# Architecture decision records

These records capture durable implementation choices for the autonomous research organization. They explain trade-offs and consequences; executable policy, schemas, tests, and merged Git history remain authoritative.

Decision records are append-only in number. A later decision supersedes an earlier one explicitly rather than rewriting why the earlier choice was made.

An ADR's recorded status is authoritative only when that exact file is reachable from the protected default branch. Copies on proposal branches carry no decision authority; human merge is the acceptance event.

The dependency-ordered implementation contracts live in the [specification program](../specs/README.md).

## Records

- [ADR-0001: Machine-testable, deny-by-default authority](0001-machine-testable-constitution.md)
- [ADR-0002: Treat the corpus inventory as a checked derived view](0002-derived-corpus-inventory.md)
- [ADR-0003: Publish allowlisted projections, not redacted private records](0003-allowlisted-public-projections.md)
- [ADR-0004: Make schemas, identity, and frozen bytes runtime-neutral](0004-runtime-neutral-artifact-contracts.md)
- [ADR-0005: Publish one machine-checked specification program](0005-canonical-specification-program.md)
- [ADR-0006: Validate the complete public release boundary](0006-validate-public-release-boundary.md)
