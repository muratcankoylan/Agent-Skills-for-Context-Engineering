# Pinned Codex runtime prerequisite

This is an explicit, credential-free diagnostic, not an installer, paid run,
host-containment proof, or production approval. It does not start a thread/turn,
list models, accept commands, load credentials, or enable a service. The SDK and
bundled runtime must both be `0.159.0`; installed metadata and the actual
app-server initialization identity are checked separately.

## Two profiles, different claims

| Profile | Executed checks | Does not establish |
|---|---|---|
| `tool_free` | Exact SDK/runtime versions, private clean-process app-server initialization | Message inference, provider admission, billing, native tools, filesystem containment |
| `native_tools` | Startup plus fixed `command/exec`: no-op, read-only write denial, workspace write/readback, sibling write denial | Arbitrary tools, all host files hidden, egress isolation, candidate-code safety, product readiness |

The tool-free gateway must separately strip tools and reject tool outputs before
the SDK sees them. This preflight does not replace that gate or prove the gateway.
Neither profile invokes a model. There is no automatic retry or alternate sandbox.
Native failures never trigger full access, extra capabilities, or changed host policy.

The parent creates only temporary fixture directories under an explicitly supplied,
existing, owned `0700` directory. HOME, CODEX_HOME and TMPDIR are private. The child
receives no ambient credentials/settings. Its process group has a 30-second default
deadline (1–120 configurable), fixed native-command 5-second limits, and bounded
JSON output. Raw error/stdout content is not reported. Same-UID hostile mutation
and read access to host files are outside this diagnostic's threat model.

## Mandatory deployment runtime

The runtime Dockerfile always installs the SDK into an isolated
`/opt/context-research/codex-venv`. `requirements-codex-linux.txt` pins eight
packages and the reviewed CPython 3.12 Linux ARM64 and AMD64 wheel hashes. Optional
`INSTALL_MCP=0|1` still controls only the separate application environment; it
cannot disable the SDK or change its dependencies. Other ABIs fail closed.

The release launcher requires `RESEARCH_CODEX_DEPENDENCY_LOCK` to match the
reviewed release's generic lock. It performs the tool-free startup probe before
organization `cycle`/`serve` admission. Read-only inspection/API and deterministic
retrieval commands do not start the SDK, so an unavailable agent runtime does not
prevent operator diagnosis. `RESEARCH_CODEX_PYTHON` selects the SDK interpreter; the
image sets its isolated venv path, and native deployments default to the launcher
interpreter when this variable is absent. These are paths, not new credentials.
An explicit `--sdk-python` must match that choice. For the organization entrypoint,
the launcher supplies the matching argument when omitted. No agent/session is
created by this preflight. All native systemd templates include the SDK lock and
interpreter paths. The organization template's `TasksMax=256` matches the bounded
SDK rehearsal; retrieval/API limits remain distinct. These process counts are
configured ceilings, not measured peak concurrency or capacity claims.

## Reproducible Linux prerequisite recipe

The dated `requirements-codex-linux-aarch64.txt` preserves the original ARM64-only
closure. The mandatory generic `requirements-codex-linux.txt` adds the two reviewed
AMD64 binary-wheel hashes; the six platform-independent wheel hashes are identical.
Neither lock establishes runtime sandbox support. Review a separate closure before
supporting a different architecture/ABI. Keep wheels
in an operator-owned cache; download/install is explicit, never part of preflight.

From a clean checkout in a disposable, non-root reference VM with no credentials:

```sh
python3.12 -m venv /absolute/private/codex-venv
/absolute/private/codex-venv/bin/python -m pip download \
  --only-binary=:all: --require-hashes \
  -r researcher/service/deploy/requirements-codex-linux.txt \
  --dest /absolute/private/wheels
/absolute/private/codex-venv/bin/python -m pip install \
  --no-index --find-links /absolute/private/wheels --only-binary=:all: \
  --require-hashes -r researcher/service/deploy/requirements-codex-linux.txt
/absolute/private/codex-venv/bin/python -m pip check
env -i PATH=/absolute/private/codex-venv/bin:/usr/bin:/bin \
  /absolute/private/codex-venv/bin/python -I -B \
  researcher/service/deploy/verify_codex_runtime.py \
  --workspace-parent /absolute/existing/owned-0700-fixture-parent \
  --profile native_tools
```

Use `--profile tool_free` only for the narrower startup prerequisite. A Linux VM
that supports the pinned runtime's native sandbox is the proposed reference for
native tools; no particular VM provider or supported deployment is established by
this recipe. Do not run on a secret-bearing shared host to compensate for container
restrictions. A future CI job must retain failures and require the intended profile
to pass under its actual deployment constraints, with no privilege bypass.

After prerequisites, run the real SDK's local fake-provider tests explicitly.
Those tests use loopback SSE, not paid inference. Ensure zero skipped tests; the
ordinary suite otherwise intentionally skips real-SDK tests without this opt-in:

```sh
env -i PATH=/absolute/private/codex-venv/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. \
  CODEX_WORKER_TEST_PYTHON=/absolute/private/codex-venv/bin/python \
  /absolute/private/codex-venv/bin/python -c 'import unittest; s=unittest.defaultTestLoader.loadTestsFromName("researcher.service.tests.test_codex_worker"); r=unittest.TextTestRunner(verbosity=2).run(s); raise SystemExit(not (r.wasSuccessful() and r.testsRun > 0 and not r.skipped))'
```

For the tool-free gateway, pipeline and organization gate, use the dedicated
verifier. Run it with the SDK interpreter, supplying a separate application
interpreter that has `requirements-dev.txt` and its `agentskills` executable.
The latter is essential for actual candidate-overlay validators, not an optional
mock. `--service-python` makes all six selected groups mandatory, requires
nonempty execution and zero skips/expected failures, binds the complete reviewed
source snapshot before/after, and imposes a 300-second child-process deadline.
Diagnostics are discarded; only closed counts/digests are returned. The test
child inherits no credentials and accepts numeric-loopback connections only;
the deployment rehearsal must additionally run with OS network isolation.

The `codex-linux-prerequisite/v3` receipt retains the failing aggregate when a
child cannot produce a valid result and adds nullable `tool_free_diagnostic_code`.
Only `TIMEOUT`, `OUTPUT_LIMIT`, `INVALID_RESULT` and `CHILD_FAILED` are exposed.
Unknown exceptions remain generic; no stderr, raw exception message or path is
returned. A timeout is not a passing test or authority to increase its deadline.
Earlier v2 receipts remain unchanged historical evidence.

```sh
env -i PATH=/absolute/private/codex-venv/bin:/usr/bin:/bin \
  /absolute/private/codex-venv/bin/python -I -B \
  researcher/service/deploy/verify_codex_runtime.py \
  --workspace-parent /absolute/existing/owned-0700-fixture-parent \
  --profile tool_free --service-python /absolute/private/application-venv/bin/python
```

This explicitly selects `test_codex_campaign`, `SDKPipelineTests`,
`SDKOrganizationTests`, `SDKLearningTests` (three simulated days, exact duplicate
suppression and no-call same-slot repeat), `SDKPipelineActionTests` (captured
actions and authenticated restart), and `SDKShutdownTests` (cooperative drain
without duplicate effects), not the native-patch worker test. A pass is a real-SDK,
synthetic-source/provider integration gate, not semantic-quality, live-provider,
or native-tool evidence. The release scenario catalog remains separate; it must
not import SDK tests and silently skip them when no interpreter was supplied.

## Retained failed Linux evidence, 2026-09-29

The earlier exact-wheel experiment used a non-root Linux aarch64 image, read-only
root filesystem, no network, all capabilities dropped, no-new-privileges, and
writable private tmpfs. **The worker suite failed: 25 executed, 24 passed, one
workspace-write failure, zero skips.** A model-terminal completion did not imply
that its file-change tool succeeded. No test assertion was weakened.

Repeating under a dedicated `/workspace` tmpfs still failed. A direct same-UID
write there succeeded, but the bundled sandbox helper reported inability to create
a new namespace; an unprivileged `unshare` probe also returned permission denied.
This rules out a simple `/tmp` exclusion or ordinary file-mode explanation. It does
not separate container seccomp policy from host namespace policy. The image digest
was `sha256:38f3946ce5f963777b8f7f65ed65f1e1b78e226a198298dfca731e6e9d1c639b`.
That native-tools deployment is **not supported by the evidence**. No host sysctl,
Docker security flag, assertion, or privilege was relaxed to manufacture a pass.

The new preflight was then executed in that same hardened image using the cached
eight-wheel lock, with no host mounts or network: `pip check` passed, `tool_free`
startup passed, and `native_tools` returned the explicit blocker
`NATIVE_NAMESPACE_DENIED` before any native command succeeded. Its 26 deterministic
contract tests passed on Linux CPython 3.12 and macOS CPython 3.11. The expected
negative diagnostic is useful evidence, not a native-tools deployment pass.

On macOS, the new fixed native preflight passes outside the surrounding automation
sandbox and fails closed inside it. This is environment-specific evidence, not a
claim of Linux native support. Tool-free startup and actual tool-free gateway
execution have separate gates from this native-tool failure.

The separate hardened-Linux tool-free campaign/pipeline run passed all 18 selected
tests with zero skips in 59.029 seconds: the real SDK processed researcher, critic
and editor roles, then twelve independent evaluation threads, exact candidate
freezing and credential-free replay. Upstream answers/sources were synthetic;
model API calls and claimed scientific improvements were zero. An earlier run
failed `CANDIDATE_UNSAFE_SOURCE_PATH`; its failed receipt is retained. The passing
run disabled macOS copyfile metadata during transport and verified the exact
913-file source digest inside Linux before testing. This does not turn the
separate failed native-tool suite into a pass.

## Official contracts used

- [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk): SDK and bundled runtime.
- [App-server](https://learn.chatgpt.com/docs/app-server): `command/exec` is sandboxed and does not require a thread/turn. This diagnostic never uses unsandboxed `process/*` or `thread/shellCommand`.
- [Sandboxing](https://learn.chatgpt.com/docs/sandboxing): native Linux namespace/bubblewrap prerequisites.
- [Approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security): platform and container restrictions. Documented bypass modes are deliberately not used.
