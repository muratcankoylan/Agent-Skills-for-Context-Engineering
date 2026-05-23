---
name: context-receipts
description: This skill should be used when designing privacy-safe receipts, traces, or audit events that prove which instructions, retrieved memories, skills, tools, compactions, or security findings entered or transformed an agent's context without exposing raw private content.
---

# Context Receipts

Context receipts are small, shareable evidence records for agent context operations. They answer: what was eligible, what was selected, what was suppressed, what changed, and what was intentionally not logged. Use them when teams need to debug or audit context behavior without pasting prompts, tool outputs, secrets, or memory bodies into logs.

## When to Activate

Activate this skill when:
- Proving which project instructions, rules, skills, memories, retrieved documents, or tool definitions entered an agent session
- Debugging lazy context loading, MCP Tool Search, deferred skill loading, skill registry reads, or duplicate context loading
- Auditing compaction, tool-result clearing, summarization, memory consolidation, self-distilled skill reuse, or objective continuity
- Sharing evidence about memory retrieval, writes, forget/delete actions, or security scans without exposing raw content
- Designing OpenTelemetry spans, JSON logs, or bug-report artifacts for context operations

Do not activate this skill for adjacent work owned by other skills:
- Reducing token cost without an audit requirement: `context-optimization`.
- Writing the summary or compaction policy itself: `context-compression`.
- Designing persistent memory architecture: `memory-systems`.
- Designing general evaluation suites or rubrics: `evaluation`.
- Designing tool schemas and tool descriptions: `tool-design`.

## Core Concepts

A receipt is not a transcript. It is a redacted proof envelope around a context operation.

### Receipt Boundaries

Model every receipt around a narrow operation:

- **Input selection**: instruction file loaded, retrieved memory selected, skill invoked, tool definition expanded
- **Input suppression**: candidate existed but did not enter context because of target agent, path scope, duplicate detection, budget, or policy
- **Transformation**: compaction, summarization, consolidation, tool-result clearing, objective handoff
- **Sensitive workflow**: secret scanning, governance delete, permission check, policy bypass evaluation

Each receipt should make the operation auditable without making private content recoverable from the receipt alone.

### Minimal Event Shape

Use stable event names and compact fields:

```json
{
  "event": "context.input.loaded",
  "session_id": "sess_redacted",
  "source": {"kind": "file", "uri_hash": "sha256:..."},
  "target": {"agent": "cursor", "surface": "rules"},
  "decision": "loaded",
  "reason": "path_scope_match",
  "content_hash": "sha256:...",
  "raw_content_logged": false
}
```

Prefer explicit booleans such as `raw_content_logged: false`, `secret_logged: false`, and `memory_body_logged: false` over vague privacy claims.

### Correlation Over Content

Receipts become useful when they correlate across systems:

- Memory server: `memory.search.returned`
- Agent harness: `context.input.loaded`
- Skill router: `context.skill.invoked`
- Tool layer: `mcp.tool_definition.loaded`
- Compactor: `context.compaction.completed`

Correlate with run IDs, source IDs, content hashes, policy names, and decision reasons. Do not correlate with raw prompts or raw memory text.

### Hashes and Redaction

Hashes prove sameness, not safety. Hash only content that is already protected elsewhere, and treat hashes as metadata that can still leak information through correlation. For high-risk content, use salted or scoped hashes, short-lived IDs, or opaque references stored in a private audit system.

## Practical Guidance

### Receipt Design Workflow

1. Name the operation: loaded, suppressed, searched, expanded, compacted, deleted, scanned, verified.
2. Identify who needs the receipt: user debugging a failed handoff, maintainer reviewing a bug, compliance reviewer, or agent developer.
3. Separate private content from evidence fields.
4. Record the decision, reason, source kind, target surface, policy, hashes or opaque IDs, and audit gaps.
5. Add explicit negative guarantees: raw prompt not logged, secret not logged, memory body not logged.
6. Map the receipt to JSON logs first; add OpenTelemetry spans only after the fields are stable.
7. Test with synthetic private strings and fail if any appear in exported receipts.

### Common Receipt Types

| Operation | Event names | Evidence to keep | Content to avoid |
|---|---|---|---|
| Instruction load | `context.input.loaded`, `context.input.suppressed` | source kind, target agent, load order, reason, hash | raw instruction body |
| Lazy tool loading | `mcp.tool_index.loaded`, `mcp.tool_definition.loaded` | server ID, tool ID, token bucket, selection reason | tool args, results, private descriptions |
| Skill registry lifecycle | `context.skill.registry.index.loaded`, `context.skill.registry.skill.read`, `context.skill.registry.skill.injected` | registry ID, skill ID hash, index/body state, reuse count bucket, injection reason | raw skill body, private file path, incident notes |
| Memory retrieval | `memory.search.returned`, `context.input.loaded` | query hash, memory IDs, scores or buckets, loaded IDs | raw query, memory body |
| Compaction | `context.compaction.completed` | trigger, preserved item IDs, before/after objective hash, audit gaps | summary body, transcript text |
| Governance delete | `memory.governance.delete.completed` | candidates, confirmation ID, tombstone IDs, replay result | deleted memory content |
| Secret scanning | `security.secret_scanning.completed` | detector type, redacted finding ID, policy decision, clean rescan | secret value, private path, raw patch |

### Bug Report Template

Ask for receipts before asking for private context:

```markdown
## Context receipt bundle
- session_id:
- operation that failed:
- receipt event names included:
- expected loaded/suppressed IDs:
- actual loaded/suppressed IDs:
- raw_content_logged flags all false? yes/no
- audit gaps reported by the receipt:
```

### Leak Test

Create a synthetic fixture with fake private strings, then assert the exported receipt does not include them:

```python
private_strings = ["customer-name", "fake-secret-token", "private-path"]
receipt = export_context_receipt(fixture)
for value in private_strings:
    assert value not in receipt
```

## Examples

**Example: AGENTS overlay receipt**

```json
{"event":"context.input.loaded","source_role":"base","target_agent":"cursor","load_order":1,"content_hash":"sha256:base"}
{"event":"context.input.loaded","source_role":"overlay","target_agent":"cursor","load_order":2,"content_hash":"sha256:cursor"}
{"event":"context.input.suppressed","source_role":"overlay","target_agent":"codex","reason":"target_agent_mismatch"}
```

**Example: Lazy MCP receipt**

```json
{"event":"mcp.tool_index.loaded","server_id":"github","definition_mode":"index_only"}
{"event":"mcp.tool_search.performed","query_hash":"sha256:query","selected_tool_id":"issues.list"}
{"event":"mcp.tool_definition.loaded","tool_id":"issues.list","definition_hash":"sha256:def"}
```

**Example: Self-distilled skill registry receipt**

```json
{"event":"context.skill.registry.index.loaded","registry_id":"skill-registry","skill_count":24,"raw_skill_bodies_logged":false}
{"event":"context.skill.registry.skill.read","skill_id_hash":"sha256:skill","body_hash":"sha256:body","reason":"task_match"}
{"event":"context.skill.registry.skill.injected","skill_id_hash":"sha256:skill","target_surface":"agent_context","token_bucket":"1k_2k"}
{"event":"context.skill.registry.reuse.evaluated","skill_id_hash":"sha256:skill","reuse_count_bucket":"2_5","decision_relevance":"supporting"}
```

Use this pattern when a runtime stores or self-distills skills, injects an index, and reads full skill bodies on demand. The receipt should distinguish index-only exposure from full-body injection; otherwise a bug report cannot tell whether a skill was merely available or actually entered context.

**Example: Compaction receipt**

```json
{"event":"context.compaction.completed","trigger":"budget_pressure","preserved_objective_hash":"sha256:goal","raw_transcript_logged":false,"audit_gaps":["summary_quality_not_machine_verified"]}
```

## Guidelines

1. Make the receipt answer a concrete audit question, not every question.
2. Keep raw context, memory bodies, tool outputs, and secrets out of exported receipts.
3. Prefer decision reasons and content hashes over natural-language summaries.
4. Record suppressions as first-class events; missing context is often the bug.
5. Include policy names and version IDs when policy made the decision.
6. Emit JSONL for local debugging and OpenTelemetry spans for production correlation.
7. Add automated leak tests with synthetic private strings before publishing examples.
8. Treat receipts as product surfaces: stable names, stable fields, and clear backward compatibility.

## Gotchas

1. **A hash can become a tracking identifier**: Stable hashes across runs can reveal that the same private content appeared in multiple sessions. Use scoped hashes or opaque IDs when correlation itself is sensitive.

2. **Receipts can launder secrets through metadata**: File paths, branch names, detector messages, tool names, and memory titles may contain private customer or incident details even when the main body is redacted.

3. **Suppression events are easy to omit**: If receipts only show loaded context, users cannot distinguish “not discovered” from “discovered and intentionally skipped.” Always log policy suppressions.

4. **Compaction receipts can imply quality they did not verify**: A completed compaction event proves the operation ran, not that the summary preserved every objective. Include audit gaps explicitly.

5. **Skill indexes are not skill bodies**: A registry index may be safe to expose broadly while a full skill body contains private rationale, incident notes, or paths. Log index load, body read, body injection, and reuse/accounting as separate events.

6. **Debug logs become API contracts**: Once users attach receipts to issues, field names become hard to change. Version event schemas before broad adoption.

## Integration

Use this skill with:

- `context-optimization` when budget tactics need proof of what stayed out of context.
- `context-compression` when compaction needs objective-continuity evidence.
- `memory-systems` when retrieval, write, consolidation, or forget flows need redacted audit trails.
- `tool-design` when tools should emit receipt-friendly JSON responses or actionable errors.
- `evaluation` when receipts become inputs to regression tests or quality gates.
- `harness-engineering` when autonomous loops need durable, append-only evidence.

## References

Internal skills in this collection:
- [context-optimization](../context-optimization/SKILL.md) - Read when: reducing context cost or deciding when to mask, compact, or partition.
- [context-compression](../context-compression/SKILL.md) - Read when: designing the compaction or handoff summary that a receipt will audit.
- [memory-systems](../memory-systems/SKILL.md) - Read when: designing memory write/search/delete semantics.
- [tool-design](../tool-design/SKILL.md) - Read when: making tools emit receipt-friendly structured outputs.
- [evaluation](../evaluation/SKILL.md) - Read when: turning receipts into deterministic tests or regression gates.

External resources:
- OpenTelemetry semantic conventions - Read when: mapping receipt events into spans and attributes.
- Agent platform documentation for tool search, skills, and memory - Read when: aligning event names to a specific runtime.

---

## Skill Metadata

**Created**: 2026-05-22
**Last Updated**: 2026-05-23
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 1.0.0
