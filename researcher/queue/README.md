# Researcher Queue

These runtime files support the supervised legacy tools. They are not a
production queue, scheduler, or loss-proof ledger. The inbox, parked, and done
files are atomically replaced snapshots; event-style histories are append-only.
Routine health fails when an expected queue file is missing, malformed, or
inconsistent with run state.

Create the four empty runtime ledgers explicitly before using a queue
supervisor (`loop_discover.py`, `loop_step.py`, `loop_daily.py`, or
`loop_status.py`):

```bash
python3 researcher/scripts/loop_status.py --initialize-runtime
```

This command creates only missing files and then validates the full set. It does
not replace, truncate, or repair an existing malformed ledger. All four JSONL
files are gitignored runtime state.

Per-run `research_loop.py` commands validate their managed run state directly;
they do not consume these global ledgers as an authority.

## Files

- `inbox.jsonl` - logically append-only candidate discovery catalog. It is not consumed as
  an executable work queue; runs are created explicitly by an operator.
- `parked.jsonl` - run IDs that hit a human-review gate and are waiting for a reviewer.
- `done.jsonl` - run IDs reaped after legacy closure. New writable closure
  statuses are `rejected`, `reference-only`, and `abandoned`; `accepted` is not
  supported by the legacy workflow.
- `quarantine.jsonl` - explicit legacy/manual quarantine records. No automatic
  retrieval-failure quarantine path is active.

## Source Record Shape

Each line in `inbox.jsonl` and `quarantine.jsonl` is a JSON object:

```json
{
  "source_id": "deterministic-hash",
  "url": "https://example.com/post",
  "url_normalized": "https://example.com/post",
  "title": "Short title",
  "author_or_org": "Org",
  "source_type": "paper | engineering_blog | documentation | benchmark | code | talk | other",
  "candidate_reason": "Why this source matters",
  "feed": "manual-seed",
  "discovered_at": "ISO-8601",
  "attempts": 0,
  "last_status": "queued"
}
```

A quarantine record uses the same source identity fields, sets `last_status` to
`quarantined`, and adds non-empty `quarantined_at` and `quarantine_reason`
fields. No command automatically retries a source or moves it to quarantine.

Active runs live under `researcher/runs/<run-id>/` and have their own `run-state.json`. The loop scripts read those state files directly rather than duplicating active-run state here, so there is one source of truth per run.
