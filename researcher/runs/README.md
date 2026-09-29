# Researcher Runs

Each run is one trip through the local research-to-skill state machine. Run
directories are ignored runtime artifacts; only the seed run is committed as a
worked example. A legacy run is supervised evidence, not an acceptance or
production authority record.

## Layout

```
researcher/runs/<timestamp>-<slug>/
  run-state.json              # state machine, locked surfaces, transition history
  THREAD.md                   # human-readable thread log
  sources/
    queue.jsonl               # source records for this run
    evaluations/              # source-evaluation JSON (drafts allowed, completed required for publish)
    evidence/
      retrieval.md            # pointer log of retrieved evidence
      raw/                    # raw fetched HTML/JSON
  proposals/
    skill-proposal.md         # proposal targeting a specific skill change
    mechanism-proposal.jsonl  # candidate mechanisms for the registry
  reports/
    validation-report.json    # repo-level validation snapshot at init time
    validation-report.md      # human summary
    novelty-result.json       # latest novelty check (created by `research_loop.py novelty`)
    pr-readiness.md           # PR summary, test plan, risks (created by `pr-ready`)
    closure.json              # set by `close`
    run-readiness.{json,md}   # set by `validate-run`
  logs/
```

## State machine

```
initialized -> retrieved -> evaluated -> proposed -> novelty_checked -> validated -> pr_ready -> closed
```

Use `researcher/scripts/research_loop.py` subcommands rather than editing `run-state.json` directly:

```bash
python3 researcher/scripts/loop_status.py --initialize-runtime
python3 researcher/scripts/research_loop.py init --title "..." --url "..."
python3 researcher/scripts/research_loop.py retrieve --run-dir <run> --file <evidence>
python3 researcher/scripts/research_loop.py evaluate --run-dir <run>
python3 researcher/scripts/research_loop.py propose --run-dir <run>
python3 researcher/scripts/research_loop.py novelty --run-dir <run>
python3 researcher/scripts/research_loop.py validate-run --run-dir <run>
python3 researcher/scripts/research_loop.py pr-ready --run-dir <run> --summary <text> --test-plan <text> --risks <text>
python3 researcher/scripts/research_loop.py close --run-dir <run> --status reference-only --reason <text> --reviewed-by <handle>
```

The first command explicitly creates any missing empty queue ledgers and
validates the complete set. It does not repair existing malformed files.
Evidence must be acquired through a reviewed process outside the legacy tools;
`retrieve --file` only records a bounded local file and performs no network
request. Writable close statuses are `rejected`, `reference-only`, and
`abandoned`. `accepted` closure and mechanism promotion are disabled.

## What is committed

Only `researcher/runs/20260515-035228-executable-autonomous-research-frameworks/` is committed. It is the worked example that bootstrapped the harness-engineering skill and the mechanism registry. Its `current_state` is `closed` and `close_status` is `reference-only`.

All other run directories are local runtime state and are excluded by `.gitignore`. PRs should not introduce new committed runs; if you need a regression fixture, add it under `researcher/fixtures/` instead.
