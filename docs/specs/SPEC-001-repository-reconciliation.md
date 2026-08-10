# SPEC-001: Repository reconciliation and generated corpus inventory

- Status: implementing
- Wave: 0
- Classification: public
- Depends on: SPEC-000

## Decision

All live counts, compatibility metadata, and cross-artifact references are derived from canonical repository files. Hand-authored documents may explain the corpus but are not a second count authority. `researcher/corpus/inventory.json` is a checked derived view bound to canonical input bytes.

## Invariants

1. Generated output is deterministic and byte-identical when canonical inputs do not change.
2. The generated inventory and summary never affect their own source-tree digest.
3. A skill change is incomplete when its published file, manifest entry, corpus relationship, mechanism, claim, fixture, or validator ownership disagrees.
4. Runtime queues, active runs, ignored reports, and unpublished paid results are excluded.
5. Historical reports retain original dated claims and are not rewritten as live status.
6. Parse failure or unresolved reference prevents replacement of the last valid generated view.

## Interfaces

- `build_inventory.py --check`: rebuild in memory, reject findings or committed drift.
- `build_inventory.py --write`: refuse unresolved findings, then atomically replace the inventory and summary.
- `build_inventory.py --json`: print the deterministic view without writing.
- `researcher/corpus/inventory.schema.json`: bootstrap public schema.
- `researcher/generated/corpus-summary.md`: human-readable live totals and compatibility status.

Stable reason codes distinguish duplicate identifier domains, dangling references, owner mismatches, missing ledger events, missing or mismatched goldens, invalid effectiveness tasks, manifest/version disagreement, path escape, and generated drift.

## Ownership boundary

- Inventory: uniqueness, completeness, digests, references, live totals, generated drift.
- Platform validator: Agent Skills syntax and install compatibility.
- Repository validator: content schemas, rubric math, source evaluations, committed run fixtures.
- Skill health: body-quality scoring.
- Activation checker: deterministic boundary smoke tests.
- Benchmark runner: scenario execution and gate composition.

## Acceptance criteria

- [x] Every current corpus category has a named owner and deterministic record set.
- [x] No unresolved, duplicate, or dangling identifier remains.
- [x] Accepted mechanism state has append-only public provenance.
- [x] Live documents link to generated totals; historical snapshots remain unchanged.
- [x] CI checks the generated inventory before existing strict validators.
- [x] Router fixtures, adversarial scenario/golden parity, and effectiveness task structure are validated.
- [x] Atomic interruption, symlink escape, duplicate keys, and mutation reason codes are tested.

The inventory does not claim Stage 3 effectiveness execution is operational. It records one available task and a scaffolded runner as separate facts.
