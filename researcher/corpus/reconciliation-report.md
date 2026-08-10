# SPEC-001 reconciliation report

- Baseline commit: `a1841d1`
- Reconciliation date: 2026-08-10
- Generated schema: `1.0.0`

## Resolved discrepancies

| Surface | Prior condition | Resolution |
| --- | --- | --- |
| Live corpus prose | README and AGENTS copied older mechanism, claim, and activation totals | Replaced copied totals with links to the generated live summary |
| CLAUDE repository map | Example and skill totals were hand-maintained | Replaced live totals with generated-inventory ownership |
| Benchmark methodology | Current `full` condition said 15 skills | Changed to all currently published skills; dated result reports were preserved |
| Mechanism ledger completeness | Eleven accepted registry mechanisms had no accepted-ledger event | Appended explicit `historical_state_reconciliation` events tied to source commit `cbc2c978...` and public skill files |
| Self-improvement provenance | Three legacy events pointed to an intentionally uncommitted runtime run | Appended corrections tied to source commit `11513d21...`; legacy events remain intact |
| Long-horizon provenance | Three legacy events had no source pointer | Appended corrections tied to source commit `52101282...`; semantic decisions are unchanged |
| Claim relationships | Corpus index mixed owning and related claim use | Preserved the curated index and projected each relationship as `owned` or `related` in the inventory |
| Effectiveness status | Task presence could be confused with runner readiness | Inventory records task count and runner state separately; the runner remains `scaffold` |

## Preserved historical material

`CHANGELOG.md`, published router reports, `researcher/insights/`, and other dated narratives keep their original counts and measurements. They are evidence about a past repository state, not live dashboards.

## Current reconciliation result

The generated inventory contains zero unresolved references. All published skills are present in the marketplace declaration and curated corpus index. Every mechanism and claim is represented in corpus relationships. Every accepted mechanism has a durable public ledger provenance path. Adversarial scenarios and goldens are one-to-one, and the effectiveness task passes structural validation.

The machine-readable evidence is `researcher/corpus/inventory.json`; current totals are rendered in `researcher/generated/corpus-summary.md`.
