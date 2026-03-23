---
name: skill-template
description: Template for creating new Agent Skills for context engineering. Use this template when adding new skills to the collection.
---

# Skill Name

Provide a clear, concise description of what this skill covers and when to use it. This description appears in skill discovery and should help agents (and humans) determine when this skill is relevant.

**Important**: Keep the total SKILL.md body under 500 lines for optimal performance. Move detailed reference material to separate files in the `references/` directory.

## When to Activate

Describe specific situations, tasks, or contexts where this skill should be activated. Include both direct triggers (specific keywords or task types) and indirect signals (broader patterns that indicate skill relevance).

Write in third person. The description is injected into the system prompt, and inconsistent point-of-view can cause discovery problems.

- Good: "Processes Excel files and generates reports"
- Avoid: "I can help you process Excel files"

## Core Concepts

Explain the fundamental concepts covered by this skill. These are the mental models, principles, or frameworks that the skill teaches.

Default assumption: Claude is already very smart. Only add context Claude does not already have. Challenge each piece of information:
- "Does Claude really need this explanation?"
- "Can I assume Claude knows this?"
- "Does this paragraph justify its token cost?"

## Detailed Topics

### Topic 1

Provide detailed explanation of the first major topic. Include specific techniques, patterns, or approaches. Use examples to illustrate concepts.

### Topic 2

Provide detailed explanation of the second major topic. Continue with additional topics as needed.

For longer topics, consider moving content to `references/` and linking:
- See [detailed reference](./references/topic-details.md) for complete implementation

## Practical Guidance

Provide actionable guidance for applying the skill. Include common patterns, anti-patterns to avoid, and decision frameworks for choosing between approaches.

Match the level of specificity to the task's fragility:
- **High freedom**: Multiple approaches are valid, decisions depend on context
- **Medium freedom**: Preferred pattern exists, some variation acceptable
- **Low freedom**: Operations are fragile, specific sequence must be followed

## Examples

Provide concrete examples that illustrate skill application. Examples should show before/after comparisons, demonstrate correct usage, or show how to handle edge cases.

Use input/output pairs for clarity:

**Example:**
```
Input: [describe input]
Output: [show expected output]
```

## Guidelines

List specific guidelines to follow when applying this skill. These should be actionable rules that can be checked or verified.

1. Guideline one with specific, verifiable criteria
2. Guideline two with clear success conditions
3. Continue as needed

## Gotchas

List experience-derived failure modes, common mistakes, and counterintuitive behaviors. These are the highest-signal content in any skill. Each gotcha should be specific, actionable, and non-overlapping with guidance already in the skill body. Use numbered format:

1. **Short descriptive title**: One to two sentences explaining what goes wrong and how to prevent it.
2. **Another gotcha title**: Description of the failure mode and what to do instead.

## Integration

Explain how this skill integrates with other skills in the collection. List related skills as plain text (not links) to avoid cross-directory reference issues:

- skill-name-one - Brief description of relationship
- skill-name-two - Brief description of relationship

## References

Internal reference (use relative path to skill's own reference files):
- [Reference Name](./references/reference-file.md) - Description

Related skills in this collection:
- skill-name - Relationship description

External resources:
- Research papers, documentation, or guides

---

## Skill Metadata

**Created**: [Date]
**Last Updated**: [Date]
**Author**: [Author or Attribution]
**Version**: [Version number]

