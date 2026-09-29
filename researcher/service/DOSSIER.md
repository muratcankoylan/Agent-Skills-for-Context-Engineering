# Inspect actual research outputs

`dossier.py` is a read-only private operator projection. It requires terminal
pipeline records, checks their local digest linkage, and reads existing trace
journals without initializing, repairing or exporting them. It makes no model,
provider or publication calls. It is not semantic validation or historical replay.

```sh
python -m researcher.service.dossier \
  --pipeline /private/organization/jobs/JOB_HASH/pipeline \
  --trace-state /private/existing-openai-authority --format html
```

The command prints HTML; JSON is the default. Supply multiple `--pipeline` and
`--trace-state` arguments for a multi-day view. The output contains full retained
research/critic/editor results, selected evidence packet, candidate freeze and
evaluation results where present, learning omissions, operation latency, trace IDs
and export receipts. It intentionally escapes all source/model text, includes no
scripts/remote assets, and treats the entire result as private. Boundaries are
64 pipelines, eight journals, and 24 MiB of retained data; excess fails, not truncates.

For `captured-actions-v1` studies, the dossier includes the bound
`research-actions.json` transcript: selected functions, exact revealed spans,
specialist question/advice and terminal decision. It deterministically rederives
the tool projections and checks packet/state/research linkage, without executing
SDK calls. Receipt references in this view remain explicitly **not origin-verified**;
the actual pipeline's Campaign replay establishes model origin. Missing or changed
action checkpoints are errors once the state records a completed action loop,
not silently omitted history. A loop that fails before final grounding has no
complete transcript: the failed pipeline's action record is absent, while earlier
completed decisions remain in per-turn Campaign checkpoints and metadata traces.
This view does not yet aggregate that partial decision history.

Phase identity consistency does not establish that mutable local artifacts were
independently re-executed. Use pipeline replay for that stronger check. An export
receipt is not authenticated Raindrop dashboard readback. To explicitly export
registered metadata, follow [TRACING.md](TRACING.md). Raw dossier contents are not
automatically uploaded to Raindrop or added to a public PR.
