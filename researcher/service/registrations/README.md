# Reviewed provider registrations

These are explicit source contracts for the repo-native service, not Codex MCP
configuration. Merely adding a registration file does not activate a schedule,
give a model tools, or authorize remote writes.

## Parallel `web_fetch`

`parallel-web-fetch.json` contains the exact input/output JSON schemas observed
from the authenticated Parallel Search MCP on 2026-09-29. The selected schema
fingerprint is
`074875a4422f67b357025b12529526584b3c30444237afc09985626a78bd0f70`
(SHA-256 of sorted, compact Python JSON for the pair of schemas). Descriptions
inside those schemas are untrusted provider metadata retained for exact schema
matching, not instructions to the harness.

The endpoint is `https://search.parallel.ai/mcp-oauth`, which requires provider
authentication, unlike the anonymous-capable `/mcp` endpoint. Use the existing
`PARALLEL_API_KEY` as the service credential, not a developer OAuth session.
Only `web_fetch` is registered. No Task MCP, background research task, search
tool, or model callback is implicitly authorized.
[Official authentication and tools](https://docs.parallel.ai/integrations/mcp/search-mcp).

To use it in a reviewed **research-mode** service configuration:

- Insert the registration object in a `mcp_tools` item with
  `credential_env: "PARALLEL_API_KEY"` and an explicit `max_cost_microusd`.
- Add one matching `mcp_reads` item to the intended research schedule.
- For the tested narrow case, use arguments
  `{"urls":["https://www.iana.org/domains/reserved"],"objective":"Identify why these domains are reserved","full_content":false}`
  and a conservative 10,000-micro-USD allowance.
- Reserve twelve source HTTP requests per generic-bridge read. This is a ceiling,
  not measured consumption. The registration caps post-SDK-parsed output at
  32 KiB and the session at sixty seconds.
- Run config validation before activation. Do not use the one-URL cost allowance
  for arbitrary batches: the observed remote schema does not encode every limit
  described in its prose. URL selection and per-read cost remain operator-owned.

Current retrieval-only schedules intentionally reject `mcp_reads`; this file
does not silently change that invariant. Daily retrieval integration and
provider-specific excerpt/provenance normalization require a separate change.
MCP output remains `mcp_observation`, not independently verified primary text.
An excerpt is not the complete source. `full_content` is explicitly false in the
tested invocation. Provider errors, empty results, and returned URLs must still
be checked after schema validation.

Live network use must retain the existing isolated worker, public-endpoint
egress controls, TLS verification and process memory limits. The generic SDK
checks DNS but does not pin the socket address; its output cap is post-parse.
Schema drift fails closed. Do not silently replace this snapshot with a new
`tools/list` result or weaken exact matching to restore availability.

See [the dated verification report](../../../docs/product/connector-verification-2026-09-29.md)
for actual live results and limitations. Offline compatibility is tested by
`test_parallel_registration.py`; it is not evidence of a live session by itself.
