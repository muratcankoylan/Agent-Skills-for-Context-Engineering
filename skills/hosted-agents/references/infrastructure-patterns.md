# Infrastructure Patterns for Hosted Agents

This reference provides preparatory pseudocode for hosted-agent infrastructure. It is not a production implementation or a claim that the illustrated provider adapters exist. Before deployment, replace every adapter with a tested implementation and complete the threat model, authentication, authorization, supervision, resource limits, redaction, recovery, and provider-isolation work.

## Sandbox Architecture

### Modal Integration Pattern

Treat every provider SDK as an untrusted adapter surface until its behavior is
verified. The application accepts only canonical configured repositories,
authenticated principals, current repository authorization receipts, and
digest-pinned images with bounded resources. It never restores a caller's raw
snapshot locator. A trusted snapshot-binding provider must resolve the locator
to authoritative repository/principal metadata before restore; the restored
sandbox must then independently report the expected repository.

All process execution uses validated argument vectors, never a shell. For Git,
a private broker resolves one opaque, repository- and operation-scoped lease
inside a trusted `GIT_ASKPASS` boundary. The bearer value never enters argv,
URLs, application memory, logs, metadata, artifacts, or snapshots, and the
lease is revoked when the single Git operation ends.

### Image Build Pipeline

The build orchestrator must enforce these gates; failure of any gate prevents
image publication:

1. Start from a digest-pinned base image with validated CPU, memory, disk,
   process-count, wall-time, and egress ceilings.
2. Clone through one opaque `clone` lease and close it before repository code
   runs. The credential-free remote is derived from the canonical repository.
3. `assert_untrusted_build_boundary` proves the build child has no ambient
   credentials, broker/control socket, cloud metadata access, or unmediated
   egress. Dependency resolution uses a lockfile and immutable dependency
   policy; do not introduce unpinned package installation in the base image.
4. Every install, build, and test command must terminate successfully. No
   ignored exit status and no development or cache-warming daemon is allowed.
5. `stop_and_reap_all` removes every descendant and credential helper, then
   `assert_quiescent` proves the process table, writable secret state, and
   broker channels are clean before snapshot finalization.
6. Publish an immutable image record bound to its repository, commit digest,
   base-image digest, policy version, and verification receipt. Application
   code cannot mutate this record after publication.

### Warm Pool Management

Serialize maintenance per canonical repository so concurrent calls cannot
overprovision. Remove expired, unsynchronized, or wrong-image entries and
terminate each unclaimed sandbox before replacement. A claimed sandbox belongs
to its session and is removed from pool ownership.

Create a candidate privately. Acquire a new opaque `fetch` lease, complete
fetch/reset inside a fixed deadline, and publish the candidate only after sync
succeeds. On timeout, cancellation, or typed sync failure, terminate the
candidate and return a stable failure. Never use a detached task plus polling;
an unsynchronized candidate is never offered.

Session allocation accepts only configured repositories and a current
authorization receipt bound to the authenticated principal, canonical
repository, and `session:start` action. A snapshot reference is an untrusted
locator: resolve it through the authoritative snapshot-binding provider and
require its repository/principal attestation to match the current request
before restore. Independently verify the restored sandbox repository. Unknown,
cross-repository, cross-actor, expired, missing, or mismatched inputs all return
the same non-enumerating denial. If identity configuration fails after any
sandbox is acquired, terminate that sandbox before returning the error. Every
session snapshot crosses the same fail-closed finalization hook as an image:
reap descendants, revoke and close credential helpers, prove quiescence and
credential absence, then create and authoritatively attest the snapshot. A
failed hook creates and attests no snapshot.

## API Layer Patterns

### Cloudflare Durable Objects for Session State

Each session may use an isolated Durable Object, but this reference deliberately does not provide a copyable handler. A production adapter must prove the following fail-closed contract:

#### Browser HTTP and WebSocket ingress

- `authenticateRequest` verifies issuer, audience, expiry, signature, and subject before routing.
- `authorizeSessionAccess` proves current session membership and returns a classification ceiling. Missing and denied sessions use the same non-enumerating response.
- `allowedOrigins`, exact methods, content type, and `MAX_MESSAGE_BYTES` are checked before bounded parsing.
- `validateMessagePayload` accepts a versioned closed schema, rejects unknown fields, binds the author to the authenticated principal, and requires an `idempotencyKey`.
- WebSocket upgrades require a single-use handshake nonce. `consumeReplayNonce` is durable and atomic. Each connection stores its principal, current membership version, and clearance; revocation closes it.
- Broadcast is per connection. Re-authorize when the membership version changes, then classify and redact for that connection's clearance. Never broadcast one pre-serialized payload to every participant.

#### Durable command and idempotency state

Use one transaction to claim `(principalId, idempotencyKey)`, record the canonical request digest, and persist a pending intent plus outbox record. The same key and digest returns the existing receipt; the same key with a different digest is an idempotency collision and performs no effect. A supervised dispatcher processes the outbox, records the typed result, and marks the intent complete atomically. Recovery resumes pending intents without forwarding a command twice. Do not broadcast or acknowledge success before the durable result exists.

### Real-Time Event Streaming

Browser ingress and sandbox-event ingress are different routes and trust policies. Define `POST /internal/event` explicitly. It rejects browser requests and instead requires an authenticated service identity, an attested sandbox-to-session binding, exact method and content type, `MAX_EVENT_BYTES`, a closed event schema, and a monotonically consumed producer sequence. Before persistence or fan-out, `classifyAndRedactEvent` converts the event to a typed projection at the session classification ceiling. Raw sandbox payloads never cross into client storage or WebSocket frames. Sequence replay, gaps, malformed data, or classification uncertainty fail closed and emit only redacted audit metadata.

## Client Integration Patterns

### Slack Bot with Repository Classification

Repository classification is routing assistance, not authority. The Slack connector keeps its service credential inside the connector boundary and passes the application a verified event:

```python
async def handle_verified_mention(event, say):
    principal = await authenticate_slack_user(event)
    candidate_repository = await classify_or_read_selected_repository(event)
    if candidate_repository == "unknown":
        await say("Specify a repository you are permitted to access.")
        return

    repository = normalize_github_repository(candidate_repository)
    access = await authorize_repository_access(
        principal=principal,
        repository=repository,
        action="session:start",
    )
    if not access.allowed:
        # Do not reveal whether the repository exists or why access failed.
        await say("Unable to start that repository session.")
        return

    session = await start_session(
        repository,
        principal=principal,
        authorization=access.receipt,
    )
    await say("Authorized session started.")
    await session.process(validate_prompt(event))
```

`authenticate_slack_user` requires a verified Slack transport event and maps the workspace/user pair to an internal principal. `authorize_repository_access` evaluates current repository membership and policy after normalization. The same decision is mandatory for a repository typed by the user, selected in a UI, or proposed by a model. Do not warm a repository, disclose its metadata, or call `start_session` before the allow decision.

### Chrome Extension DOM Extraction

Do not copy arbitrary page DOM or framework internals into an agent context. A production extractor must enforce these boundaries:

- Authenticate the extension and authorize the principal for the target session and repository before capture.
- Require an explicit user selection and an allowlisted origin. Exclude credential fields, hidden elements, cross-origin frames, extension pages, and browser-managed surfaces.
- Bound traversal by node count, depth, elapsed time, and encoded bytes. Abort rather than truncate into an ambiguous schema.
- Emit a versioned closed schema. Classify and redact text, attributes, URLs, and framework metadata before they leave the browser; never send a raw DOM object or unbounded `textContent`.
- Bind the extraction to a nonce, session, origin, tab, timestamp, and content digest so replay or cross-session reuse fails closed.
- Render a user-visible preview of the released projection and retain only redacted audit metadata.

## Multiplayer Implementation

### Authorship and Concurrent Effects

Do not trust `PromptContext.author` or any client-supplied identity. Bind each prompt to a server-attested principal, current session-membership decision, repository authorization receipt, classification ceiling, and idempotency key before it enters a queue.

A shared workspace has one mutation owner at a time. Serialize commit-producing operations or use isolated branches/worktrees with explicit merge arbitration. Do not mutate shared `git config` concurrently; pass validated author identity to the single commit operation or use an isolated repository config per attempt.

PR creation is a destination-locked broker effect bound to the authorized repository, exact branch and commit, initiating principal, base branch policy, and idempotency key. Persist a pending intent and outbox entry before the effect, reject key/digest collisions, and record one typed result before broadcasting. A participant record never carries a bearer credential, and one participant's clearance never authorizes data release to another.

## Metrics and Monitoring

### Key Metrics to Track

Define a versioned event schema before choosing an aggregator. Derive metrics
only from durable typed events with a declared window, clock semantics,
deduplication key, repository/principal privacy policy, and completeness lag.
Publish the numerator, denominator, sample size, and missing-data count for
every rate. Empty windows return an explicit `no_data` state, never a fabricated
zero or a division-by-zero path. At minimum, measure authorization denials,
warm-sync latency/failure, build-gate failure, cleanup/quiescence failure,
session start latency, first useful result, task outcome, human review outcome,
resource consumption, and cost per accepted outcome.

## Security Considerations

### Sandbox Isolation

Treat command and network policy as positive capabilities, not a command denylist. A shell, alternate binary, language runtime, or renamed executable trivially bypasses string matching.

- Start from no ambient credentials and no direct network. Grant a typed command/effect capability for one operation and revoke it at completion.
- Route permitted egress through an enforcing proxy bound to exact scheme, destination, port, repository, operation, and resolved-address policy. Hostname strings alone are not an egress boundary.
- Validate integer CPU, memory, disk, process, and duration limits before provider allocation. Require an immutable digest-pinned base image.
- Execute untrusted repository build and test code in a child isolation boundary with no broker lease, cloud metadata access, control-plane socket, or inherited secret.
- Require every build and test to succeed. Stop and reap all child processes, verify no writable secret/helper state remains, then finalize the snapshot. Never snapshot a cache-warming daemon.
- Exclude memory-backed broker channels and helpers from snapshots, traces, process metadata, and artifact collection.

### Ephemeral Credential Brokerage

```python
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Literal

GitOperation = Literal["clone", "fetch", "push"]

@dataclass(frozen=True, slots=True, repr=False)
class GitCredentialLease:
    """Opaque capability metadata; contains no bearer credential."""

    repository: str
    operation: GitOperation
    expires_at: datetime
    _capability: object  # Unforgeable in-process reference, never serialized.

    def __repr__(self) -> str:
        return "<GitCredentialLease redacted>"

class GitHubCredentialBroker:
    """Own GitHub credentials and expose only constrained operations."""

    @asynccontextmanager
    async def git_lease(
        self,
        *,
        repository: str,
        operation: GitOperation,
    ) -> AsyncIterator[GitCredentialLease]:
        repository = normalize_github_repository(repository)
        capability = await self.private_broker.issue_git_capability(
            repository=repository,
            operation=operation,
            ttl_seconds=60,
        )
        lease = GitCredentialLease(
            repository=repository,
            operation=operation,
            expires_at=capability.expires_at,
            _capability=capability.reference,
        )
        try:
            yield lease
        finally:
            await self.private_broker.revoke(capability.reference)

    def github_effect(
        self,
        *,
        principal_id: str,
        repository: str,
        operation: Literal["pull_request:create"],
    ):
        """Return a destination-locked client, never a raw credential."""
        return self.private_broker.scoped_github_client(
            principal_id=normalize_identity_id(principal_id),
            repository=normalize_github_repository(repository),
            operation=operation,
        )
```

Prefer GitHub App installation grants with the minimum repository permissions. Mint short-lived credentials only inside the private broker at effect time. Do not return them to application code or store them in users, sessions, queues, databases, caches, images, or snapshots. If user delegation is required, keep the refresh grant in an external secrets service and expose the same constrained effect API; application workers still never decrypt or receive it.

The execution adapter must use direct process spawning (`execve` or an SDK equivalent), pass every untrusted value as exactly one argv element, and reject shell-string APIs and shell interpreter dispatch. Validate repository, principal, display-name, email, branch, and working-directory fields at their ingress boundaries. Logs should contain canonical identifiers, operation names, stable error codes, and exception types only. Never log rejected raw input or exception text from credential providers.

## References

- [Modal Documentation](https://modal.com/docs)
- [Cloudflare Durable Objects](https://developers.cloudflare.com/durable-objects/)
- [Cloudflare Agents SDK](https://developers.cloudflare.com/agents/)
- [GitHub Apps Authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app)
- [Slack Bolt for Python](https://slack.dev/bolt-python/)
- [Chrome Extension APIs](https://developer.chrome.com/docs/extensions/)
