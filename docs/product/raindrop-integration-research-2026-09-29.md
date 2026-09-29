# Raindrop integration research

Date: 2026-09-29. Status: source/documentation review, not a live integration acceptance test.

## Decision

Use an explicit, optional repo-native OTLP/HTTP exporter for sanitized service telemetry. Do not make the machine-wide Workshop installer, a coding-agent plugin, automatic instrumentation, or Raindrop's autonomous investigation features a runtime dependency. Keep research state, budget admission, evidence, and publication authority in the harness. Telemetry is an observation of those operations, never authorization to repeat them.

The distinction matters: Workshop is a local debugger and control plane; Raindrop Cloud is a hosted ingestion/query product. Their acknowledgement contracts differ. Neither should be treated as a durable replacement for the harness's write-ahead effect records. This recommendation is an engineering judgment based on the contracts below.

## Scope and evidence identity

- Read public documentation, installer text, and selected official source. No installer, downloaded binary, project replay, provider model request, cloud trace upload, or MCP invocation was executed. No credentials were read or copied.
- The chat-pasted credential must be rotated. A later authorized cloud canary must use a fresh write key from the private environment, never the chat value.
- The live installer at `https://raindrop.sh/install` and the repository installer at commit `a6b82d71596cf7e8974e5efae63f9e15260d76ef` both hashed to `d588912bc46b5c6f46f2869d1d3afb1b3b337312ec7195b05c99e8ff568aa915` during this review. This identifies inspected text, not a verified release binary or complete supply-chain audit. [Installer source](https://github.com/raindrop-ai/workshop/blob/a6b82d71596cf7e8974e5efae63f9e15260d76ef/install.sh)
- The Parallel search/extract skills were read. Their CLI was unavailable, and installation was out of scope, so research used official pages and bounded HTTPS source reads instead. No Parallel result file or paid research run was produced.

## Cloud transport contract

The documented trace endpoint is `POST https://api.raindrop.ai/v1/traces`. Authentication is `Authorization: Bearer <SDK write key>`. Set `X-Raindrop-Project-Id` explicitly; omission selects the default Production project. JSON uses `Content-Type: application/json` without compression. Protobuf uses `application/x-protobuf`, with optional gzip/deflate. OTLP/gRPC, metrics, and logs are not supported by this endpoint. The response is an `ExportTraceServiceResponse` using the request encoding. The documented default rate limit is 1,000 requests per minute per write key, subject to organization configuration; 429 asks for a 60-second delay. Decompressed bodies above 32 MiB are rejected. These are provider ceilings, not recommended harness batch sizes. [Raindrop OpenTelemetry contract](https://www.raindrop.ai/docs/sdk/opentelemetry/)

OTLP JSON uses `resourceSpans -> scopeSpans -> spans`, hexadecimal trace/span IDs, lower-camel-case fields, numeric enums, and decimal-string 64-bit integer fields. Full success is HTTP 200 with a valid response and no partial-success rejection. HTTP 200 can also report partial acceptance through `partialSuccess.rejectedSpans`; zero rejected spans plus an error message can convey a warning. A populated partial-success response must not trigger retransmission of the whole batch. A timed-out export does not prove rejection or acceptance. [OTLP specification](https://opentelemetry.io/docs/specs/otlp/)

For model attribution, Raindrop documents `gen_ai.system`, `gen_ai.response.model`, and `gen_ai.usage.input_tokens`/`output_tokens`. Optional message and system-instruction attributes carry content; the recommended default exporter must exclude them. Model/token fields should be absent when unknown, not fabricated as zero. [Attribute mapping](https://www.raindrop.ai/docs/sdk/opentelemetry/)

The separate events API is not an interchangeable trace endpoint: `/v1/events/track` accepts an array of event objects and documents HTTP 204 acknowledgement. It supports optional AI input/output and tool payloads; events have a 1 MB limit with property truncation. Do not interpret its 204 contract as a valid OTLP acknowledgement. [HTTP events API](https://www.raindrop.ai/docs/sdk/http-api/)

## Workshop installer and collector

The installer resolves a mutable release manifest, verifies downloaded size/SHA-256, installs under `~/.raindrop/bin` by default, and edits the selected shell's startup file to add PATH. Its default final action executes `raindrop setup`. `--no-setup` skips setup but does not skip binary installation or shell modification. `--cloud` selects cloud setup instead. The checksum validates a download against the fetched manifest; it is not independent approval of a release. [Pinned installer](https://github.com/raindrop-ai/workshop/blob/a6b82d71596cf7e8974e5efae63f9e15260d76ef/install.sh)

Setup defaults to global skills plus MCP installation, not repo-local scope. On successful ordinary binary setup it also configures startup and starts Workshop. Source lists Claude Code, Cursor, Codex, OpenCode, Amp, and Windsurf as approved integration targets; exact per-agent paths are delegated to its installer dependency and were not comprehensively audited here. [Setup](https://github.com/raindrop-ai/workshop/blob/a6b82d71596cf7e8974e5efae63f9e15260d76ef/src/init.ts), [Integration target selection](https://github.com/raindrop-ai/workshop/blob/a6b82d71596cf7e8974e5efae63f9e15260d76ef/src/install/detect.ts)

The startup implementation writes `~/Library/LaunchAgents/ai.raindrop.workshop.plist` on macOS, including login startup and failure restart behavior. On Linux it writes a user `raindrop-workshop.service`, reloads systemd, and enables it when supported. This is persistent machine configuration, not merely a temporary debugger process. [Startup source](https://github.com/raindrop-ai/workshop/blob/a6b82d71596cf7e8974e5efae63f9e15260d76ef/src/workshop-startup.ts)

The CLI defaults to port 5899 and loopback binding, keeps PID/log files under `~/.raindrop`, and can spawn a detached daemon. Its MCP bridge can start the daemon automatically. `workshop setup` additionally writes `RAINDROP_LOCAL_DEBUGGER` to a project environment file. Cloud setup is distinct: the documented flow signs in, stores a write key in `./.env`, and installs hosted MCP/cloud skills without starting the local daemon. [CLI source](https://github.com/raindrop-ai/workshop/blob/a6b82d71596cf7e8974e5efae63f9e15260d76ef/src/index.ts), [Cloud setup documentation](https://github.com/raindrop-ai/workshop/blob/a6b82d71596cf7e8974e5efae63f9e15260d76ef/README.md)

The inspected local server accepts OTLP JSON/protobuf at `/v1/traces` and two compatibility aliases. It enforces loopback source access by default, with Host/Origin checks and explicit opt-ins for local-network access. No write-key authentication check was found in the trace-ingestion path. It returns `{ok:true, spansIngested:N}`, including zero for a body that parses to no spans, rather than the cloud OTLP response schema. Local compatibility therefore needs a separate acknowledgement validator and must never receive the cloud write key. The server also exposes agent/replay and provider-backed operations; do not expose it as an unauthenticated public collector. [Pinned collector implementation](https://github.com/raindrop-ai/workshop/blob/a6b82d71596cf7e8974e5efae63f9e15260d76ef/src/server.ts)

The parser converts timestamps to millisecond values and derives duration from end minus start unless an explicit duration attribute is present. It stores normalized spans/attributes; arbitrary OTLP events are not preserved as a general event list in the returned parsed-span record, although exception-message events are inspected. Do not assume every custom event appears losslessly in Workshop. [Parser source](https://github.com/raindrop-ai/workshop/blob/a6b82d71596cf7e8974e5efae63f9e15260d76ef/src/parse.ts)

## SDKs and managed-agent visibility

The Python package is `raindrop-ai`. Its documented tracing mode can auto-instrument detected LLM clients; `auto_instrument=False` disables that behavior while retaining manual tracing. It buffers events, documents up to three request retries, and requires flushing/shutdown for short-lived processes. Git metadata discovery and shared process-wide OpenTelemetry state are additional behaviors to account for. A narrow direct exporter avoids introducing those defaults into the existing effect/budget boundary. [Python SDK](https://www.raindrop.ai/docs/sdk/python/)

Raindrop now documents a separate beta managed OpenAI Agents API wrapper, `@raindrop-ai/openai-managed-agents`, requiring Node 22+ and `openai >=7.15.0 <8`. It captures turns and supported tool operations, not internal inference calls. Automatic capture excludes reasoning, intermediate commentary, agent-to-agent messages, streaming deltas, and images. Usage is best-effort; revisions after the first terminal receipt are not applied. Observed span timing can include recovery, and subagent model identity need not match session configuration. Stable event identity is required across process restarts. Its redaction hook covers captured text, but callers must redact their own properties and attachments. This TypeScript wrapper is not evidence that the repository's Python HTTP adapter is already instrumented. [Managed Agents integration](https://www.raindrop.ai/docs/integrations/openai-managed-agents.md)

## Privacy and authority

Raindrop states that it stores/processes data sent by default. Server-side PII Guard acts during ingestion; it cannot prevent the original data from leaving this harness. Its separate client-side PII documentation currently describes TypeScript regex redaction, not a universal guarantee for Python/OTLP. Use a closed, typed metadata projection before serialization, not a secret regex applied to arbitrary prompts and errors. [Privacy and PII](https://www.raindrop.ai/docs/security/pii-redaction/)

The vendor describes encrypted transport/storage and US subprocessors, including model providers. This is a vendor statement, not an independent audit or authorization to export private research. Retention, deletion, plan entitlements, and organization settings must be checked before a real deployment. [Security statement](https://www.raindrop.ai/docs/security/data-security-and-privacy/)

The hosted MCP endpoint is `https://mcp.raindrop.ai/mcp`, using Streamable HTTP and OAuth or an API key. Its query key is distinct from the ingestion write key. Tools include both data queries and investigation/configuration capabilities; registering every discovered tool is not a read-only integration. No Raindrop MCP was connected in this review. [MCP documentation](https://www.raindrop.ai/docs/mcp/overview/)

## Narrow implementation recommendation

These are proposed harness requirements, not claims about work completed in this research task:

1. Keep a private local trace journal and explicit export command. Cloud shipping is off until explicitly configured with a rotated write key and a nonempty project identifier.
2. Export fixed event names, opaque operation IDs, parent/child relationships, approved release/model/provider identity, integer counts/durations, phase/outcome enums, and safe error codes. Omit prompts, responses, source text/URLs, queries, tool arguments/results, headers, paths, arbitrary metadata, exception strings, and credential-derived identifiers by default.
3. Cover retrieval, capture/replay validation, evidence selection, research/critic/editor roles, candidate evaluation, budget admission, managed session lifecycle, and publication decisions at the harness boundary. Label missing provider internals explicitly. A trace cannot prove reasoning quality or replace an evaluation receipt.
4. Keep transport separate: fixed HTTPS cloud destination, verified TLS, no redirects or ambient proxies, bounded body/response/deadline, one POST attempt, and strict acknowledgement parsing. A response or exception must never be echoed raw. A failed export must not retry research/model/publication work.
5. Represent delivery as accepted, partial, rejected, or unknown. Keep request identity stable for operator reconciliation; do not promise exactly-once ingestion or assume provider deduplication. A later retry policy needs an explicit telemetry-only duplicate tolerance.
6. Test payload rejection before I/O, invalid configuration, nested content/secret-shaped attributes, response truncation and size limits, malformed JSON, partial success, HTTP errors, redirects, TLS/network failure, and deadline expiry. Fault-test that exporter failures cannot change completed research outcomes or release a reservation.
7. If Workshop is wanted later, separately approve a pinned installation and machine/global configuration changes. Run it with a minimal environment, loopback-only access, and no provider secrets. Validate its count-based acknowledgement separately; do not activate replay or self-healing features implicitly.

## Bounded exporter implementation follow-up

The separate `researcher/service/trace_export.py` adapter now implements `export_payload(payload, *, credential, project_id, transport=None)`. It calls the harness's closed `tracing.validate_otlp` contract before any transport and revalidates the serialized payload in its isolated child. Production requests use a fixed cloud destination, a ten-second subprocess wall deadline, no environment-derived proxies or credentials, one POST, and a 65,536-byte acknowledgement limit. Credential material travels to the child on stdin, never command-line arguments. These are implementation facts, not provider guarantees.

Its receipt reports only schema/status, whether dispatch was attempted, sent/rejected span counts, a warning flag, and a fixed error code. It does not include remote error text, headers, prompts, or URLs. HTTP 4xx is rejected; redirects, unexpected statuses, malformed responses, transport errors and timeouts are unknown. Partial acknowledgements never trigger retry. A successful acknowledgement means accepted ingestion, not independently verified dashboard persistence. `default` is deliberately refused; explicit project slugs follow the documented 63-character lower-case alphanumeric/hyphen grammar. New uncreated slugs can accept data without making it visible in the dashboard until the project is created, so operators should choose an existing active project. [Project contract](https://www.raindrop.ai/docs/platform/projects/)

Offline tests cover valid/invalid metadata, credential reflection, project grammar, exact request shape, partial/warning/invalid acknowledgements, framing, size/deadline limits, non-retry behavior, safe worker errors and actual subprocess rejection of a foreign origin before networking. No cloud upload or local Workshop canary has run. Journal admission/resume, CLI wiring, and operation instrumentation are separate parent-owned changes and are not certified by the transport tests.

## Sources

- [Raindrop documentation index](https://www.raindrop.ai/docs/llms.txt)
- [Cloud OTLP/HTTP](https://www.raindrop.ai/docs/sdk/opentelemetry/)
- [HTTP event ingestion](https://www.raindrop.ai/docs/sdk/http-api/)
- [Python SDK](https://www.raindrop.ai/docs/sdk/python/)
- [Managed OpenAI Agents API integration](https://www.raindrop.ai/docs/integrations/openai-managed-agents.md)
- [Workshop overview](https://www.raindrop.ai/docs/workshop/overview/)
- [Pinned Workshop repository](https://github.com/raindrop-ai/workshop/tree/a6b82d71596cf7e8974e5efae63f9e15260d76ef)
- [PII redaction](https://www.raindrop.ai/docs/security/pii-redaction/)
- [Data security and privacy](https://www.raindrop.ai/docs/security/data-security-and-privacy/)
- [Hosted MCP](https://www.raindrop.ai/docs/mcp/overview/)
- [Project identifiers and ingestion behavior](https://www.raindrop.ai/docs/platform/projects/)
- [OTLP wire specification](https://opentelemetry.io/docs/specs/otlp/)

Public documentation/source access occurred on 2026-09-29. No live collector or cloud acknowledgement was observed. This note does not certify SDK binaries, provider retention, production availability, delivery guarantees, or end-to-end integration.
