# ADR-0009: Amend SPEC-001 for exact repository snapshot identity

- Status: accepted
- Date: 2026-08-15
- Spec: SPEC-001
- Lifecycle transition: SPEC-001@1 -> amended -> SPEC-001@2

## Context

SPEC-001 revision 1 established the canonical repository inventory, deterministic source-tree digest, generated corpus summary, closed reference checks, and atomic regeneration. Its `source_tree_digest` intentionally excludes the generated inventory and summary so those outputs do not hash themselves.

That digest is an identity for the canonical source set, not an identity for a Git repository snapshot. Later control-plane contracts must bootstrap repository acceptance from one exact protected commit and tree while proving that the checked inventory was generated from those same bytes. A Git commit alone does not prove the inventory relation, and a source-tree digest alone does not identify the Git object format, commit, tree, or repository history boundary. Treating either value as both identities would let independent implementations accept different repository states under the same claimed bootstrap evidence.

SPEC-000 revision 1 is also entering its amendment lifecycle. SPEC-001 revision 1 is frozen to `SPEC-000@1`; it cannot advance against the replacement constitution without its own revision and exact dependency binding.

## Decision

SPEC-001 revision 1 enters the terminal `amended` state and names `SPEC-001@2` as its only replacement. Revision 2 must preserve the checked derived-view architecture while defining a non-self-referential repository snapshot evidence contract that:

- keeps canonical-source-tree identity distinct from Git repository identity;
- binds the Git object format, exact commit object, exact tree object, exact inventory bytes, inventory schema and builder versions, and the inventory's declared `source_tree_digest`;
- verifies that every registered canonical source byte is the byte reachable from the bound tree and that generated files do not become inputs to their own digest;
- rejects dirty, untracked, sparse, submodule, symlink, index-flag, ancestry-rewrite, or mixed-snapshot ambiguity unless a later accepted contract explicitly defines the case;
- remains deterministic across repository locations and process restarts; and
- grants no repository acceptance, merge, deployment, or runtime authority merely because snapshot evidence validates.

The replacement must bind the current accepted constitution revision through the ordinary dependency-revision lifecycle. Repository acceptance and accepted-public-commit transitions remain owned by their later specifications and human authority boundaries.

This decision authorizes only the lifecycle transition. It does not accept revision 2, define its final schema, change inventory bytes, bootstrap repository acceptance, or authorize implementation.

## Consequences

- Existing revision-1 inventory and summary artifacts remain valid as deterministic derived views; they are not retroactively reinterpreted as Git acceptance receipts.
- Downstream journal, work-order, command, and reconciliation contracts may consume exact repository snapshot evidence only after revision 2 is accepted and implemented.
- The successor implementation must include clean-tree and adversarial repository-state fixtures, deterministic regeneration, rollback, and validation that snapshot evidence cannot become an authority token.
- SPEC-001 must be revised before it can advance against `SPEC-000@2` or satisfy later same-stage dependency floors.

## Alternatives considered

- Use `git rev-parse HEAD` as the inventory identity. Rejected because ambient HEAD can differ from the reviewed tree and does not prove inventory derivation.
- Treat `source_tree_digest` as a Git commit identity. Rejected because it intentionally covers a different byte set and excludes generated outputs to avoid self-reference.
- Add an implementation-only receipt without revising SPEC-001. Rejected because independent conforming implementations would still lack one normative identity relation.

## Verification

The transition PR must change only lifecycle metadata in SPEC-001, add this one-purpose accepted ADR, update its index, move the active dependency-binding inventory fixture to another active specification, regenerate deterministic inventory outputs, and pass the base-aware lifecycle validator against the exact parent branch. The successor and implementation PRs must separately provide the contract, fixtures, migration, rollback, and authority-separation evidence described above.
