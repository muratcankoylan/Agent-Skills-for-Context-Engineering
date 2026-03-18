# Dimension Library: Pre-Built Sets for All 5 Diagnostic Types

When building a diagnostic, propose the matching set as a starting point. Always confirm with the user before finalizing — dimensions should be edited to match their specific service and ICP.

---

## Type 1: Lead Qualification Diagnostic

**Purpose pattern:** "Is this prospect ready for a proposal, or do they need education/nurture first?"

**Recommended dimensions (choose 4–5):**

| Dimension | What it measures | Suggested weight |
|-----------|-----------------|-----------------|
| **Problem clarity** | How well they articulate the problem they need solved | 20% |
| **Pain acuity** | How much the problem is costing them right now (urgency) | 25% |
| **Solution awareness** | Do they know what kind of solution they need (vs. still exploring) | 15% |
| **Decision readiness** | Are the right stakeholders involved and motivated to act | 20% |
| **Budget reality** | Is budget allocated or hypothetical | 20% |
| **Timeline pressure** | Is there a real deadline driving urgency | (swap with another if needed) |

**Score band logic for lead diagnostics:**
- **High (66–100):** Ready for proposal — advance to `Proposal` stage in pipeline
- **Medium (36–65):** Qualified but not ready — advance to `Discovery` stage, schedule call
- **Low (0–35):** Not yet qualified — add to nurture sequence, don't pitch yet

---

## Type 2: Client Health Diagnostic

**Purpose pattern:** "Is this active client at risk of not renewing / going quiet before I notice?"

**Recommended dimensions (choose 4–5):**

| Dimension | What it measures | Suggested weight |
|-----------|-----------------|-----------------|
| **Goal progress** | Are they getting the results they hired you for | 30% |
| **Communication quality** | Are they engaged, responsive, and informed | 20% |
| **Stakeholder alignment** | Is the internal champion still championing | 20% |
| **Value perception** | Do they see the ROI of working with you | 20% |
| **Future intent** | Are they thinking about what comes next with you | 10% |

**Score band logic for client health:**
- **High (66–100):** Healthy — flag as renewal candidate, request testimonial
- **Medium (36–65):** Monitor — proactive check-in, clarify goals, re-anchor value
- **Low (0–35):** At risk — immediate attention, escalate in `client-lifecycle-agent`

**Integration note:** score maps directly to the `health_score` field in the client card (0–100).

---

## Type 3: Onboarding Readiness Diagnostic

**Purpose pattern:** "Is this new client ready to kick off, or are there blockers to clear first?"

**Recommended dimensions (choose 4–5):**

| Dimension | What it measures | Suggested weight |
|-----------|-----------------|-----------------|
| **Access & setup** | Do they have what you need to start work (credentials, assets, tools) | 25% |
| **Internal alignment** | Is the team that needs to be involved on board and available | 20% |
| **Success definition** | Have they articulated what "done well" looks like | 25% |
| **Bandwidth** | Do they have time to do their part of the engagement | 15% |
| **Decision authority** | Can the person you're working with make decisions, or is there a blocker above | 15% |

**Score band logic for onboarding:**
- **High (66–100):** Ready to kick off — proceed with `client-onboarding` Day 0 sequence
- **Medium (36–65):** Kick off with caveats — address specific low-scoring dimensions before start
- **Low (0–35):** Not ready — delay kickoff, send pre-onboarding checklist, schedule prep call

---

## Type 4: Product Validation Diagnostic

**Purpose pattern:** "Is the market pain real enough, and am I the right person to solve it?"

**Recommended dimensions (choose 4–6):**

| Dimension | What it measures | Suggested weight |
|-----------|-----------------|-----------------|
| **Pain frequency** | How often they experience the problem (daily vs. occasionally) | 20% |
| **Pain cost** | What the problem costs them in time, money, or energy | 25% |
| **Current solution dissatisfaction** | How badly current tools/workarounds are failing them | 20% |
| **Willingness to pay** | Would they pay for a solution, and roughly how much | 20% |
| **Urgency** | Is solving this a current priority or a "someday" item | 15% |

**Score band logic for product validation:**
- **High (66–100):** Strong market signal — proceed with `/solo:build design`
- **Medium (36–65):** Weak signal — need more respondents or problem reframe
- **Low (0–35):** Market not ready — pivot the problem statement or audience

**Usage pattern:** Publish this as a Tally form to 3–5 target communities. 30+ responses with average score > 60 = validated demand signal. Feed aggregate data into `/solo:build validate`.

---

## Type 5: Self-Assessment Diagnostic

**Purpose pattern:** Varies — examples below.

### Self: Business Health Check

| Dimension | What it measures | Suggested weight |
|-----------|-----------------|-----------------|
| **Revenue predictability** | Stability and recurrence of income | 25% |
| **Client concentration** | Over-dependence on any single client | 20% |
| **Pipeline health** | Are you always working on finding the next client | 20% |
| **Pricing alignment** | Are you priced for where you are today or where you started | 20% |
| **Energy sustainability** | Are you burning out or could you keep this pace for 3 more years | 15% |

### Self: Niche Clarity

| Dimension | What it measures | Suggested weight |
|-----------|-----------------|-----------------|
| **ICP precision** | Can you describe your ideal client in one sentence | 25% |
| **Problem ownership** | Is there a specific problem you're known for solving | 25% |
| **Differentiation** | Is there something about how you work that competitors don't offer | 25% |
| **Proof density** | Do you have case studies / results that back your positioning | 25% |

### Self: Pricing Readiness

| Dimension | What it measures | Suggested weight |
|-----------|-----------------|-----------------|
| **Market knowledge** | Do you know what peers charge for similar work | 25% |
| **Value communication** | Can you articulate ROI before quoting a price | 25% |
| **Confidence level** | Do you flinch when you name your price | 25% |
| **Demand signal** | Are you turning away work or chasing every lead | 25% |

---

## Dimension Design Rules

**Good dimension:** measures one thing, has a clear good/bad direction, and the respondent can answer honestly without feeling judged.

**Weak dimension:** compound ("your strategy and your execution"), too abstract ("overall business health"), or socially loaded ("how much do you care about this").

**Weight guidance:**
- The most predictive dimension of your purpose question gets the highest weight
- No dimension below 10% (too low to matter)
- No dimension above 35% (too dominant — one bad answer shouldn't define the score)
- Recalculate if the user edits dimensions: weights must sum to 100%
