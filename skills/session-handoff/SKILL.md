---
name: session-handoff
description: >
  Persists task progress across AI sessions via structured JSON records and a state machine.
  Use when the user asks to "hand off work to the next session", "resume where the last
  session left off", "persist in-progress context across sessions", "track change state
  across conversations", or when a long-running task risks spanning multiple AI sessions
  and context must survive session boundaries. Provides init/create/update/status/resume
  workflows with append-only revision history and an enforced lifecycle state machine.
---

# Session Handoff

A context-engineering skill that solves a specific problem: when an AI session ends mid-task (context expires, conversation abandoned, or wall-clock limits hit), the next session starts blind. This skill persists structured task context to the filesystem so the next agent can resume cleanly with full awareness of progress, next steps, blockers, and recent decisions.

## Overview

Most context-engineering approaches focus on keeping context *inside* the current session — summarization, memory stores, retrieval. Session handoff is the complement: when the current session is about to end (or already has), how does the next one pick up without re-reading the entire history?

The answer here is a **Technical Change (TC) record** — a JSON document stored in the project filesystem that captures what's happening *right now*: progress summary, numbered next steps, active blockers, key decisions made, files currently mid-edit, and enough breadcrumbs to resume the exact task. The state machine enforces lifecycle discipline (`planned → in_progress → implemented → tested → deployed`), the append-only revision history preserves full decision context, and each record is self-validating against a schema.

## When to Activate

Activate this skill when:
- The user asks to "hand off" or "save progress for the next session"
- A task is large enough that it may span multiple AI sessions
- The user wants a resumption breadcrumb left on disk for the next agent
- Long-running refactors, migrations, or multi-phase features need structured tracking
- The user asks for `/tc init`, `/tc create`, `/tc update`, `/tc resume`, `/tc status`, or `/tc close`
- Onboarding an existing project and wanting retroactive task documentation

Do NOT activate this skill when:
- The user wants in-session memory (use `memory-systems` instead)
- The user wants to compress conversation history (use `context-compression`)
- The user only wants a changelog from git history
- The change is trivial and won't be touched by a future session

## Storage Layout

Each project stores TCs at `{project_root}/docs/TC/`:

```
docs/TC/
├── tc_config.json          # Project settings
├── tc_registry.json        # Master index + statistics
├── records/
│   └── TC-001-04-05-26-user-auth/
│       └── tc_record.json  # Source of truth
└── evidence/
    └── TC-001/             # Log snippets, command output, screenshots
```

## TC ID Convention

- **Parent TC:** `TC-NNN-MM-DD-YY-functionality-slug` (e.g., `TC-001-04-05-26-user-authentication`)
- **Sub-TC:** `TC-NNN.A` or `TC-NNN.A.1` (letter = revision, digit = sub-revision)
- `NNN` is sequential, `MM-DD-YY` is the creation date, slug is kebab-case.

## State Machine

```
planned -> in_progress -> implemented -> tested -> deployed
   |            |              |           |          |
   +-> blocked -+              +- in_progress <-------+
        |                          (rework / hotfix)
        +-> planned
```

> See [references/lifecycle.md](references/lifecycle.md) for the full transition table and recovery flows.

## Workflow Commands

The skill ships five Python scripts that perform deterministic, stdlib-only operations on TC records. Each one supports `--help` and `--json`.

### 1. Initialize tracking in a project

```bash
python3 scripts/tc_init.py --project "My Project" --root .
```

Creates `docs/TC/`, `docs/TC/records/`, `docs/TC/evidence/`, `tc_config.json`, and `tc_registry.json`. Idempotent — re-running reports "already initialized" with current stats.

### 2. Create a new TC record

```bash
python3 scripts/tc_create.py \
  --root . \
  --name "user-authentication" \
  --title "Add JWT-based user authentication" \
  --scope feature \
  --priority high \
  --summary "Adds JWT login + middleware" \
  --motivation "Required for protected endpoints"
```

Generates the next sequential TC ID, creates the record directory, writes a fully populated `tc_record.json` (status `planned`, R1 creation revision), and updates the registry.

### 3. Update a TC record

```bash
# Status transition (validated against the state machine)
python3 scripts/tc_update.py --root . --tc-id TC-001-04-05-26-user-auth \
  --set-status in_progress --reason "Starting implementation"

# Add a file
python3 scripts/tc_update.py --root . --tc-id TC-001-04-05-26-user-auth \
  --add-file src/auth.py:created

# Append handoff data
python3 scripts/tc_update.py --root . --tc-id TC-001-04-05-26-user-auth \
  --handoff-progress "JWT middleware wired up" \
  --handoff-next "Write integration tests" \
  --handoff-next "Update README"
```

Every change appends a sequential `R<n>` revision entry, refreshes `updated`, and re-validates against the schema before writing atomically (`.tmp` then rename).

### 4. View status

```bash
# Single TC
python3 scripts/tc_status.py --root . --tc-id TC-001-04-05-26-user-auth

# All TCs (registry summary)
python3 scripts/tc_status.py --root . --all --json
```

### 5. Validate a record or registry

```bash
python3 scripts/tc_validator.py --record docs/TC/records/TC-001-.../tc_record.json
python3 scripts/tc_validator.py --registry docs/TC/tc_registry.json
```

Validator enforces the schema, checks state-machine legality, verifies sequential `R<n>` and `T<n>` IDs, and asserts approval consistency (`approved=true` requires `approved_by` and `approved_date`).

> See [references/tc-schema.md](references/tc-schema.md) for the full schema.

## Slash-Command Dispatcher

The repo ships a `/tc` slash command at `commands/tc.md` that dispatches to these scripts based on subcommand:

| Command | Action |
|---------|--------|
| `/tc init` | Run `tc_init.py` for the current project |
| `/tc create <name>` | Prompt for fields, run `tc_create.py` |
| `/tc update <tc-id>` | Apply user-described changes via `tc_update.py` |
| `/tc status [tc-id]` | Run `tc_status.py` |
| `/tc resume <tc-id>` | Display handoff, archive prior session, start a new one |
| `/tc close <tc-id>` | Transition to `deployed`, set approval |
| `/tc export` | Re-render all derived artifacts |
| `/tc dashboard` | Re-render the registry summary |

The slash command is the user interface; the Python scripts are the engine.

## Session Handoff Format

The handoff block lives at `session_context.handoff` inside each TC and is the single most important field for AI continuity. It contains:

- `progress_summary` — what has been done
- `next_steps` — ordered list of remaining actions
- `blockers` — anything preventing progress
- `key_context` — critical decisions, gotchas, patterns the next bot must know
- `files_in_progress` — files being edited and their state (`editing`, `needs_review`, `partially_done`, `ready`)
- `decisions_made` — architectural decisions with rationale and timestamp

> See [references/handoff-format.md](references/handoff-format.md) for the full structure and fill-out rules.

## Validation Rules (Always Enforced)

1. **State machine** — only valid transitions are allowed.
2. **Sequential IDs** — `revision_history` uses `R1, R2, R3...`; `test_cases` uses `T1, T2, T3...`.
3. **Append-only history** — revision entries are never modified or deleted.
4. **Approval consistency** — `approved=true` requires `approved_by` and `approved_date`.
5. **TC ID format** — must match `TC-NNN-MM-DD-YY-slug`.
6. **Sub-TC ID format** — must match `TC-NNN.A` or `TC-NNN.A.N`.
7. **Atomic writes** — JSON is written to `.tmp` then renamed.
8. **Registry stats** — recomputed on every registry write.

## Non-Blocking Bookkeeping Pattern

TC tracking must NOT interrupt the main workflow.

- **Never stop to update TC records inline.** Keep coding.
- At natural milestones, spawn a background subagent to update the record.
- Surface questions only when genuinely needed ("This work doesn't match any active TC — create one?"), and ask once per session, not per file.
- At session end, write a final handoff block before closing.

## Retroactive Bulk Creation

For onboarding an existing project with undocumented history, build a `retro_changelog.json` (one entry per logical change) and feed it to `tc_create.py` in a loop, or extend the script for batch mode. Group commits by feature, not by file.

## Anti-Patterns

| Anti-pattern | Why it's bad | Do this instead |
|--------------|--------------|-----------------|
| Editing `revision_history` to "fix" a typo | History is append-only — tampering destroys the audit trail | Add a new revision that corrects the field |
| Skipping the state machine ("just set status to deployed") | Bypasses validation and hides skipped phases | Walk through `in_progress -> implemented -> tested -> deployed` |
| Creating one TC per file changed | Fragments related work and explodes the registry | One TC per logical unit (feature, fix, refactor) |
| Updating TC inline between every code edit | Slows the main agent, wastes context | Spawn a background subagent at milestones |
| Marking `approved=true` without `approved_by` | Validator will reject; misleading audit trail | Always set `approved_by` and `approved_date` together |
| Overwriting `tc_record.json` directly with a text editor | Risks corruption mid-write and skips validation | Use `tc_update.py` (atomic write + schema check) |
| Putting secrets in `notes` or evidence | Records are committed to the repo | Reference an env var or external secret store |
| Reusing TC IDs after deletion | Breaks the sequential guarantee and confuses history | Increment forward only — never recycle |
| Letting `next_steps` go stale | Defeats the purpose of handoff | Update on every milestone, even if it's "nothing changed" |

## Cross-References

- `memory-systems` — For *in-session* memory and cross-session knowledge retention via vector stores or knowledge graphs. Session handoff is the complement: it captures *task state* (not knowledge) for explicit resumption. Use both together — memory-systems for what the agent knows, session-handoff for what it was doing.
- `context-compression` — When context itself is getting too long, use compression. When the session is about to *end*, use session-handoff.
- `context-degradation` — Both skills address context loss: degradation mitigates quality loss within a session, session-handoff preserves task state across session boundaries.
- `project-development` — Overall project tracking patterns; session-handoff is the fine-grained per-task variant.

## References in This Skill

- [references/tc-schema.md](references/tc-schema.md) — Full JSON schema for TC records and the registry.
- [references/lifecycle.md](references/lifecycle.md) — State machine, valid transitions, and recovery flows.
- [references/handoff-format.md](references/handoff-format.md) — Session handoff structure and best practices.
