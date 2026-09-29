---
name: hosted-agents
description: "This skill should be used when designing hosted or background agent infrastructure: sandboxed execution, remote coding environments, warm pools, session persistence, multiplayer collaboration, self-spawning agents, or Modal-style sandboxes."
---

# Hosted Agent Infrastructure

Hosted agents run in remote sandboxed environments rather than on local machines. When designed well, they provide elastic but explicitly bounded concurrency, consistent execution environments, and multiplayer collaboration. Session speed should minimize infrastructure overhead without hiding authorization, synchronization, isolation, or readiness checks.

Treat this skill and its bundled examples as preparatory architecture guidance, not production-ready infrastructure. Production use requires a provider-specific sandbox adapter, authenticated authorization boundary, credential broker, supervised task lifecycle, bounded failure handling, and adversarial verification.

## When to Activate

Activate this skill when:
- Building background coding agents that run independently of user devices
- Designing sandboxed execution environments for agent workloads
- Implementing multiplayer agent sessions with shared state
- Creating multi-client agent interfaces (Slack, Web, Chrome extensions)
- Scaling agent infrastructure beyond local machine constraints
- Building systems where agents spawn sub-agents for parallel work

Do not activate this skill for adjacent work owned by other skills:
- Designing the autonomous research loop, novelty gates, rollback policy, or merge boundaries: `harness-engineering`.
- Choosing supervisor, swarm, or handoff topology without hosted infrastructure concerns: `multi-agent-patterns`.
- Designing the tools used by a hosted agent, such as spawn/status tools or PR tools: `tool-design`.
- Managing file-backed state inside a session rather than the hosted runtime itself: `filesystem-context`.

## Core Concepts

Move agent execution to remote sandboxed environments when measured workload needs justify it. Remote sandboxes can provide bounded concurrency, reproducible environments, and collaborative workflows because each session gets isolated compute with an attested environment image. Set hard attempt, cost, and resource ceilings; elasticity is not infinite capacity.

Design the architecture in three layers because each layer scales independently. Build sandbox infrastructure for isolated execution, an API layer for state management and client coordination, and client interfaces for user interaction across platforms. Keep these layers cleanly separated so sandbox changes do not ripple into clients.

## Detailed Topics

### Sandbox Infrastructure

**The Core Challenge**
Eliminate sandbox spin-up latency because users perceive anything over a few seconds as broken. Development environments require cloning repositories, installing dependencies, and running build steps -- do all of this before the user ever submits a prompt.

**Image Registry Pattern**
Pre-build environment images on a regular cadence (every 30 minutes works well) because this makes synchronization with the latest code a fast delta rather than a full clone. Include in each image:
- Cloned repository at a known commit
- All runtime dependencies installed
- Initial setup and build commands completed
- Cache outputs from successful, terminating build and test commands

Require a digest-pinned base image and validated integer CPU, memory, disk, process, and duration bounds before allocation. Close the clone lease before running repository-controlled build or test code, and execute that code in a child boundary with no ambient credentials, broker socket, cloud metadata access, or unmediated egress. Every verification step must succeed. Reap all processes and prove quiescence before finalizing a snapshot; do not snapshot a background cache-warming server.

When starting a session, spin up a sandbox from the most recent image. The repository is at most 30 minutes out of date, making the remaining git sync fast.

**Snapshot and Restore**
Take filesystem snapshots at key points to enable instant restoration for follow-up prompts without re-running setup:
- After initial image build (base snapshot)
- When agent finishes making changes (session snapshot)
- Before sandbox exit for potential follow-up

Route every image and session snapshot through one fail-closed finalization gate that reaps descendants and proves quiescence, closed credential helpers, and absence of credential material before snapshot creation. Treat a session snapshot reference as an untrusted opaque locator. Resolve its repository and principal through an authoritative snapshot-binding provider, require that binding to match the current authorization receipt, and independently verify the restored sandbox identity before exposure. Attest every new snapshot through the same provider before returning its locator.

**Git Configuration for Background Agents**
Configure git identity explicitly in every sandbox because background agents are not tied to a specific user during image builds:
- Request a new opaque, short-lived, repository- and operation-scoped lease from a credential broker for each clone, fetch, or push
- Keep bearer credentials inside the broker; never return them to the sandbox manager, place them in a URL or command, or persist them in sessions, queues, logs, images, or snapshots
- Set git config `user.name` and `user.email` when committing and pushing changes
- Use the prompting user's identity for commits, not the app identity

**Warm Pool Strategy**
Maintain a pool of pre-warmed sandboxes for high-volume repositories because cold starts are the primary source of user frustration:
- Authorize the authenticated principal for the selected repository before warming or allocating any sandbox
- Complete a bounded, credentialed fetch and reset before publishing a sandbox as ready; terminate and exclude it on any sync failure
- Expire and terminate stale, unclaimed pool entries as new image builds complete
- Serialize maintenance per repository so concurrent warm-up signals cannot overprovision the pool

### Agent Framework Selection

**Server-First Architecture**
Structure the agent framework as a server first, with TUI and desktop apps as thin clients, because this prevents duplicating agent logic across surfaces:
- Multiple custom clients share one agent backend
- Consistent behavior across all interaction surfaces
- Plugin systems extend functionality without client changes
- Event-driven architectures deliver real-time updates to any connected client

**Code as Source of Truth**
Select frameworks where the agent can read its own source code to understand behavior. Prioritize this because having code as source of truth prevents the agent from hallucinating about its own capabilities -- an underrated failure mode in AI development.

**Plugin System Requirements**
Require a plugin system that supports runtime interception because this enables safety controls and observability without modifying core agent logic:
- Listen to tool execution events (e.g., `tool.execute.before`)
- Block or modify tool calls conditionally
- Inject context or state at runtime

### Speed Optimizations

**Predictive Warm-Up**
After authenticating the user and authorizing repository membership, begin supervised warm-up while the user is typing. The API or supervisor must own and observe the task, its deadline, and its failure; do not drop an untracked background task. A sandbox becomes selectable only after its bounded sync succeeds.

**Readiness Before I/O**
Do not expose a sandbox for reads or writes while repository synchronization is incomplete. Stale reads can misdirect an agent and create time-of-check/time-of-use inconsistencies even if writes are delayed. Complete sync within a fixed deadline or fail the allocation with a typed error; never poll indefinitely for readiness.

**Maximize Build-Time Work**
Move everything possible to the image build step because build-time duration is invisible to users:
- Full dependency installation
- Database schema setup
- Initial app and test suite runs (populates caches)

### Self-Spawning Agents

**Agent-Spawned Sessions**
Build tools that allow agents to spawn new sessions because frontier models are capable of decomposing work and coordinating sub-tasks:
- Research tasks across different repositories
- Parallel subtask execution for large changes
- Multiple smaller PRs from one major task

Expose three primitives: start a new session with specified parameters, read status of any session (check-in capability), and continue main work while sub-sessions run in parallel.

**Prompt Engineering for Self-Spawning**
Engineer prompts that guide when agents should spawn sub-sessions rather than doing work inline:
- Research tasks that require cross-repository exploration
- Breaking monolithic changes into smaller PRs
- Parallel exploration of different approaches

### API Layer

**Per-Session State Isolation**
Isolate state per session (SQLite per session works well) because cross-session interference is a subtle and hard-to-debug failure mode:
- Dedicated database per session
- No session can impact another's performance
- Treat hundreds of concurrent sessions as an unmeasured capacity target until load, isolation, quota, and cost tests demonstrate it; enforce a lower explicit ceiling meanwhile

**Real-Time Streaming**
Stream all agent work in real-time because high-frequency feedback is critical for user trust:
- Token streaming from model providers
- Tool execution status updates
- File change notifications

Use WebSocket connections with hibernation APIs to reduce compute costs during idle periods while maintaining open connections.

**Synchronization Across Clients**
Build a single state system that synchronizes across all clients (chat interfaces, Slack bots, Chrome extensions, web interfaces, VS Code instances) because users switch surfaces frequently and expect continuity. All changes sync to the session state, enabling seamless client switching.

### Multiplayer Support

**Why Multiplayer Matters**
Plan multiplayer boundaries early because identity, clearance, concurrent mutation, and audit semantics are expensive to retrofit. Implement it only when measured value justifies its additional authorization and coordination cost:
- Teaching non-engineers to use AI effectively
- Live QA sessions with multiple team members
- Real-time PR review with immediate changes
- Collaborative debugging sessions

**Implementation Requirements**
Build the data model so sessions are not tied to single authors because multiplayer fails silently if authorship is hardcoded:
- Pass authorship info to each prompt
- Attribute code changes to the prompting user
- Share session links for instant collaboration

### Authentication and Authorization

**User-Based Commits**
Preserve human attribution without exposing credentials to application or sandbox code:
- Resolve the authenticated principal to repository membership before a session can start
- Use a destination- and operation-locked broker effect to push branches or create PRs
- Record the initiating principal in durable audit metadata; do not claim GitHub authorship semantics that the selected App or delegated grant cannot provide

**Sandbox-to-API Flow**
Follow this sequence because it keeps sandbox permissions minimal while letting the API handle sensitive operations:
1. Sandbox requests a new brokered, repository-scoped push lease after policy approval
2. Sandbox sends event to API with branch name and session ID
3. API invokes a destination-locked GitHub effect for PR creation without receiving a bearer credential
4. GitHub webhooks notify API of PR events

### Client Implementations

**Slack Integration**
Prioritize Slack as the first distribution channel for internal adoption because it creates a virality loop as team members see others using it:
- No syntax required, natural chat interface
- Treat classifier output or a user-selected repository as an untrusted candidate, never an authorization decision
- Verify the Slack request, map the Slack user to an authenticated principal, and require repository-membership authorization before warm-up or session creation
- Fail closed with no repository disclosure when classification is ambiguous or access is denied

**Web Interface**
Build a web interface with these features because it serves as the primary power-user surface:
- Real-time streaming of agent work on desktop and mobile
- Hosted VS Code instance running inside sandbox
- Streamed desktop view for visual verification
- Before/after screenshots for PRs
- Statistics page: sessions resulting in merged PRs (primary metric), usage over time, live "humans prompting" count

**Chrome Extension**
Treat a Chrome extension for non-engineering users as a separately threat-modeled client. DOM or React extraction is an untrusted collection boundary, and any quality or token advantage over screenshots must be measured for the actual tasks:
- Sidebar chat interface with screenshot tool
- Allow extraction only on an origin allowlist and after explicit user selection; use explicit selectors, bound traversal depth/node count/time/bytes, a closed schema, classification and redaction, and a user preview before release
- Distribute via managed device policy (bypasses Chrome Web Store)

## Practical Guidance

### Hosted Agent Design Checklist

Before building the system, decide these infrastructure properties explicitly:

1. **Sandbox lifecycle**: how sessions start, snapshot, restore, time out, and terminate.
2. **Image and warm-pool policy**: how often images rebuild, which caches are precomputed, and when warm sandboxes expire.
3. **Repository readiness**: the deadline and typed failure used to ensure no sandbox is offered before credentialed synchronization succeeds.
4. **Per-session state isolation**: what storage belongs to one session, what is shared, and how cross-session interference is prevented.
5. **Auth and commit identity**: which authenticated principal and repository grant authorize each brokered Git or GitHub effect, and how commits are attributed.
6. **Output extraction**: how branches, PRs, files, logs, screenshots, and session summaries leave the sandbox.
7. **Budget and teardown**: maximum runtime, cost ceilings, idle policy, and forced cleanup behavior.

Treat configured repository membership, the current authorization receipt, pinned image digest, resource bounds, and an authoritative snapshot actor/repository attestation as allocation preconditions rather than optional runtime checks.

### Follow-Up Message Handling

Choose between queueing and inserting follow-up messages sent during execution. Prefer queueing because it is simpler to manage and lets users send thoughts on next steps while the agent works. Build a mechanism to stop the agent mid-execution when needed, because without it users feel trapped.

### Metrics That Matter

Track these metrics because they indicate real value rather than vanity usage:
- Sessions resulting in merged PRs (primary success metric)
- Time from session start to first model response
- PR approval rate and revision count
- Agent-written code percentage across repositories

### Adoption Strategy

Drive internal adoption through visibility rather than mandates because forced usage breeds resentment:
- Work in public spaces (Slack channels) for visibility
- Let the product create virality loops
- Do not force usage over existing tools
- Build to people's needs, not hypothetical requirements

## Examples

**Example 1: Background coding session lifecycle**

```text
user prompt
-> API authenticates the user and authorizes repository membership
-> pool builds a candidate from the current image
-> sandbox acquires a new fetch lease and completes bounded sync
-> pool publishes the sandbox as ready; reads and writes are now allowed
-> agent edits and tests inside isolated workspace
-> shared finalization gate reaps processes, proves quiescence and credential absence, then snapshots and attests the filesystem
-> branch is pushed through a new scoped broker lease
-> API creates PR through a destination-locked broker effect
-> session summary, logs, and PR URL are returned to clients
```

This sequence keeps setup work outside the user-visible path while preserving auditability and user ownership of code changes.

**Example 2: Boundary decision**

If the task is "make the agent loop run for days with locked rubrics and PR approval," use `harness-engineering`. If the task is "run that loop in remote sandboxes with warm pools, session snapshots, streaming clients, and user-authored PRs," use this skill.

## Guidelines

1. Pre-build environment images on regular cadence (30 minutes is a good default)
2. Warm only after authenticated repository authorization, under a supervised task with a deadline
3. Publish a sandbox only after credentialed synchronization completes; expose neither reads nor writes before readiness
4. Structure agent framework as server-first with clients as thin wrappers
5. Isolate state per session to prevent cross-session interference
6. Attribute commits to the user who prompted, not the app
7. Track merged PRs as primary success metric
8. Design explicit multiplayer identity and concurrency boundaries, then enable them only after measured validation

## Gotchas

1. **Cold start latency**: First sandbox spin-up takes 30-60s and users perceive this as broken. Use warm pools and predictive warm-up on keystroke to eliminate perceived wait time.
2. **Image staleness**: Infrequent image rebuilds mean agents run with outdated dependencies or code. Set a 30-minute rebuild cadence and monitor image age; alert if builds fail silently.
3. **Sandbox cost runaway**: Long-running agents without timeout or budget caps accumulate unexpected costs. Set hard timeout limits (default 4 hours) and per-session cost ceilings.
4. **Credential lease expiry**: Never refresh or retain a bearer credential inside a session. Request a new short-lived broker lease or constrained effect immediately before each sensitive Git or GitHub operation; fail closed if the broker denies it.
5. **Git config in sandboxes**: Missing `user.name` or `user.email` causes commit failures in background agents. Always set git identity explicitly during sandbox configuration, never assume it carries over from the image.
6. **State loss on sandbox recycle**: Agents lose completed work if the sandbox is recycled or times out before results are extracted. Extract artifacts (branches, PRs, files), pass the shared finalization gate, then snapshot and attest before termination; fail closed rather than snapshotting live processes or credential state.
7. **Oversubscribing warm pools**: Concurrent warm-up signals can race and exceed the target. Serialize maintenance per repository, terminate stale unclaimed entries, and then scale the target from measured traffic.
8. **Missing output extraction**: Agents complete work inside the sandbox but results never get pulled out to the user. Build explicit extraction steps (push branch, create PR, return file contents) into the session teardown flow.

## Integration

This skill owns hosted runtime infrastructure. Adjacent skills own the control system, topology, and tool contracts:

- `harness-engineering`: governance, locked evaluators, rollback, novelty gates, and human approval boundaries around autonomous work.
- `multi-agent-patterns`: self-spawning and supervisor patterns once hosted infrastructure exists.
- `tool-design`: spawn, status, teardown, and PR tools exposed to agents.
- `context-optimization`: managing context across distributed hosted sessions.
- `filesystem-context`: using the sandbox filesystem for durable session state and artifacts.

## References

Internal reference:
- [Infrastructure Patterns](./references/infrastructure-patterns.md) - Read when: implementing sandbox lifecycle, image builds, or warm pool logic for the first time

Related skills in this collection:
- multi-agent-patterns - Read when: designing self-spawning or supervisor coordination patterns
- tool-design - Read when: building tools for agent session management or status checking
- context-optimization - Read when: context windows fill up across distributed agent sessions

External resources:
- [Ramp](https://builders.ramp.com/post/why-we-built-our-background-agent) - Read when: evaluating whether to build vs. buy background agent infrastructure
- [Modal Sandboxes](https://modal.com/docs/guide/sandbox) - Read when: choosing a cloud sandbox provider or comparing isolation models
- [Cloudflare Durable Objects](https://developers.cloudflare.com/durable-objects/) - Read when: designing per-session state management with WebSocket hibernation
- [OpenCode](https://github.com/sst/opencode) - Read when: selecting a server-first agent framework or studying plugin architectures

---

## Skill Metadata

**Created**: 2026-01-12
**Last Updated**: 2026-05-15
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 1.2.0
