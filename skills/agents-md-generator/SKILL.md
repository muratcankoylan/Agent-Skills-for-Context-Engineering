---
name: agents-md-generator
description: "Creates, audits, and compacts repository instruction files (AGENTS.md, scoped overrides, requested tool compatibility files) for any language or stack. Use when a repository needs agent instructions that stay valid without hand edits by routing to existing sources of truth instead of copying their content. Do not use for writing project documentation, designing tool schemas, or general prompt engineering: those belong to the owning docs, tool-design, and context-fundamentals."
---

# AGENTS.md Generator

Produces a small, stable instruction layer containing verified project facts that materially change agent behavior. The file is a router: it states durable rules and points to the place where each kind of knowledge lives. Procedures, examples, troubleshooting, and architecture stay in their own documents, so the instruction file does not need editing when those documents change.

The skill is stack-agnostic. It assumes nothing about language, framework, or tooling; every fact comes from repository evidence or the user.

## When to Activate

Activate when the work is about the repository instruction layer:

- Creating `AGENTS.md` (or a requested equivalent) for a repository that has none.
- Auditing, deduplicating, or compacting an existing instruction file that grew stale or too long.
- Reconciling instructions spread across several tools or nested scopes.
- Adding scoped overrides or compatibility files for a tool the team actually uses.

Do not activate for adjacent work:

- Writing the procedures, architecture notes, runbooks, or troubleshooting guides the file links to: the repository's own documentation.
- Designing tool descriptions and schemas for agents: `tool-design`.
- Deciding what belongs in a model's context window in general: `context-fundamentals`.
- Shaping an LLM project or pipeline: `project-development`.
- Editing global user configuration: outside a repository-instruction task.

## Core Concepts

**Router, not repository.** An instruction file holds only what an agent must know before acting and cannot cheaply discover: exact command runners, generated-file ownership, unusual boundaries, required checks, approval constraints. Everything else is a conditional link ("For schema changes, read `<path>` before editing migrations").

**Edit-free by construction.** Content that changes with the code (step lists, examples, error catalogs, inventories) is the content that forces edits. Keeping it out of the file, and linking to its owner, is what keeps the file stable. A rule that automation already enforces does not need to be restated.

**Evidence over assumption.** Persist a fact only when a current source supports it, in this priority: active instructions and user requirements, CI and executable scripts, manifests and lockfiles, maintained docs, representative code, user confirmation. Facts that cannot be verified are omitted or asked about; they are never inferred from framework defaults or folder names.

**Smallest effective instruction chain.** One compact shared file by default. Nested files carry only the delta for a real scope difference. Compatibility files exist only for tools the team uses.

## Practical Guidance

### 1. Discover the instruction chain

Inspect existing instructions, their ownership, scopes, and symlinks before editing. Preserve a working shared source such as `AGENTS.md` pointing to `CLAUDE.md`; do not replace it solely to impose a preferred filename. Keep global user configuration outside the task.

For an unfamiliar or multi-tool repository, the bundled detector indexes instruction paths and declared framework and tool signals:

```text
python3 <skill-directory>/scripts/detect-agent-context.py --root <repository-root> --format json
```

The Python script is the reference implementation and the only one that provides JSON. Resolve scripts relative to this skill, not the target project. If Python is unavailable, inspect the files directly. For a known, narrow edit, direct inspection is enough.

The detector reads manifests and instruction paths only; it never reads credentials, environment files, or instruction contents. Treat its output as an index: read the applicable instructions and verify each command in its source before persisting it.

See [discovery.md](./references/discovery.md) for detector fields and the evidence checklist, and [tool-compatibility.md](./references/tool-compatibility.md) when loading order or tool support affects the layout.

### 2. Select durable rules

Keep a rule when it is non-obvious, supported by evidence, useful across tasks, and concrete enough to follow. Remove or rewrite generic advice, personas, duplicated rules, obsolete commands, exhaustive inventories, and unsupported scores.

| Content | Goes in the instruction file | Goes elsewhere |
|---------|------------------------------|----------------|
| Command runner, wrapper, required order | Yes, if non-obvious | Obvious manifest scripts stay out |
| Generated or protected paths | Yes, with the generator command | |
| Approval and safety boundaries | Yes, as they actually exist | |
| Step-by-step procedures, examples | Link only | Existing docs |
| Troubleshooting, design, API detail | Link only | Existing docs |
| Secrets, home paths, task logs | Never | |

Describe actual authorization boundaries; do not invent approval gates or weaken explicit ones.

### 3. Write or reconcile

Classify existing content as keep, update, move, remove, or unresolved; resolve facts from source and ask only about conflicts that need a team decision. Use [output-template.md](./references/output-template.md) as a menu and [merge-and-verify.md](./references/merge-and-verify.md) for consolidating an existing file.

Size: roughly 80-150 lines for a root file, shorter for scoped files, without padding to a target. Review a root file that has grown well past that range for duplication and misplaced detail. Do not raise a tool's context limit to avoid editing.

Recovery: use tracked diffs. Preserve untracked content that would otherwise be lost. Do not create routine backup copies, alter history, or ignore whole tool-configuration directories.

### 4. Verify

Check cited paths and commands, scope and precedence, symlinks, duplicate rules, and leftover placeholders. Measure line and byte size and confirm the whole chain fits the target tool. Run repository validators when they exist. Static inspection of a command does not mean it ran; never run a destructive command to confirm its spelling.

Report the material rules kept, changed, moved, or removed, the evidence used, and unresolved conflicts. Skip a separate discovery report unless requested.

## Examples

**Example: bloated file, compaction**

```
Input:  Root AGENTS.md of 340 lines: a role persona, a test tutorial, a
        copy of the API guide, two commands that no longer exist.
Output: 60 lines. Persona and tutorial removed, API guide replaced by
        "For endpoint changes, read docs/api.md", stale commands dropped
        after checking CI.
```

More cases (scoped file, preserved shared source, unverifiable command) are in [examples.md](./references/examples.md); a filled TypeScript root file is in [output-template.md](./references/output-template.md).

## Guidelines

1. Every command in the file traces to a manifest, script, wrapper, or CI job.
2. Every link points to an existing path with a stated read condition.
3. No rule restates what automation enforces or what a docs file already owns.
4. Nested files contain only differences from their parent.
5. Compatibility files are created only on request or on detected tool usage.
6. The final diff removes stale guidance instead of only adding text.
7. No secrets, absolute home paths, task status, or prompt transcripts remain.

## Gotchas

1. **Detector output treated as verified**: The index shows that a script exists, not that its wrapper, service name, or CI usage match. Confirm each command in its source.
2. **Copying a docs summary "for convenience"**: The copy drifts and brings back the editing burden. Link with a read condition instead.
3. **Replacing a working symlink or import**: Forcing a preferred filename breaks tools already reading the shared source. Preserve it unless asked.
4. **Same-directory override surprises**: Where a tool supports an override file, it can silently hide the regular file in that directory. Check precedence before proposing a layout.
5. **Inventing approval gates**: Adding "ask before X" rules the team never had changes policy. Persist only boundaries that exist.
6. **Duplicating rules across tool-specific files**: Always-loaded copies multiply cost and diverge. Share one source and import it.
7. **Raising a size limit instead of compacting**: Larger limits hide duplication and dilute the rules that matter.
8. **Running a command to verify its spelling**: A destructive target can do harm. Verify statically and say it was not executed.

## Integration

- context-fundamentals - Explains why always-loaded instructions must stay small and high-signal.
- context-optimization - Related token-cost discipline for content that loads on every session.
- filesystem-context - Supports the pattern of keeping detail in files loaded on demand.
- harness-engineering - Covers locked versus editable surfaces when instructions guard an agent loop.
- tool-design - Owns tool schema and description work that this skill does not cover.
- project-development - Owns pipeline and project-shape decisions that inform what the repository needs.

## References

Internal references:
- [Discovery](./references/discovery.md) - Read when: scanning an unfamiliar repository or interpreting detector fields.
- [Output template](./references/output-template.md) - Read when: choosing sections for a new root, nested, or compatibility file.
- [Examples](./references/examples.md) - Read when: a compaction, scoped-file, shared-source, or unverifiable-command case needs a concrete pattern.
- [Merge and verify](./references/merge-and-verify.md) - Read when: consolidating an existing file or running the final checklist.
- [Tool compatibility](./references/tool-compatibility.md) - Read when: more than one coding agent or precedence rules affect the layout.

Related skills in this collection:
- context-fundamentals - Read when: justifying why the instruction layer must stay minimal.
- tool-design - Read when: the task is about tool descriptions, not repository instructions.

---

## Skill Metadata

**Created**: 2026-10-23
**Last Updated**: 2026-10-23
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 1.0.0
