---
name: rendered-ui-finish-gate
description: "This skill should be used when an agent is implementing or reviewing a web or mobile interface and needs to preserve product context through a state matrix, rendered evidence, and deterministic finish checks. It treats the rendered interface as an evaluated artifact rather than trusting source code or a single happy path."
---

# Rendered UI Finish Gate

Use this skill to keep interface work grounded in product context and observable behavior. The unit of review is the rendered interface across its required states, not a component tree that looks plausible in source.

## When to Activate

Activate this skill when:

- Implementing or reviewing a web, mobile, or responsive interface.
- Translating a product brief into interface states and acceptance checks.
- Reviewing a page after implementation and before calling it complete.
- Investigating generic, inconsistent, or visually polished but unusable UI.
- Comparing a rendered result against product references, an established design system, or a design contract.

Do not activate for adjacent work owned by other skills:

- General agent-system evaluation, production monitoring, or LLM quality rubrics: `evaluation`.
- Tool schemas, tool routing, or actionable tool errors: `tool-design`.
- Long-running autonomous loop governance, locked evaluators, or rollback: `harness-engineering`.
- Choosing a web framework or designing a complete LLM project pipeline: `project-development`.

## Core Concepts

### Preserve context as a design contract

Before changing UI, write down the context that source code often omits:

- Product goal and primary user action.
- Platform, viewport, input method, and accessibility assumptions.
- Content hierarchy, tone, and domain-specific terminology.
- Existing tokens, components, layout constraints, and visual references.
- Required states, failure behavior, and what counts as complete.

This contract prevents an agent from substituting a familiar dashboard, card grid, or hero section for the product that was actually requested.

### Evaluate the state space, not the screenshot

A single loaded screen is weak evidence. Model the interface as a state matrix that includes loading, empty, populated, error, permission, validation, success, disabled, focus, hover, pressed, and responsive states where they apply. Mark each state as required, intentionally unsupported, or not applicable. An omitted state is a product decision only when it is explicit.

### Use an evidence ladder

Review in this order:

1. Product contract and state matrix.
2. Source-level deterministic checks.
3. Rendered captures at representative viewports and interaction states.
4. Keyboard and assistive-technology checks.
5. Human review of hierarchy, specificity, and finish quality.

Rendered evidence catches overflow, clipping, awkward wrapping, broken hierarchy, and missing states that source inspection cannot prove. Deterministic checks catch inert controls, missing labels, broken links, token drift, and incomplete state wiring before visual judgment is applied.

### Treat genericity as a diagnosis

Do not call a UI generic because it uses a common component. Diagnose the missing product signal: unclear primary action, invented content, ungrounded visual language, absent edge states, or inconsistent interaction feedback. The repair should restore context, not add decoration.

## Practical Guidance

### Workflow

1. **Extract the contract.** Record the user, goal, primary action, platform constraints, content rules, tokens, references, and explicit non-goals.
2. **Build the state matrix.** List every route or component state. Include state-entry conditions and the expected user action or recovery path.
3. **Define the finish gate.** Choose checks that can fail objectively: required states exist, controls have behavior, names and focus are present, layouts fit target viewports, and no placeholder content remains where real content is required.
4. **Implement the smallest coherent slice.** Keep tokens, components, content, and interaction behavior consistent with the contract. Do not polish an unverified structure.
5. **Render representative evidence.** Capture the primary flow plus the highest-risk states at relevant widths. Inspect the result as a user, not as the author of the source.
6. **Exercise interaction states.** Test keyboard navigation, focus visibility, validation, loading, error recovery, disabled controls, and responsive transitions that apply to the product.
7. **Run the gate.** Record pass, fail, or intentionally unsupported for each criterion. Fix failures or document the explicit product decision before reporting completion.

### Finish-gate checklist

| Area | Pass condition |
| --- | --- |
| Context | The hierarchy and terminology reflect the product contract. |
| States | Required loading, empty, success, error, and permission states are represented. |
| Interaction | Every visible control has a clear action, feedback, and recovery path. |
| Layout | Content remains usable at target widths without clipping or accidental overflow. |
| Accessibility | Names, focus order, focus visibility, contrast, and keyboard paths are checked. |
| System fit | Existing tokens and components are reused unless a documented exception is necessary. |
| Content | Placeholder, invented, or misleading content is removed or explicitly marked. |
| Evidence | The report links each claim of completion to a check or rendered artifact. |

### Decision rules

- If the contract is missing, stop and extract it before choosing a visual direction.
- If a state is unknown, mark it unknown. Do not silently replace it with a success state.
- If source checks pass but the render fails, treat the render as the failure signal.
- If visual polish conflicts with interaction clarity, keep the clearer interaction and record the trade-off.
- If a new pattern is needed, prove the existing system cannot express it before adding a one-off token or component.

## Examples

### Example: vague polish request

Input: `Make the billing page feel more premium.`

Before implementation, turn it into a contract:

```text
User: account owner reviewing plan and invoice status
Primary action: change plan or download an invoice
Required states: loading, no invoices, invoices available, payment failure, permission denied
Constraints: preserve existing billing terminology and token system
Evidence: desktop and narrow viewport, keyboard path to both primary actions
Non-goal: adding decorative sections that do not support billing decisions
```

Then render the invoice-empty, invoice-populated, failure, and permission states. A page that looks polished only in the populated state has not passed the gate.

### Example: source passes, render fails

Input: A component has all required props and unit tests pass, but the narrow viewport clips the primary action.

Output: Mark the layout criterion failed, capture the narrow render, fix the layout or define a documented responsive rule, then rerun the capture. Do not report the component complete because its source structure is correct.

### Example: boundary with agent evaluation

Input: An agent pipeline needs a rubric for factual accuracy and tool efficiency, and one step happens to render a UI.

Output: Use `evaluation` for the pipeline rubric. Activate this skill only for the rendered interface contract, state coverage, and interaction evidence.

## Guidelines

1. Start from product context and required states, not from a preferred component library.
2. Separate evidence from taste. A screenshot can prove clipping or missing content; it cannot by itself prove product fit.
3. Prefer one complete user flow with its edge states over many disconnected polished screens.
4. Keep deterministic checks reproducible and keep human judgments explicit.
5. Report unsupported states and open risks instead of implying coverage.

## Gotchas

1. **Happy-path bias**: The populated state hides missing loading, empty, and failure behavior. Render the state matrix before polishing.
2. **Source confidence**: A clean component tree does not prove usable layout or interaction. Treat rendered evidence as a separate check.
3. **Decoration drift**: Gradients, shadows, and extra cards can make a screen look finished while weakening hierarchy. Fix the missing product signal first.
4. **False reuse**: Reusing a component with the wrong content or state semantics is not system consistency. Verify the contract and behavior, not only the class names.
5. **Unbounded review**: Do not keep polishing without a gate. Define the failure criteria and stop when the required evidence passes.

## Integration

- `evaluation` - Owns agent and pipeline quality measurement; this skill supplies rendered-interface evidence when UI is one evaluated artifact.
- `harness-engineering` - Owns locked evaluators and approval boundaries for autonomous loops; this skill defines the interface-specific artifact checks.
- `project-development` - Owns project fit and pipeline shape; this skill starts after an interface task has been selected.
- `context-fundamentals` - Explains context curation; this skill turns product context into a UI contract and state matrix.
- `context-degradation` - Diagnoses context failure; this skill helps detect when generic UI indicates lost or substituted product context.

## References

Internal reference:

- [Skill template](../../template/SKILL.md) - Required structure and ownership boundaries for skills in this collection.

External resources:

- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/) - Interaction and keyboard behavior patterns.
- [UIZZE anti-ui-slop Skill](https://github.com/uizze/uizze/tree/main/skills/anti-ui-slop) - An open implementation of a product-context and rendered-finish workflow for coding agents.
- [UIZZE](https://uizze.com) - Optional reference library for inspecting real web and iOS interface patterns.

---

## Skill Metadata

**Created**: 2026-08-20
**Last Updated**: 2026-08-20
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 1.0.0
