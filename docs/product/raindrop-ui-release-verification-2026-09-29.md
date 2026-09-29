# Raindrop UI verification and release handoff

Date: 29 September 2026. Scope: repository-owned Codex SDK research service,
operational observability, safe shutdown and a reviewable follow-on PR. This is
not a cloud activation, automatic merge or scientific-effectiveness result.

## What actually failed

The configured Production/default dashboard showed zero Events despite 246
previously acknowledged OTLP spans. The project selection and configured slug
agreed. Published Raindrop SDK source explains the distinction: the trace endpoint
can return HTTP 200 while discarding spans without recognized attributes; automatic
Event derivation from an outermost LLM span has additional content/finish-reason/user
requirements. Our generic metadata-only operations did not meet that contract.
The earlier acknowledgements remain historical transport observations, not usable
Events. [Pinned Raindrop SDK source](https://files.pythonhosted.org/packages/d5/cf/a76bb191b8448039ed23ac3a733a76a928e314b29e83dfd92e4e4f484553/raindrop_ai-0.0.69.tar.gz),
[OTLP documentation](https://www.raindrop.ai/docs/sdk/opentelemetry/).

The fix publishes plain operational Events for completed root spans and associates
every detailed span with that Event. No fake model content, finish reason or new
third-party instrumentation dependency is introduced. Input/output remains private
in the dossier. Closed tool labels come from the SDK's exact semantic conventions;
wrappers are not counted again as tools. [HTTP Events](https://www.raindrop.ai/docs/sdk/http-api/),
[semantic convention definitions](https://raw.githubusercontent.com/traceloop/openllmetry/main/packages/opentelemetry-semantic-conventions-ai/opentelemetry/semconv_ai/__init__.py).

## Delivery invariants

1. Validate both projections and require each trace's completed root in the batch
   or a prior successful local root-Event receipt, then durably claim the batch.
2. Send at most one Event request for completed roots present in that batch.
3. Persist its phase receipt before sending the associated OTLP spans.
4. Only both acknowledgements mark the batch exported. Unknown/partial/rejected
   results stay quarantined; restart does not resend or restart research.
5. Verify the Event and trace tree through authenticated UI or an independently
   configured Query key. Neither a 200 response nor an empty queue is readback.

The documentation specifies an empty 204. The current live endpoint returned 200
with `{"events":[{"event_id":"…"}]}`. A distinct bounded experiment confirmed
that the returned ID matched the newly submitted Event and the UI showed it.
The exporter now accepts that exact closed JSON contract with a complete unique
ID set, as well as empty 204. It refuses arbitrary 2xx/200 bodies, duplicate or
foreign IDs and malformed framing. The official SDK accepts successful HTTP statuses
via `raise_for_status()`, but our narrower contract does not adopt its retries or
redirect behavior. Initial uncertain canaries were not resent or rewritten.

No SQL schema change is needed. Existing v1 transport receipts stay readable;
new v2 composite receipts retain both phases. A process death between phases
retains the Event receipt in a running attempt. One due pump sends at most 100
spans through two isolated ten-second requests. The two-journal Organization
ceiling is four requests/forty transport seconds, not an unbounded flush loop.

## Actual live research and outputs

The independent query was **retrieval augmented generation evaluation**. The
current daily slot called arXiv, Hacker News and Hugging Face, then captured two
primary pages. It did not simulate elapsed production days or establish complete
coverage of those sources. The run used pinned SDK/CLI 0.159.0, the existing
`gpt-6-sol` policy, low reasoning and concurrency one.

| Observation | Result |
| --- | --- |
| Source effects | Five, including two primary captures |
| Actual paid SDK turns | Five completed, no new unresolved effect |
| Agent sequence | Four typed researcher decisions, then an independent critic |
| Research result | Abstained; no accepted skill, publication or model-judge win |
| End-to-end local cycle | 36.313 seconds, including post-cycle export |
| Dashboard | One real `organization.cycle` Event, 37 spans, displayed duration 35.3 s |
| Inspected SDK span | Researcher role, `codex_sdk` runtime, token counters and approximately 3.0 s duration |
| New model estimated upper cost | $0.235313, not invoice-verified |
| New retained reservation | $1.103801, not actual cost |
| Original cumulative authority | $100 cap; $8.819379 reserved; $91.180621 available |
| Historical unresolved calls | Three, unchanged and not retried |

The authenticated trace tree showed discovery, source verification, primary
reading, pipeline phases, agent actions and SDK turns. This is evidence of working
collection, association and UI rendering. It is not a retention/SLO guarantee or
proof that future exports cannot fail. A separate three-span fixture verified
the repaired delivery without model calls before the real cycle.

The critic's abstention is a valid product outcome: grounded observations alone
do not authorize a skill update. Held-out labels, paired baseline and candidate
evaluation remain independent requirements. Private receipts and the HTML dossier
retain the actual outputs; no prompts, paper text, secrets, paths or input digests
are copied into this public report.

### Second independent query on the final tool-label build

The second query, **agent memory evaluation**, performed five source effects,
including two primary captures, and five completed SDK turns. It finished in
49.553 seconds including export. Authenticated UI readback showed its own
`organization.cycle` Event, **37 spans and nine tools**, with a displayed root
duration of 48.5 seconds. The tree classified three discovery requests, two primary
reads and four typed agent actions as tools. The five SDK turns remained separate
spans. The earlier run is preserved as observed, before the final tool labels.

The researcher proposed transferring adoption-aware utility and bounded memory
consolidation from a kernel-synthesis paper. The critic distinguished the authors'
reported results from demonstrated transfer to semantic memory, identified missing
methods and baseline details in partial HTML, and used a separate self-update
safety paper as counterevidence. It abstained pending a held-out paired memory
experiment. No skill mutation or publication was accepted. This is a concrete
example of the research/critique boundary working, not an effectiveness benchmark.

The second run's estimated upper model cost was $0.254862 and its retained
reservation was $1.129096. Across both runs, ten SDK turns completed for an
estimated $0.490175. The original cumulative $100 authority now retains $9.948475
in reservations, leaving $90.051525 available. Its completed-call estimated upper
cost is $1.949148, not invoice-verified. All three historical unresolved calls
remain quarantined; these runs introduced none. Source identity was unchanged
during each run. A separate three-span fixture also verified the two-tool UI count
before the final real query.

## Additional release repairs

- Cooperative shutdown now stops before the next source effect, SDK turn or
  pipeline phase. Completed receipts replay; started unknown effects retain their
  reservation. The systemd reference unit uses `KillMode=mixed` so the first TERM
  reaches the coordinator rather than interrupting its in-flight SDK child. The
  600-second grace covers the bounded validation phase and telemetry deadlines,
  not arbitrary filesystem stalls. No unit was installed.
- The mandatory actual-SDK image gate includes captured-action and shutdown
  recovery cases, instead of allowing their absence to look like coverage.
- Combining the local service with the published stack exposed a legacy inode
  lock regression. The append path again holds both sidecar and ledger locks,
  samples rollback length after locking and preserves previously committed data.
  Published contention tests are retained alongside the stricter hardlink refusal.
- A default-limit restart test exposed another real delivery gap: a rejected root
  Event claimed the first 100 spans, then a restarted pump sent the remaining
  child-only batch without a confirmed Event. The new pre-claim root gate leaves
  those children pending and sends nothing. Successful root-Event receipts still
  permit ordinary later batches, including when the original OTLP phase was
  uncertain. Historical OTLP-only receipts grant no Event authority. The profile
  assumes the same verified Raindrop account/project across batches; changing the
  target of a populated journal remains unsupported.

The final root-gate repair also passed a live, explicitly synthetic batch canary:
one Event with 102 spans, delivered as 100 then two spans by a fresh exporter
instance. The authenticated UI showed all 102 spans and 101 fixture tools. The
second batch created no duplicate Event, and a subsequent export made no request.
No model or retrieval call was made for this canary. This proves that the new
prerequisite preserves the healthy cross-batch path, separately from the offline
rejected/unknown-root fault tests.

Executed targeted checks: 157 trace-contract tests, 13 actual-SDK shutdown tests
with synthetic providers and zero skips, 37 deployment tests, 97 legacy-loop tests,
and 119 inventory tests. These suites overlap other repository checks and are not
an additive effectiveness score. Earlier test failures and the initial mismatched
acknowledgement remain retained as failures, not silently discarded.

### Final combined-checkout verification

| Check | Executed result |
| --- | --- |
| Full service suite with the actual pinned SDK and synthetic loopback providers | 1,235 tests, zero failures/errors/skips; 297.039 seconds |
| Full repository scripts suite | 1,247 tests, zero failures/errors/skips; 190.063 seconds |
| Deployment-profile suite | 37 tests passed, zero skips |
| TypeScript schema contracts | Typecheck and 25 tests passed |
| Benchmark runner contracts | Typecheck and 82 tests passed; import-denying dry runs made no paid calls |
| Control Center | 54 tests, typecheck, production build and standalone HTTP smoke passed; nine static assets verified |
| Node production dependency audits | Zero reported vulnerabilities in the three checked packages |
| Structural release gates | Inventory, reference platform, strict repository, skill health, activation, benchmark catalog, governance, schemas and exact-parent lifecycle all passed |
| Focused Python static analysis | All checked tracing, shutdown and related test files passed Ruff |

Both complete Python suites retained identical before/after source identities.
The final metadata append records these observations; it does not retroactively
change the tested executable files. Hosted checks on the published PR head remain
separate evidence. The benchmark catalog check is three checks over seven entries,
not seven executed research scenarios or a model-quality result.

The first hosted transport-conformance job failed during module import, before
executing transport cases: its older workflow installed no dependencies, while
the integrated tracing layer imports the existing JSON Schema contract. Python
3.12 reported missing `jsonschema`; the 3.11 matrix leg was cancelled. The
append-only CI repair installs the existing hash-locked requirements and checks
their consistency, without changing package versions or runtime behavior. Two
workflow regressions cover installation order and dependency-change triggers.
This hosted failure is distinct from the passing local suites above; the repaired
hosted result must be observed on the new head before claiming hosted success.

The first full service pass exposed outdated single-request telemetry mocks and a
generic stop mock. Their replacements assert Event-before-OTLP order, known root
IDs and a real stop event. The first scripts invocation used a temporary wrapper
without a multiprocessing main guard; it reentered and corrupted its own log.
That invocation is retained as invalid verification, not a product race. A later
run was explicitly interrupted because repository-copy fixtures were copying
572 MB of generated Node artifacts. The artifacts were moved recoverably outside
the checkout, preserving source identity, and the complete Python-first reruns
above passed. No test timeout or product-state assertion was relaxed.

The candidate removes two obsolete ambient-credential/live judge test files,
replaced by injected bounded-runtime tests, and one committed runtime-history
file. All three remain recoverable from the unchanged parent Git history. The
44 published base-only files absent from the older integration tree are retained.

## Review and deployment sequence

Only Muratcan-authored project PRs are in this release. The existing chain is:

```text
main -> #121 -> #122 -> #123 -> #124 -> #125 -> #126 -> #127 -> #128
     -> #129 -> #130 -> #131 -> #134 -> #135 -> #136 -> #137 -> #138
     -> #132 -> #139
```

The SDK/service follow-on is published as draft [#139](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/139)
above the exact #132 tip, retaining published files absent from the older integration
worktree. It does not rewrite the 17 existing heads. Generated inventory is
reconciled on the combined tree. Review the stack from bottom to top and run
Cursor Bugbot on #139; no Bugbot run, merge or cloud deployment is authorized by
this report. Draft publication is not production activation.

The deployment target is the repository's persistent Linux coordinator profile,
using API credentials and the pinned SDK independently of Codex desktop. GitHub
hosts the reviewed source, validation and PR workflow. An ephemeral GitHub Actions
filesystem is not cumulative budget authority. Preserve the reviewed release SHA,
dedicated identity, private persistent state, literal credential files and launch
attestation described in the [deployment runbook](../../researcher/service/DEPLOYMENT.md).

Before activation, rotate the write key previously exposed in chat, install the
reviewed artifact on the selected host, complete its exact-host canary and verify
required checks/review protections. The inspected GitHub rules do not currently
enforce a successful status check or an approving review; a green run alone does
not enforce the merge boundary. Changing those security settings remains an
explicit owner decision. The ingestion key does not grant Query API/MCP readback.
Metadata-only traces do not supply raw-content issue detection or vendor model-cost
attribution. Those limits are deliberate and visible, not production features
claimed from successful HTTP calls.
