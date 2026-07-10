# 002 - Context compression handoff

## Hypothesis

The `context-compression` skill should improve preservation of exact identifiers and artifact state when converting a noisy long session into a bounded durable handoff. The irrelevant-skill condition should behave like control.

## Setup

`starting/history.md` contains 1,200 synthetic turns. Twelve durable facts are distributed across the session among repetitive trace entries.

## Deterministic grading

`verify.sh` requires:

1. a `HANDOFF.md` no larger than 2,500 bytes;
2. explicit sections for intent, artifacts, decisions, state, risks/constraints, and next actions;
3. exact preservation of the error code, function, event ID, file paths, test counts, lock decision, charge count, approval constraint, and canary region;
4. the source history to remain unchanged.

This is a preliminary single-task fixture. A valid effectiveness claim still requires at least three replications and additional held-out tasks.
