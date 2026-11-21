---
name: instruction-surface-security
description: "Hardens agent runtimes against persistent prompt injection or unauthorized changes to instructions and permissions. Use to audit what agents auto-load, design reviewed activation for project rules, skills, memory, or tool configuration, and test whether trust boundaries hold after reload, restart, or delegation."
---

# Instruction-Surface Security

A memory entry, configuration edit, or handoff can change what the next agent treats as authoritative. Protect the transition from mutable content to effective instructions or capabilities. Treat text warnings as defense in depth and put enforceable decisions in the runtime.

## When to Activate

- Audit how a coding, research, or multi-agent runtime discovers instructions, memory, skills, tools, or permission policy.
- Design an approval boundary for changes that affect later turns, sessions, workers, or deployment.
- Investigate unexpected instruction drift or check whether a recovery restored the effective runtime state.
- Evaluate containment and legitimate task completion across a reload, restart, or handoff.

Do not activate for general tool design, routine edits with no instruction or privilege boundary, or generic application security. Use `context-degradation` for accidental drift and `self-managed-context` for bounded edits to the model's live context. Use `harness-engineering` for general optimizer and evaluator governance.

## Core Concepts

- **Effective surface.** The inputs the selected runtime actually uses to set instructions, tools, executable behavior, or permissions. Include each source's role, scope, precedence, resolvers or imports, writers, and activation triggers. The same file can be data in one runtime and loaded guidance in another.
- **Write and activation.** A write changes stored state. Activation changes what an agent consumes or can do. Enforce both boundaries. A repository review gates merge and may leave working-copy activation entirely exposed.
- **Integrity and authorization.** A digest identifies content and a verified signature identifies a signer. An independent policy must authorize that principal, revision, target, and effect. A handoff, memory entry, or review note carries evidence and proposals. Any authority it conveys must come from the authenticated delegation envelope and the recipient's own runtime policy.
- **Scope of the evidence.** The Mind Viruses preprint observes persistent instructions and onward transfer in its test harnesses. The prompt warning reduced spread in a bounded experiment, with residual first-hop behavior. Read the [research evidence](references/evidence.md) when interpreting the paper or comparing interventions.

## Practical Guidance

1. **Map one concrete runtime.** Pin build, profile, workspace root, and effective agent role. Trace loaders from startup through resume, directory changes, tool discovery, and delegation where supported. For each authority-bearing input, record who can produce or replace it, what consumes it, when it takes effect, and what blocks an unauthorized change. Mark unknown entries. Use loader diagnostics or inspect the installed implementation from a trusted inspection environment.
2. **Stage proposals as data.** Keep ordinary task outputs and proposals writable. Keep staged changes out of authority-bearing load paths. Workers can still retrieve source-labeled notes or staged proposals through a data-only index. Review candidate text as quoted data. Use a separate restricted preview only when needed. Time in staging grants no authority.
3. **Approve the effective change.** Compare the candidate with the last approved configuration, including differences in scope, capabilities, and imported dependencies. Bind approval to the exact artifact or resolved snapshot, target profile and scope, active base and policy revision, and authorized approver. Use approvals or signatures verified outside the candidate and outside the agent's writable state.
4. **Mediate activation.** Use the runtime, launcher, or an external policy boundary to activate precisely the reviewed inputs. Verify at first use and at each supported change of effective inputs. Keep the files or immutable snapshot used at activation consistent with what was verified. Reject stale or unbound changes. Where the host cannot enforce this, constrain the runtime to an approved input set or report the remaining exposure explicitly.
5. **Verify from outside the model.** Observe what loaded and which capabilities were available, then exercise a bounded behavioral check and an authorized task. A statement of compliance is diagnostic. For an unexpected change, pause affected launches or sensitive actions, preserve relevant evidence, and restore known-good inputs and settings through a trusted path. Verify from a clean session with affected caches and resumed state accounted for.

For an audit, deliver the effective surface map, evidence links, and unresolved paths. For a design, identify the enforcing component, its approval contract, and a recovery path. Use the [runtime review and promotion reference](references/runtime-review.md) for an inventory and approval record or a prompt to use alongside actual controls. Use the [evaluation protocol](references/evaluation.md) for defensive experiments.

## Examples

A formatting preference proposed by a research worker can be kept as a data record and evaluated on a sample document. The parent can continue compiling the report under its existing instructions. Before making the preference a workspace default, a policy-authorized reviewer approves the exact revision and scope, and the next clean session records the revision it loaded.

A project checks approvals before merging rule changes. Its interactive runtime also reads working-copy rules. Record separate boundaries for publishing and local activation, then verify the latter at load time. A successful merge check establishes only the publishing result.

## Guidelines

- Preserve legitimate work under the last approved state when a change is staged or blocked. Return the affected surface, decision, evidence, and next permitted operation.
- Match controls to effects. Protect anything that grants authority or automatically steers future agents. Keep regular scratch memory and task artifacts available as data where their loader and permissions support that distinction.
- Audit delegated work using the recipient's effective permissions. Carry source and scope across the handoff, and require independent authorization for sensitive effects.

## Gotchas

1. **Filename lists miss effective inputs.** Nested rules, resolved imports, plugin state, dynamic tool registration, and resumed context can change what is in force. Observe the actual loader.
2. **Post-start checks arrive late.** A diff or canary can detect a change after admission. Gate the load or capability use before it takes effect.
3. **Approval can outlive its review.** Replacing a path or changing an import, scope, or policy can invalidate approval even when the primary file's bytes match.
4. **A refusal can hide a failure.** The model may report that it refused while a different writer already changed state. Check trusted lifecycle events and state, including recovery and ordinary task completion.

## Integration

Use `harness-engineering` to protect the controller and logs, `multi-agent-patterns` for delegation topology and role allocation, and `evaluation` for deterministic graders and regression coverage. This skill owns the boundary between proposed content and authority during load or use.

## References

- [Runtime review and promotion](references/runtime-review.md)
- [Defensive evaluation protocol](references/evaluation.md)
- [Research evidence and limits](references/evidence.md)
