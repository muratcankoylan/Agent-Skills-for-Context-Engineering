# Private offline service recovery

This runbook applies to the single-host `researcher/service/` preview. It does
not activate the service, reconcile remote effects, approve research, or provide
a production disaster-recovery guarantee. It replaces neither provider-side
reconciliation nor a tested encrypted off-host backup policy.

## What is retained

`python -m researcher.service.recovery_bundle` creates a closed directory bundle,
not a tar archive. `manifest.json` binds each relative path, exact-byte SHA-256,
byte count, source implementation/dependency identity, Git baseline, configuration
digest, job manifests and explicitly selected managed-session manifests. Blob
filenames are hashes; manifest paths are validated against the known service
namespace before materialization.

The closure includes:

- A consistent SQLite backup containing jobs, checkpoints, effects, source slots,
  reservations, clock state and events. WAL/SHM files are never copied as data.
- Exact source and primary-HTML bodies and observation metadata, including retained
  captures from unsuccessful attempts. Referenced captures must exist and match.
- Candidate draft skill files, content-addressed candidate bodies, classification
  metadata and freeze receipts. Referenced frozen content must exist and match.
- Only explicitly named managed ledgers: `packet.json`, `session.json`, and an
  existing `result.json`. Their local submission phases and result bindings survive.
  A managed retrieval packet must reference a job and report in the same bundle.

A separate `openai-budget-authority/v1` Store is also supported through a narrower
registered closure: its SQLite database and validated `authority.json` only.
Snapshot it separately from retrieval state, supplying that `authority.json` as
`--config`, with no `--session` options. Restore retains the cumulative cap, prior
spend, every completed/unknown reservation and its exact authority configuration,
and pauses that Store too. It cannot top up or reset the authority. Never continue
both the original and restored budget authority; that would duplicate spending
authority even when each individual database is internally consistent.

The tool rejects unexpected files instead of recursively copying arbitrary private
directories. In particular, `.env*`, keys, Git directories, logs, unrelated files
and unregistered ledger types are not included. Do not put credentials inside the
state directory. Runtime locks are not portable state; required capture locks are
recreated empty. The exact matching operator configuration must be retained
separately and supplied at restore, not reconstructed from an example config.

No secret scanner can prove that a query, source body or model response contains
no sensitive content. The whole bundle is private operational data, even though
credential files are excluded. It is **not encrypted by this tool**. Use an
encrypted private volume and separately reviewed encrypted off-host transport.
Never commit a bundle, expose it through the UI, or attach it to a public issue.

## Preconditions

1. Stop the scheduler/API admission path and worker. Stop every other writer using
   these state/artifact paths. The tool additionally takes nonblocking worker,
   managed-session and capture locks; lock contention fails rather than waiting
   behind an active remote operation.
2. Inventory every managed ledger explicitly. A session omitted from `--session`
   is not backed up. A local lock does not stop an already-running remote session.
3. Use absolute paths with no symlink components. State and output parents must
   be owned private `0700` directories. Files must be owned, regular, single-link
   `0600` files. Candidate intermediate directories already enclosed by the
   private state root may be owner-controlled `0755`; restored directories are
   uniformly `0700`. Unsafe ownership, writable ancestors, FIFOs, symlinks and
   hardlinks fail closed.
4. Retain the exact source checkout, runtime dependencies and operator config.
   Source/config drift requires a separately reviewed migration, not a restore
   override. This command does not check out Git revisions or install packages.

## Snapshot

Create the private backup parent through your normal operator provisioning. The
destination below must not exist. Replace the example absolute paths with actual
operator-managed paths; no command reads an environment file.

```sh
python -m researcher.service.recovery_bundle snapshot \
  --root /srv/context-research/repo \
  --config /srv/context-research/operator/config.json \
  --state /srv/context-research/private/state \
  --session research-20260929=/srv/context-research/private/managed-20260929 \
  --destination /srv/context-research/backups/snapshot-20260929
```

Omit `--session` only when there are no managed ledgers in scope. Repeat it for
each explicitly selected ledger. Keep the returned `manifest_digest` in a trusted
record separate from the bundle. Restore requires that pinned digest, so replacing
both a blob and its manifest cannot silently pass the operator's integrity check.
This is integrity pinning, not digital signing or attestation against a compromised
host that can rewrite the trusted record too.

The default hard bounds are 10,000 payload files, 256 MiB total payload, 64 MiB per
file, 8 MiB manifest, 32 managed ledgers, and a 30-second SQLite-backup deadline.
The Python API permits lower file/byte ceilings, not increases above these bounds.
Directory enumeration is bounded, including ignored lock files. There is no
compression, arbitrary archive extraction, pagination or network operation.

Files are private, atomically written and fsynced. `manifest.json` is written
last and marks a complete snapshot. An interrupted/failed snapshot can leave a
private incomplete directory; it is never accepted as a complete bundle. The tool
does not overwrite, resume into or automatically delete that directory. Inspect
and remove it through the operator's normal recoverable cleanup procedure, or
choose a fresh destination.

## Isolated restore and drill

Fence the original writer before using a restored copy. The destination must be
new; restore never replaces a live Store.

```sh
python -m researcher.service.recovery_bundle restore \
  --root /srv/context-research/repo \
  --config /srv/context-research/operator/config.json \
  --bundle /srv/context-research/backups/snapshot-20260929 \
  --manifest-digest sha256:REPLACE_WITH_THE_SEPARATELY_RETAINED_DIGEST \
  --destination /srv/context-research/drills/restore-20260929
```

The restored layout is `state/`, optional `sessions/<name>/`, and `restore.json`.
All hashes, SQLite schema/checkpoint/effect digests, capture/CAS closure and managed
ledger bindings are verified before creating the destination. The SQLite image is
modified in memory only to set `paused=true`, then written atomically. No worker,
scheduler, API server, provider client or GitHub operation is started. No credentials
are read. The receipt records both the original and paused database hashes.

A failure while writing can leave an incomplete private destination. It is not a
successful restore without `restore.json`; do not point any service at it. Retry
only into a new destination. Every materialized database is already paused,
including one left by an interrupted restore.

Verify locally before considering any operational change:

- Open the restored Store with the matching config and confirm `paused=true`.
  Compare job states, effect rows and cumulative reservations with the snapshot.
- Replay retained discovery/primary captures using the read-only replay paths.
  A replay proves the recorded observation, not paper quality or current freshness.
- Materialize retained frozen candidate receipts under the existing read capability.
  This does not accept or publish the candidate.
- Load restored managed ledgers. A `submitting`, `running`, or
  `reconciliation_required` phase is not a new submission opportunity or proof that
  the provider stopped. Do not submit again to test recovery.

The deterministic regression drill is:

```sh
python -m unittest researcher.service.tests.test_recovery_bundle -b -q
```

It uses synthetic transports and fake model clients, with external socket connects
blocked. It covers captured retrieval replay without changed evidence files,
candidate materialization, unknown-effect reservation retention, managed create
intent/result retention, no duplicate effects after explicit fixture-only resume,
config/source mismatch, corruption, missing dependencies, traversal, symlinks,
hardlinks, ownership, FIFOs, size/count limits and lock contention. Passing these
tests is not an RPO/RTO measurement, cloud failover drill or provider canary.

## Authority and uncertainty after restore

The original effect rows and managed phases are preserved. Restore does not call
`recover`, clear uncertainty, refund reservations, retry an effect, or reset a
budget. A later explicitly authorized worker restart applies the existing
recovery rules: started effects become unknown, completed effects replay, and
unknown remote creates are never repeated automatically.

A snapshot cannot contain effects started **after** its consistency point. If the
original service continued after backup, unpausing an older copy could repeat those
unrecorded effects. Fencing the original writer and reconciling the entire
post-snapshot interval are mandatory before any live resumption. This module has
no force-unpause, provider reconciliation or automated promotion command.

Unresolved release gates remain encrypted off-host storage/key rotation, measured
restore time and loss window at representative scale, remote reconciliation,
original-writer fencing in the deployment environment, and a multi-day soak.
