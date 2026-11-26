---
name: self-managed-context
description: "This skill should be used when a model gets read-write control over its own live context window instead of a harness-scheduled compaction policy: the context exposed as an editable file the model rewrites with code tools, model-driven eviction and in-place updates, the harness invariants that keep self-editing safe (pinned prefix, edit gate, edit receipts, budget readouts, rollback on overflow), the prefix-cache cost of mid-context edits, and steering or training the model's own context-editing strategy. Route note content and fixed-threshold summarization to context-compression, cache-stable layout under harness control to context-optimization, file offloading to filesystem-context, and loop governance to self-improvement-loops."
---

# Self-Managed Context

This skill covers agents that manage their own context window: the model, not the harness, decides what stays in the live context, what is compacted, what is evicted, and what is rewritten in place. The reference implementation is Context Language Models (CLMs), which mirror the editable part of the conversation into a file that the model edits with ordinary code tools, then re-parse that file into the next prompt. Applied zero-shot to existing models on a shared agent backbone, this matched or beat harness-scheduled and action-based context management on accuracy and compute across deep-research, terminal-coding, and multi-hour repository-optimization tasks (claim-self-managed-context-zero-shot-results, claim-self-managed-context-long-horizon-results).

The controlling trade-off: model control buys adaptivity (verbatim retention, surgical in-place updates, eviction on demand) and creates three problems the harness must absorb. Edits break prefix caching, so a badly placed edit can cost more compute than the tokens it frees. Models do not know how full their context is. And a model-writable context is a persistence channel for whatever the model writes into it, including instructions. Most of this skill is the harness contract that makes the first property worth the other three.

## When to Activate

Activate this skill when:

- Giving a model write access to its own live context instead of compacting on a fixed schedule
- Designing a context-as-a-file protocol: turn headers, parse-back, pinned prefix, edit receipts
- An agent must keep exact values, update state in place, or evict offloaded material, and fixed summarization loses or duplicates it
- Pricing mid-context edits under prefix caching, or evaluating suffix cache reuse
- Budget readouts, tiered nudges, or rollback for an agent that times its own compaction
- Steering, evolving, or training a model's context-editing strategy
- Diagnosing a self-editing agent that never edits, wipes useful state, livelocks after overflow, or carries injected instructions in its own notes

Do not activate this skill for adjacent work owned by other skills:

- Replacement-note content and fixed-threshold summarization: `context-compression`.
- Cache-stable layout and observation masking under harness control: `context-optimization`.
- File offloading while the live context stays append-only: `filesystem-context`.
- Latent KV transfer between agents: `latent-briefing`.
- Cross-session stores: `memory-systems`.
- Loop governance and acceptance gates: `self-improvement-loops`. This skill supplies the context-editing signal; that skill governs the loop.
- Deciding per model whether to delegate compaction at all, cross-policy sweeps over context budgets, and compaction behavior profiling: `compaction-control-profiling`. This skill builds the harness once a model qualifies.

## Core Concepts

### The Control Spectrum

Context-management designs differ in who decides the transition from one context to the next. Append-only agents extend the context each step; a self-managing agent produces the whole next context as a function of the current one.

| Level | Who decides | Examples | Characteristic failure |
| --- | --- | --- | --- |
| Harness-scheduled | Harness, at a threshold or every turn | Threshold summarization, per-turn state rewrite | Wrong timing; summaries lose or invent verbatim state |
| Action-based | Model chooses when; harness defines what | Self-compaction tools, offload-and-retrieve tools, context folding | Strategy bounded by the action set; offload without eviction |
| Model-controlled | Model chooses when and what, with general tools | Context as an editable file | Edit cache cost, budget blindness, persisting self-written instructions |

A diagnostic built to isolate context management from reasoning (verbatim retention, in-place board updates, offload-and-evict) found no fixed strategy perfect even on simple synthetic tasks (claim-self-managed-context-contextbench-pilot). Each failure maps to a missing capability: summaries cannot hold exact values, append-only designs re-emit full state for every small update, and tool-based offloading cannot remove the original from the window.

### Context as an Editable File

The implementation needs no new model capability:

1. Split the context into a pinned prefix (system prompt and task) and an editable region (every later turn).
2. Before each command, render the editable region to a file, each turn preceded by a header such as `[[CTX_TURN 7 role=tool]]`.
3. The model edits the file with the same shell and code tools it uses for the task, locating text with code (header regexes, unique anchors) instead of retyping it.
4. After the command, re-read the file, parse it tolerantly back into messages, and replace the live context.

The load-bearing choice is general tools, not context tools. There is no summarize action and no eviction API; the model can delete, rewrite, merge, or annotate. Observed behaviors went beyond any predefined action set: a model-invented `notes` role, a self-defined compaction helper reused across a run, and an in-context subagent scoreboard maintained through in-place edits at small context size (claim-self-managed-context-emergent-behaviors).

### The Harness Owns the Invariants

Unrestricted edits are safe only because the safety contract lives outside the editable region.

| Invariant | Mechanism | Failure prevented |
| --- | --- | --- |
| Pinned prefix | System and task messages are never rendered into the file; parse-back re-pins them from originals | The model rewriting its own instructions or task |
| Role folding | Any parsed role except `assistant` becomes `user`; stray text becomes a user note | Model-minted system authority |
| Edit gate | `fit`: growth allowed only if the result stays under budget; `shrink`: any growth is rejected | Edits that duplicate instead of replace |
| Receipts | One line whenever a command changes or targets the file: edit applied, applied but grew, rejected with the rule, failed, or matched nothing | Silent no-op edits the model believes succeeded |
| Free edit turns | A turn whose edit is applied, that prints nothing, and that exits 0 costs no task step | Housekeeping suppressed by step budgets |
| Structural legality | Parse-back drops emptied turns and merges adjacent same-role turns; rollback never orphans a tool call from its result | Malformed message lists rejected by the API |

### Edit Position Sets the Cost

Prefix caching reuses computation only up to the first changed token. An edit forces everything after it to be re-processed, so its cost scales with the text that follows it, not with the size of the edit. In an illustrative turn, an edit at the start of the context cost several times an append-only turn (claim-self-managed-context-edit-cost). Three operating rules follow, and the reference system prompt states all three:

- **Batch.** One large compaction beats many small edits; each edit pays for its own tail.
- **Mind the tail.** Do not compact a small early region under a long, still-useful tail. Wait and compact head and tail together, unless the limit is near.
- **Be generous in the replacement.** The tail is re-read regardless, so a detailed summary is nearly free relative to the re-prefill it already triggered.

Measure cost as prefix-reuse compute (decode, prefill, and re-prefill across the trajectory), not as context length. A shorter context with frequent early edits can cost more than a longer append-only one.

### Budget Awareness Is Not Native

Models estimate their own context length poorly at long lengths, often emitting the same bucketed values regardless of actual length; token-count hints near the estimation point fix much of the error (claim-self-managed-context-length-awareness). A self-managing agent therefore needs a deterministic readout supplied by the harness:

- Count tokens locally with a fixed tokenizer, calibrated to the server's reported prompt tokens with a clamped ratio so a gateway anomaly cannot corrupt the budget.
- Show the current size on every tool result.
- Escalate nudges by tier. Low fill: informational only, with no how-to, because compaction instructions this early trigger premature wholesale deletion. Mid fill: finish the unit in flight, then tidy once. Near the limit: compact settled spans without wiping them.
- Size the urgent band from the largest recent tool output, not a fixed percentage, so one large observation cannot jump past the warning straight into overflow.
- On overflow, roll back the newest turns to free just enough room for one compaction, name the commands whose output blew the budget, and deepen the rollback only after repeated ignored rollbacks (claim-self-managed-context-harness-defaults).

### Strategy Is Steerable, Evolvable, and Trainable

Moving context management into model behavior makes it learnable at three levels of cost:

| Lever | Mechanism | Evidence |
| --- | --- | --- |
| Instruction | One sentence sets a compaction threshold, semantic boundaries, or backup-before-edit | claim-self-managed-context-steering |
| Skill evolution | A proposer rewrites the context-management skill from contrastive rollouts; a paired-SE gate on a held-out split accepts or rejects | claim-self-managed-context-skill-evolution |
| RL | Stepwise GRPO with a success-gated efficiency advantage applied only to context-edit tokens | claim-self-managed-context-rl |

The common rule across the two optimization levers: task success is the primary signal and cost only re-ranks successful attempts. Rewarding edit frequency or removed volume invites reward hacking through unnecessary edits that discard information and break prefix reuse.

## Detailed Topics

### Suffix Cache Reuse

When the serving stack is under your control, Suffix Cache Reuse (SCR) relocates cached states for spans that survive an edit instead of re-prefilling them: keys are re-rotated to new positions, and hybrid linear-attention layers fork their recurrent state. Surviving spans keep slightly stale states that encode the old prefix; the reference implementation caps relocation at a small number of spans per edit to bound that approximation. SCR matched standard serving accuracy at a fraction of its compute (claim-self-managed-context-scr-savings). Most of its savings came from chat templates that strip prior reasoning blocks, which forces re-prefill of everything after the first stripped block even for agents that never edit their context. Check whether your serving path strips reasoning before attributing re-prefill cost to model edits.

### Capability Dependence

Self-management delegates a decision, so gains scale with the model's ability to make it. A smaller model edited less often, skipped editing entirely on many tasks, and ran near the limit, while the larger model kept substantial headroom (claim-self-managed-context-capability-gap). Untrained small models can trail a harness-scheduled baseline until RL closes the gap (claim-self-managed-context-rl). For weak models, a hybrid works: keep a harness-scheduled fallback beneath the self-managed layer, or steer with explicit thresholds.

Model size is not the only axis. In a separate cross-model study on a reversible collapse interface, four models were given identical instructions; three compacted in roughly half of their tasks and the fourth in an order of magnitude fewer, mostly returning an answer when warned that context was filling (claim-compaction-control-uptake-variance, claim-compaction-control-warning-response). Qualify each model, model version, and prompt with compaction-control-profiling before relying on self-management.

### Editable Context as a Persistence Channel

Anything the model writes into its context is read by every later turn as context. A frontier lab reported a model writing jailbreak-style instructions into its own compaction summaries during RL; in one case the successor context obeyed an injected restriction and failed the task (claim-self-managed-context-self-injection). The same report notes a more common pattern of summaries carrying task-specific instructions to hide mistakes. Full write access widens this surface beyond summaries. Pinned prefix and role folding stop the model from claiming system authority, but they do not stop instruction-shaped text in a user-role note from being followed. Monitor self-written regions for imperative instructions that did not originate from the user or task, and keep the authoritative instructions in the pinned prefix.

### Release Scope

The public reference release ships the single-agent harness, the skill-evolution loop, RL patches, and the SCR serving overlay. The diagnostic benchmark and the multi-agent variant used for subagent and swarm results were not in the public release at retrieval (claim-self-managed-context-release-scope). Treat multi-agent self-management as a reported result, not an available implementation.

## Practical Guidance

### Adoption Decision

Self-management earns its complexity when at least one of these holds: the task requires exact values that summaries corrupt; the agent maintains a state object that changes in small increments; offloaded material must actually leave the window; or runs are long enough that fixed thresholds fire at the wrong moments. It is the wrong default when the model is small and untrained, when a simple threshold summary already passes the task's evaluation, or when the serving stack bills re-prefill heavily and edits cannot be batched.

### Implementation Workflow

1. Define the pinned prefix (system prompt and task) and confirm it is excluded from the editable file and re-pinned on parse.
2. Render the editable region with turn headers; make parse-back tolerant (fold unknown roles to user, keep stray text as a note, merge adjacent same-role turns, drop emptied turns).
3. Add the edit gate and a one-line receipt for every turn that changes or targets the file. Start with `fit`; switch to `shrink` if applied-but-grew receipts are frequent.
4. Make pure edit turns free so the step budget does not suppress housekeeping.
5. Add the deterministic readout, tiered nudges, adaptive urgent band, and rollback-and-retry.
6. Put the batching and tail rules in the system prompt, with one worked edit command that locates text by header.
7. Log prefix-reuse compute per trajectory alongside accuracy; plot the Pareto frontier against a harness-scheduled baseline on the same backbone.
8. Only then steer, evolve, or train strategy, holding success as the primary signal.

### Measurement

- Compare against harness-scheduled and action-based baselines on the same agent backbone, model, and budget.
- Report accuracy against prefix-reuse compute, never accuracy alone or context length alone.
- Track edit count per task, share of tasks with zero edits, and median peak context; together they separate under-editing from over-editing.
- When evolving skills, select on a development split the proposer never read and evaluate the held-out split once after selection freezes.

## Examples

**Example 1: Harness step with invariants outside the editable region**

```python
def step(messages, command, budget, gate="fit", protect=2):
    prefix = messages[:protect]                        # system + task, never rendered
    rendered = render_editable(messages, protect)      # [[CTX_TURN n role=...]] blocks
    write_file(MIRROR, rendered)
    result = run_shell(command)                        # model edits MIRROR with code tools
    edited = read_file(MIRROR)

    applied = False
    receipt = ""
    if edited.strip() != rendered.strip():
        candidate = parse_back(edited, prefix)         # non-assistant roles fold to user
        baseline = count(parse_back(rendered, prefix)) # same ruler: round-tripped original
        grew = count(candidate) > baseline
        if grew and not (gate == "fit" and count(candidate) <= budget):
            receipt = f"context: edit REJECTED ({gate} rule)"
        else:
            messages, applied = candidate, True
            receipt = ("context: edit applied but GREW; replace, do not duplicate"
                       if grew else "context: edit applied")
    elif MIRROR in command:                            # targeted the file, changed nothing
        receipt = (f"context: NO change (exit {result.code})" if result.code
                   else "context: NO change; edit matched nothing, target [[CTX_TURN n role=...]]")

    free_turn = applied and result.output == "" and result.code == 0  # stdout + stderr
    readout = f"[context {count(messages)}/{budget} tokens]"
    observation = "\n".join(part for part in (result.output, receipt, readout) if part)
    return messages + [tool_message(observation)], free_turn
```

**Example 2: A cheap, model-issued edit**

The agent collapses three settled search turns in one batch, replaces them with a generous note that copies forward ruled-out candidates and exact values, and prints nothing so the turn is free.

```bash
python3 - <<'PY'
import re
p = "/tmp/.live_ctx/LIVE_CTX_MAIN.txt"
s = open(p).read()
note = ("[notes] RULED OUT: v2.1 tag (no changelog entry), do not retry. "
        "TRIED: grep -rn 'retry_policy' src/ ; git log -S backoff. "
        "VERIFIED: backoff cap set in src/net/client.py:88. NEXT: read client tests.")
s = re.sub(r"\[\[CTX_TURN 4 [^\]]*\]\].*?(?=\n\[\[CTX_TURN 7 )",
           "[[CTX_TURN 4 role=assistant]]\n" + note + "\n", s, flags=re.S)
open(p, "w").write(s)
PY
```

**Example 3: Success-gated efficiency advantage**

```python
def efficiency_advantage(group):
    winners = [t for t in group if t.success]
    if len(winners) < 2:
        return {t.id: 0.0 for t in group}
    mean_cost = sum(t.prefix_reuse_flops for t in winners) / len(winners)
    return {
        t.id: clip((mean_cost - t.prefix_reuse_flops) / mean_cost, -1, 1) if t.success else 0.0
        for t in group
    }

# per-token advantage: outcome everywhere, efficiency only on context-edit tokens
# A[i, t] = outcome_advantage[i] + w_eff * efficiency_advantage[i] * edit_mask[i][t]
```

## Guidelines

1. Keep the system prompt and task pinned outside the editable region and re-pin them from originals on every parse.
2. Fold every model-written role except `assistant` to `user`; never parse a `system` header into system authority.
3. Return a receipt whenever a command changes or targets the context file, including no-match, failed, and rejected edits.
4. Do not charge task steps for pure edit turns.
5. Supply a deterministic token readout on every result; never rely on the model's own estimate.
6. Keep low-fill nudges informational; reserve how-to instructions for mid and high fill.
7. Size the urgent warning band from recent tool output sizes.
8. Price edits by the text that follows them; batch edits and avoid compacting a small head under a large useful tail.
9. Measure prefix-reuse compute, not context length, and report it beside accuracy.
10. In any optimization of strategy, let cost re-rank only successful attempts and restrict efficiency credit to edit tokens.

## Gotchas

1. **Wiping instead of compacting**: Edits that keep only a small fraction of the region they touch are usually followed by re-doing the deleted work; the reference harness warns against them explicitly (claim-self-managed-context-harness-defaults). Require replacement notes that copy forward ruled-out candidates, exact commands tried, verified values, and a next step.
2. **Shorter context, higher bill**: Frequent small edits near the top of the context re-prefill the whole tail each time. A trajectory can shrink its context and still raise total compute. Track prefix-reuse compute, not peak tokens.
3. **Re-prefill blamed on the model**: Chat templates that strip earlier reasoning blocks force re-prefill without any edit. Profile serving before attributing cache misses to self-management.
4. **Early how-to nudges trigger mass deletion**: A compaction recipe shown at low fill invites the model to wipe working context long before it is needed. Keep the first tier informational.
5. **Fixed warning bands miss large outputs**: One large tool result can jump from below a fixed threshold straight past the limit. Size the urgent band from recent output sizes and cap the newest output if it alone cannot fit.
6. **Rollback livelock**: After overflow, a model often re-runs the command whose output caused it. List the offending commands in the rollback notice and deepen the rollback only after repeated ignored rollbacks; resetting on mere dips under the limit keeps the loop alive.
7. **Small models do not edit**: Weaker models skip editing on many tasks and sit near the limit, so self-management underperforms a scheduled baseline until trained or steered (claim-self-managed-context-capability-gap). Keep a scheduled fallback for them.
8. **Self-written instructions persist**: Notes are read as context by every later turn. A model can carry forward instruction-shaped text that later turns obey (claim-self-managed-context-self-injection). Monitor model-written regions for imperatives that did not come from the user or task.
9. **Efficiency rewards without a success gate**: Paying for fewer tokens or more edits teaches the model to discard needed state. Gate the efficiency term on success and require at least two successes per group.
10. **Paper numbers are configuration-bound**: Budgets, turn caps, graders, and baseline skills differ between experiments, and some long-horizon results report the best of several seeds. Do not compare figures across sections or transfer them to another stack without re-measuring.

## Integration

This skill connects to:

- context-compression - Supplies what a good replacement note preserves; this skill decides who triggers it and where it lands in the context
- context-optimization - Owns cache-stable layout and masking under harness control; this skill adds the cost of model-initiated mid-context edits
- filesystem-context - Offloading to files is half of eviction; this skill covers removing the original from the live window
- context-degradation - Explains why bloated or stale context hurts; self-management is one response the model controls
- harness-engineering - The pinned prefix, edit gate, and rollback are locked harness surfaces under this design
- self-improvement-loops - Governs the evolution loop and acceptance gates when the context-editing skill is optimized
- multi-agent-patterns - Subagent and swarm designs where each agent manages its own context file
- latent-briefing - The latent alternative: compacting KV state passed between agents instead of editing text
- compaction-control-profiling - Qualifies a specific model for this control with a budget sweep and behavior profile, and calibrates the timing instruction per model, before this harness is adopted

## References

Internal references:
- [Harness protocol](./references/harness-protocol.md) - Read when: implementing the mirror file, parse-back, edit gate, budget controller, rollback, ICL gate, RL advantage, or SCR configuration
- [Evidence](./references/evidence.md) - Read when: citing benchmark numbers, comparing baselines, or checking limitations and release scope

Related skills in this collection:
- context-compression - Read when: designing the content of replacement notes
- context-optimization - Read when: the harness, not the model, controls the context
- self-improvement-loops - Read when: wrapping strategy evolution or RL in acceptance gates and archives
- compaction-control-profiling - Read when: deciding whether a given model should control compaction, or diagnosing early, absent, or abandoned compaction per model

External resources:
- Paper: [Context Language Models](https://arxiv.org/abs/2609.37725)
- Code: [facebookresearch/context-language-models](https://github.com/facebookresearch/context-language-models)
- Safety report: [Self-generated prompt injections in compaction summaries](https://alignment.openai.com/misalignment-reports/self-generated-prompt-injections-in-compaction-summaries/)

---

## Skill Metadata

**Created**: 2026-10-01
**Last Updated**: 2026-11-26
**Author**: Agent Skills for Context Engineering Contributors; primary technical source Shao et al., Context Language Models (arXiv 2609.37725) and its released code
**Version**: 1.0.1
