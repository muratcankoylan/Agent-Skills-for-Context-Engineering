# Merge, compact, and verify

Use this reference when an instruction file already exists or a new draft exceeds its budget.

## Semantic reconciliation

Build an inventory of actionable rules rather than merging by heading alone. For each rule, record:

- Scope: root, subtree, tool-specific, or personal/global.
- Evidence: the current source that supports or contradicts it.
- Action: keep, update, move, remove, or confirm.

Rules with different wording but the same effect are duplicates. Keep the clearest, most concrete version. A heading without useful rules does not need to survive.

## Removal criteria

Remove or move content when it is:

- General model knowledge or a role persona.
- A long workflow that does not differ from normal agent behavior.
- Duplicated by a nearer instruction file.
- A detailed tutorial, inventory, status report, roadmap, or change history.
- Contradicted by current manifests, CI, source, or maintained docs.
- Too vague to verify.
- Enforced fully by automation and does not require an agent command.
- Personal or tool-local rather than repository-wide.
- A copy of content owned by another document that will drift when that document changes. Replace it with a conditional link stating when to read it, so the instruction file needs no edit when the owner changes.

Do not preserve stale content in a "legacy" section. Git history already records it.

## Conflict handling

Resolve conflicts from repository evidence where authority is clear. Ask the user only when two plausible sources have different owners or when changing the rule would alter team policy.

Present a compact question containing:

1. The conflicting rule.
2. Each supporting source path.
3. The practical effect of each choice.

Do not dump an entire section diff into the conversation unless the user asks.

## Compaction pass

Compact in this order until the file is within budget:

1. Remove role text, introductions, conclusions, and generic advice.
2. Remove duplicated or automation-enforced rules.
3. Replace documentation summaries with conditional links.
4. Move subtree-specific rules into the nearest supported nested instruction file.
5. Combine related bullets without weakening their concrete conditions.
6. Remove optional sections that contain no repository-specific behavior.

Do not raise an instruction-size setting as a substitute for compaction.

## Recovery

When the file is tracked by Git, use the working-tree diff as the recovery mechanism. Do not create `.backup` files or commits automatically. For an untracked file whose replacement is requested, preserve content needed for recovery in an appropriate local location. State that path; ask only when placement or retention has a material unresolved consequence.

## Verification checklist

Validate the final files, not only the generation process:

- Line count and byte size of each file are within the selected budget.
- Referenced paths exist.
- Commands match current scripts, CI, wrappers, and service names.
- No placeholders, generated comments, task status, prompt transcript, secrets, or local absolute home paths remain.
- Root rules are broadly applicable.
- Nested files contain only scoped differences.
- `AGENTS.override.md` is intentional wherever present.
- Compatibility files are opt-in and use current supported syntax.
- The final diff removes stale guidance rather than only adding content.

Summarize the result as counts or short bullets: kept, updated, moved, removed, and unresolved. Mention any command that could not be verified.
