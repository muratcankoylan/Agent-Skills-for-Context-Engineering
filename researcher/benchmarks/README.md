# Researcher Benchmark Inputs

`run_benchmarks.py` executes exactly two deterministic checks: repository
validation and activation-case validation. The seven
adversarial JSONL records are currently a closed scenario catalog with golden
gate mappings, not executable attack fixtures. Catalog consistency is useful
design evidence, but it must not be reported as proof that a gate resists the
described mutation. A future Stage-0 implementation must materialize each
mutation in an isolated fixture and invoke the named validator.

`--record` may append the check and catalog result to
`researcher/reports/benchmark-history.jsonl`. That file is gitignored runtime
state, not published evidence or a production health ledger. Each current
record reports `executed_scenarios: 0` and binds the tracked checkout identity;
status treats stale, dirty-checkout, malformed, or failing records as unhealthy.
