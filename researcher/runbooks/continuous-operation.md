# Supervised Legacy Loop Runbook

This runbook describes the repository's legacy file-based loop for supervised,
local testing. It is not a production activation procedure. The loop predates
the specification-owned journal, work-order, identity, capability, deployment,
and recovery contracts. Those contracts are not an operational runtime. Keep
the launchd jobs uninstalled unless a future SPEC-025 activation epoch is
human-approved over implemented dependencies.

## What Can Be Run Manually

| Command | Scheduling | Purpose |
| --- | --- | --- |
| `loop_step.py` | manual only | reap closed runs and park active runs that need an explicit operator action; it never initializes a run or advances evidence-bearing state |
| `loop_discover.py` | manual only | append normalized entries from the reviewed manual seed to the logically append-only candidate catalog |
| `loop_daily.py` | manual only | run a reduced gate and scenario-catalog profile, write a dated snapshot, flag volatile claims due for review |
| `loop_status.py` | manual only | fail closed over queue/run integrity, then refresh the dashboard and parked review surface |

No scheduler is active. The checked-in configuration contains only admission and
health bounds that the manual commands actually consume:

- max parked: 12
- max inbox size: 200
- max manual-seed additions per discovery invocation: 8

`loop_step.py` stops its bookkeeping path when the parked bound is full.
`loop_discover.py` enforces the inbox capacity and per-invocation addition
limit. There is no active daily-run, failure, retry, or automatic quarantine
budget.

## Activation Is Disabled

`researcher/orchestration/launchd/install.sh` fails closed. Do not copy or
bootstrap the checked-in plists manually. They remain migration evidence for a
future SPEC-025 adapter, not an authorized service definition.

## Uninstall

```bash
researcher/orchestration/launchd/uninstall.sh
```

## Manual Operation

You can run the loop scripts directly without launchd:

```bash
python3 researcher/scripts/loop_status.py --initialize-runtime  # explicit one-time runtime ledger creation
python3 researcher/scripts/loop_discover.py            # copy reviewed manual-seed entries into the catalog
python3 researcher/scripts/research_loop.py init \
  --title "..." --url "https://..."                     # explicit run creation
python3 researcher/scripts/loop_step.py                # bookkeeping or park one existing run
python3 researcher/scripts/loop_daily.py               # reduced health profile + snapshot
python3 researcher/scripts/loop_status.py              # refresh dashboard
```

The initialization command creates only missing empty ledgers and validates all
four. It does not repair existing bytes. Run it before `loop_discover.py`,
`loop_step.py`, `loop_daily.py`, or ordinary status projection. Per-run
`research_loop.py` commands validate managed run state independently and do not
require the global queue ledgers.

Network retrieval is absent from the legacy loop. Acquire evidence through a
reviewed, bounded operator process outside these commands and record a local
file with
`research_loop.py retrieve --file ...`. The future SPEC-009/SPEC-010 path must
prove connector allowlists, SSRF and redirect confinement, immutable capture,
integrity, and resource limits before unattended retrieval can be enabled.

## Human Review Surface

Read these files when checking on the loop:

- `researcher/reports/status.md` - high-level dashboard.
- `researcher/reports/parked-review.md` - runs waiting for a reviewer.
- `researcher/reports/snapshots/<date>.md` - daily snapshot.
- `researcher/reports/benchmark-history.jsonl` - ignored runtime history written only when recording is requested. Each record binds the tracked checkout and contains two executed deterministic checks, catalog consistency, and zero executed scenarios.
- `researcher/queue/inbox.jsonl` - candidate discovery catalog; it is not an executable work queue.
- `researcher/queue/quarantine.jsonl` - legacy/manual quarantine records; no automatic quarantine path is active.

Parked runs require one of these actions:

| Reason | Action |
| --- | --- |
| `needs source retrieval` | retrieve manually and run `research_loop.py retrieve --run-dir <run> --file <evidence>` |
| `needs evaluation` | complete the source evaluation JSON and run `research_loop.py evaluate --run-dir <run>` |
| `needs human or model action from state proposed` | finish the proposal and run `research_loop.py novelty --run-dir <run>` |
| `needs merge approval` | review the PR notes; merge only after explicit approval |

Close a legacy run only as `rejected`, `reference-only`, or `abandoned`.
`accepted` is deliberately unavailable because the legacy run lacks the
specification-owned freeze and authority pipeline.

## Current Safety Boundary

- The loop never invokes LLMs or paid APIs.
- The legacy commands perform no network retrieval.
- Inbox entries are never consumed or quarantined automatically; a human creates
  a run explicitly and curates the catalog record.
- `research_loop.py promote-mechanisms` always fails closed. Run-local mechanism
  proposals do not modify the registry or its historical ledgers.
- Push and merge are always human-controlled.
- `loop_daily.py` is a reduced local health profile, not a substitute for the
  pinned CI gate manifest or a deployment health check.

## Daily Rhythm

A reasonable cadence for a human running this:

1. Morning: read the latest snapshot and parked review.
2. Pick up to three parked runs and either advance, reject, or abandon them.
3. Treat any mechanism proposal as advisory input to a separate reviewed repository change; the legacy command cannot promote it.
4. Run the reduced daily check or status projection again after changes. Nothing
   remains scheduled in the background.
