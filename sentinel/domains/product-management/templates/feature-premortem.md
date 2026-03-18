# Feature Pre-mortem - Sentinel

## Purpose

A pre-mortem imagines the feature has already failed, then works backward to
identify what caused that failure. It is NOT pessimism - it's the most effective
bias-reduction tool before a commitment (Kahneman, 2011; Klein, 2007).

The pre-mortem is most useful when:
- The team is excited and aligned (groupthink risk)
- The timeline is aggressive
- The feature is novel with no internal precedent
- There's executive pressure to ship

---

## Feature

- **Feature name**:
- **Pre-mortem facilitator**:
- **Date**:
- **Participants** (names + roles):
- **Target launch date**:
- **Success metric committed to**:
---


## Setup (read aloud to the room)

> "We're now 6 months past the launch date of [feature name].
> The feature flopped. Adoption is near zero. The engineering team regrets
> building it. Nobody on sales is using it as a talking point.
> The PM is embarrassed at the retrospective.
>
> Your job is NOT to defend the feature or explain why this is unlikely.
> Your job is to figure out what happened. Assume the failure is real.
> Write your diagnosis. You have 5 minutes - alone, in silence."

---

## Individual diagnosis (5 min, alone, in writing)

*Each participant writes their own answer before discussion.*

**Participant**: ___________________________

**What happened?** (describe the failure as if explaining to a journalist):

**Root cause** (the most likely single cause):

**Early warning sign we ignored**:

---

## Group analysis - 7 failure modes

For each failure mode, the group estimates probability and discusses evidence.

### FM1 - Built for the vocal minority
> The users who asked loudest were not representative of the actual user base.
> Most users had no need for this feature.

**Evidence this could happen**:
**How many users were actually consulted?**
**Were they representative of the target segment or outliers?**
**Probability**: % **Severity**: /10

**Prevention**:
- [ ] Validate with N > ___ users across ___ segments before committing
- [ ] Compare requestors to usage analytics - are they typical users?

---

### FM2 - Solved a fake problem
> Discovery was confirmation, not exploration. The problem we thought existed
> was an artifact of our interview framing or our own assumptions.

**Evidence this could happen**:
**Did research start with a solution or a problem?**
**What would falsify the problem hypothesis?**
**Probability**: % **Severity**: /10

**Prevention**:
- [ ] Rerun discovery starting with open problem exploration, not solution feedback
- [ ] Identify ONE observation that would cause you to abandon this feature

---

### FM3 - Scope crept past viability
> The "MVP" accumulated so many requirements that the thing we shipped was
> too complex to understand, adopt, or maintain.

**Evidence this could happen**:
**Current scope vs. initial scope** (how much has it grown?):
**Who can add scope, and what stops them?**
**Probability**: % **Severity**: /10

**Prevention**:
- [ ] Freeze scope NOW. Document scope freeze in writing.
- [ ] Identify the 50%-cut version. Is that the actual MVP?

---

### FM4 - Shipped without activation loop
> The feature exists but users never discover it. No onboarding trigger,
> no habit formation hook, no integration with the natural user journey.

**Evidence this could happen**:
**Where in the product will users encounter this feature?**
**What triggers the first use?**
**Probability**: % **Severity**: /10

**Prevention**:
- [ ] Activation plan is part of definition of done - not post-launch
- [ ] Map exact user journey from signup/login to first feature use

---

### FM5 - Underestimated effort, overestimated quality
> We shipped fast but shipped broken. Tech debt made post-launch iteration
> impossible. Bugfixes consumed the team and killed momentum.

**Evidence this could happen**:
**What's the estimate vs. historical comparable?**
**What's NOT included in the current estimate?**
**Probability**: % **Severity**: /10

**Prevention**:
- [ ] Add 40% buffer to estimate (planning fallacy correction)
- [ ] Define explicit "not shipping" quality gates before launch

---

### FM6 - Wrong success metric
> We hit our KPI (feature adoption %) but it had zero correlation with
> retention or revenue. We optimized for the wrong thing.

**Evidence this could happen**:
**What's the success metric?**
**What's its proven correlation to business outcome?**
**Probability**: % **Severity**: /10

**Prevention**:
- [ ] Define success metric BEFORE building - not after
- [ ] Map metric to business outcome with explicit hypothesis

---

### FM7 - Killed by internal competition
> A higher-priority incident, initiative, or executive request consumed the
> team's attention post-launch. The feature launched and was immediately
> abandoned with no iteration budget.

**Evidence this could happen**:
**What else is competing for this team's post-launch attention?**
**Who is responsible for iteration post-launch?**
**Probability**: % **Severity**: /10

**Prevention**:
- [ ] Reserve ___ sprints explicitly for post-launch iteration
- [ ] Name the person who owns iteration (it should be the same PM)

---

## Priority risks summary

| Failure mode | Probability % | Severity /10 | Risk score | Status |
|-------------|:------------:|:------------:|:----------:|--------|
| FM1 - Built for vocal minority | | | | |
| FM2 - Solved fake problem | | | | |
| FM3 - Scope crept | | | | |
| FM4 - No activation loop | | | | |
| FM5 - Effort underestimate | | | | |
| FM6 - Wrong metric | | | | |
| FM7 - Internal competition | | | | |

**Risk score** = Probability x Severity / 10

---

## Decision

Based on the pre-mortem:

- [ ] **GO as planned** - risks are acceptable and mitigated
- [ ] **GO with changes** - modifications needed before launch:
  1.
  2.
- [ ] **REDUCE SCOPE** - ship a smaller version to reduce FM3/FM5 risk
- [ ] **DELAY** - until FM1/FM2 is resolved through additional discovery
- [ ] **KILL** - risk/value ratio is unfavorable

**What would change this decision**:

**Pre-mortem facilitator sign-off**:

**Date**:
