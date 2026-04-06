---
name: production-orchestrator
description: Production-tested patterns for coordinating 57+ specialized agents with anti-duplication and quality gates
tags: [orchestration, multi-agent, production, quality-gates]
author: milkomida77
source: https://github.com/milkomida77/guardian-agent-prompts
---

# Production Orchestrator Skill

Real-world patterns from running 57 specialized agents across 10,000+ production tasks.

## When to Use

Use this skill when you need to coordinate multiple agents on complex tasks where:
- Tasks overlap and need deduplication
- Quality verification is critical before marking work done
- Agent assignments can go stale and need monitoring

## Core Patterns

### Anti-Duplication Registry

```python
# SQLite-based task registry with similarity matching
# 55% threshold catches near-duplicates without false positives
# 45% threshold triggers warnings for human review

def check_duplicate(new_task, existing_tasks):
    for task in existing_tasks:
        similarity = difflib.SequenceMatcher(None, new_task, task.description).ratio()
        if similarity > 0.55:
            return "CONFLICT"  # Already assigned
        elif similarity > 0.45:
            return "WARNING"   # Needs human review
    return "CLEAR"
```

### 5-Step Quality Gate

Before marking any task "done", verify:

1. **File changed** - `git diff` shows actual modifications
2. **Tests pass** - Test suite is green
3. **No secrets** - No API keys or credentials in diff
4. **Builds** - Project compiles and runs
5. **In scope** - Changes are within assigned scope

Rejection rate: ~8% of unverified "done" claims fail at least one gate.

### Delegation Format

```
[ORCHESTRATOR -> agent-name] TASK: description
SCOPE: files/directories allowed
VERIFICATION: command to prove completion
DEADLINE: timeframe
CONTEXT: relevant memory/decisions from previous tasks
```

### Heartbeat Monitoring

```
Every 30 minutes:
1. List all active assignments
2. Check for stale tasks (no progress in 30+ minutes)
3. Post reminder to assigned agent
4. After 2 reminders with no response, reassign
```

## Guard Rails

- Never re-dispatch same task >2 times/24h without new evidence
- Never claim "done" without file path + verification command
- Never expose credentials in delegation messages
- Always check task registry before starting new work

## Integration

Works with any agent framework that supports task delegation. Designed for Claude Code agents but patterns are framework-agnostic.

Source: [guardian-agent-prompts](https://github.com/milkomida77/guardian-agent-prompts)
