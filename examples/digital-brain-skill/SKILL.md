---
name: digital-brain
description: "This skill should be used for personal operating-system workflows: content creation, voice consistency, relationship lookup, meeting preparation, weekly review, goal tracking, personal brand management, and network management."
version: 1.0.0
---

# Digital Brain

A structured personal operating system for managing digital presence, knowledge, relationships, and goals with AI assistance. Designed for founders building in public, content creators growing their audience, and tech-savvy professionals seeking AI-assisted personal management.

**Important**: This skill uses progressive disclosure. Module-specific instructions are in each subdirectory's `.md` file. Only load what's needed for the current task.

## When to Activate

Activate this skill when the user:

- Requests content creation (posts, threads, newsletters) - load identity/voice.md first
- Asks for help with personal brand or positioning
- Needs to look up or manage contacts/relationships
- Wants to capture or develop content ideas
- Requests meeting preparation or follow-up
- Asks for weekly reviews or goal tracking
- Needs to save or retrieve bookmarked resources
- Wants to organize research or learning materials

**Trigger phrases**: "write a post", "my voice", "content ideas", "who is [name]", "prepare for meeting", "weekly review", "save this", "my goals"

## Core Concepts

### Progressive Disclosure Architecture

The Digital Brain follows a three-level loading pattern:

| Level | When Loaded | Content |
|-------|-------------|---------|
| **L1: Metadata** | Always | This SKILL.md overview |
| **L2: Module Instructions** | On-demand | `[module]/[MODULE].md` files |
| **L3: Data Files** | As-needed | `.jsonl`, `.yaml`, `.md` data |

### File Format Strategy

Formats chosen for optimal agent parsing:

- **JSONL** (`.jsonl`): Append-only logs - ideas, posts, contacts, interactions
- **YAML** (`.yaml`): Structured configs - goals, values, circles
- **Markdown** (`.md`): Narrative content - voice, brand, calendar, todos
- **XML** (`.xml`): Complex prompts - content generation templates

### Append-Only Data Integrity

JSONL files are **append-only**. Never delete entries:
- Mark as `"status": "archived"` instead of deleting
- Preserves history for pattern analysis
- Enables "what worked" retrospectives

## Detailed Topics

### Module Overview

```
digital-brain/
├── identity/     → Voice, brand, values (READ FIRST for content)
├── content/      → Ideas, drafts, posts, calendar
├── knowledge/    → Bookmarks, research, learning
├── network/      → Contacts, interactions, intros
├── operations/   → Todos, goals, meetings, metrics
└── agents/       → Automation scripts
```

### Identity Module (Critical for Content)

**Always read `identity/voice.md` before generating any content.**

Contains:
- `voice.md` - Tone, style, vocabulary, patterns
- `brand.md` - Positioning, audience, content pillars
- `values.yaml` - Core beliefs and principles
- `bio-variants.md` - Platform-specific bios
- `prompts/` - Reusable generation templates

### Content Module

Pipeline: `ideas.jsonl` → `drafts/` → `posts.jsonl`

- Capture ideas immediately to `ideas.jsonl`
- Develop in `drafts/` using `templates/`
- Log published content to `posts.jsonl` with metrics
- Plan in `calendar.md`

### Network Module

Personal CRM with relationship tiers:
- `inner` - Weekly touchpoints
- `active` - Bi-weekly touchpoints
- `network` - Monthly touchpoints
- `dormant` - Quarterly reactivation checks

### Operations Module

Productivity system with priority levels:
- P0: Do today, blocking
- P1: This week, important
- P2: This month, valuable
- P3: Backlog, nice to have

## Practical Guidance

### Content Creation Workflow

```
1. Read identity/voice.md (REQUIRED)
2. Check identity/brand.md for topic alignment
3. Reference content/posts.jsonl for successful patterns
4. Use content/templates/ as starting structure
5. Draft matching voice attributes
6. Log to posts.jsonl after publishing
```

### Pre-Meeting Preparation

```
1. Look up contact: network/contacts.jsonl
2. Get history: network/interactions.jsonl
3. Check pending: operations/todos.md
4. Generate brief with context
```

### Weekly Review Process

```
1. Run: python agents/scripts/weekly_review.py
2. Review metrics in operations/metrics.jsonl
3. Check stale contacts: agents/scripts/stale_contacts.py
4. Update goals progress in operations/goals.yaml
5. Plan next week in content/calendar.md
```

## Examples

### Example: Writing an X Post

**Input**: "Help me write a post about AI agents"

**Process**:
1. Read `identity/voice.md` → Extract voice attributes
2. Check `identity/brand.md` → Confirm "ai_agents" is a content pillar
3. Reference `content/posts.jsonl` → Find similar successful posts
4. Draft post matching voice patterns
5. Suggest adding to `content/ideas.jsonl` if not publishing immediately

**Output**: Post draft in user's authentic voice with platform-appropriate format.

### Example: Contact Lookup

**Input**: "Prepare me for my call with Sarah Chen"

**Process**:
1. Search `network/contacts.jsonl` for "Sarah Chen"
2. Get recent entries from `network/interactions.jsonl`
3. Check `operations/todos.md` for pending items with Sarah
4. Compile brief: role, context, last discussed, follow-ups

**Output**: Pre-meeting brief with relationship context.

## Guidelines

1. **Voice First**: Always read `identity/voice.md` before any content generation
2. **Append Only**: Never delete from JSONL files - archive instead
3. **Update Timestamps**: Set `updated` field when modifying tracked data
4. **Cross-Reference**: Knowledge informs content, network informs operations
5. **Log Interactions**: Always log meetings/calls to `interactions.jsonl`
6. **Preserve History**: Past content in `posts.jsonl` informs future performance

## Integration

This skill integrates context engineering principles:

- **context-fundamentals** - Progressive disclosure, attention budget management
- **memory-systems** - JSONL for persistent memory, structured recall
- **tool-design** - Scripts in `agents/scripts/` follow tool design principles
- **context-optimization** - Module separation prevents context bloat

## References

Internal references:
- [Identity Module](./identity/IDENTITY.md) - Voice and brand details
- [Content Module](./content/CONTENT.md) - Content pipeline docs
- [Network Module](./network/NETWORK.md) - CRM documentation
- [Operations Module](./operations/OPERATIONS.md) - Productivity system
- [Agent Scripts](./agents/AGENTS.md) - Automation documentation

External resources:
- [Agent Skills for Context Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering)
- [Anthropic Context Engineering Guide](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

## Skill Metadata

**Created**: 2024-12-29
**Last Updated**: 2024-12-29
**Author**: Murat Can Koylan
**Version**: 1.0.0
