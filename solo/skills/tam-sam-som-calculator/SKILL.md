---
name: tam-sam-som-calculator
description: "Calculates Total Addressable Market (TAM), Serviceable Addressable Market (SAM), and Serviceable Obtainable Market (SOM). Triggered by 'market size', 'calculate TAM', 'revenue potential', 'market volume'."
version: "2.1.0"
bundle: research-validate
triggers:
  - "calculate TAM"
  - "market size"
  - "TAM SAM SOM"
tools:
  standalone: ["exa"]
  supercharged: ["exa"]
---

# Skill: TAM/SAM/SOM Calculator

This skill helps you put a dollar value on your opportunity. It uses two rigorous approaches—Top-Down (industry reports) and Bottom-Up (unit economics)—to ensure your market sizing is realistic, not just wishful thinking.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Dual-Method Pricing (Top-Down vs. Bottom-Up)                 │
│  ✓ Automatic unit-economics calculator (ACV x Customers)        │
│  ✓ Realistic SOM estimation based on sales capacity             │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~search)                             |
│  + Live Data Enrichment: Use Exa/Tavily to find recent reports   │
│    (Gartner, Forrester, Statista) for Top-Down numbers.         │
│  + Industry Multipliers: Auto-calculate growth rates (CAGR).    │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "How big is the [Industry] market?"
- "Calculate my TAM for this project"
- "Market sizing for [Product]"
- "Is this market big enough?"

---

## 📋 The 3 Layers of Market Sizing

1.  **TAM (Total Addressable Market)**: The total demand for your category globally.
2.  **SAM (Serviceable Addressable Market)**: The portion of TAM that fits your specific service, geography, and technology.
3.  **SOM (Serviceable Obtainable Market)**: The portion of SAM you can realistically capture in the next 12-24 months with your current resources.

---

## ⚖️ Calculation Methods

The agent will calculate using both methods to find the "Truth in the Middle":

### Method A: Top-Down (The "Ocean" View)

- Find a large industry figure (e.g., "The global CRM market is $60B").
- Apply filters based on your niche (e.g., "SaaS is 20%", "SMB is 15%", "Europe is 30%").
- _Result_: A fraction of the large pie.

### Method B: Bottom-Up (The "Hustler" View)

- Define your **ACV** (Annual Contract Value).
- Estimate the total number of reachable target customers.
- _Calculation_: ACV × Total Customers = Market Size.
- _Result_: A sum of potential sales.

---

## 🚀 Workflow

1.  **Identity Extraction**: Read `business-profile.json` and `icp.json`.
2.  **Market Scanning**: Use `~~search` to find industry reports for Top-Down estimation.
3.  **Unit Economics**: Ask for your pricing model (Retainer/One-off) and target price.
4.  **SOM Scaling**: Ask about your current team size/capacity to cap the SOM.
5.  **Synthesis**: Compare both methods and highlight discrepancies.
6.  **Output**: Save to `data/3-Ressources/research/market-size.md`.

---

## 📈 Agent Instructions

- **Be Skeptical**: If a solopreneur claims a $1B SOM, challenge them. "A $1B SOM would require hundreds of sales reps. With just you, what is the ACTUAL volume you can handle?"
- **Citations Required**: For Top-Down data, always provide the source URL.
- **Output Template**:
  - The Market Triangle (ASCII visualization).
  - Top-Down vs. Bottom-Up Table.
  - The "Growth Path": From SOM to SAM.
  - Assumptions Registry: What must be true for these numbers to work?

---

## 📂 References

- [Sizing Workbook](./references/workbook.md)
- [Unit Economics Guide](./references/unit-economics.md)
- [Market Growth Rates (CAGR)](./references/cagr.md)

---

## 🔬 Sentinel Integration (when installed)

```python
SENTINEL_ROOT = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

Skip this section entirely if `sentinel_installed` is False. TAM/SAM/SOM works identically without it.

### Trigger condition
Activate **after the SOM is calculated**. TAM and SAM are arithmetic — Sentinel doesn't touch them. SOM is where judgment (and overconfidence) enters.

### What to run

**Step 1 — reality-checker (SOM reference class)**

Invoke `reality-checker` with:

Reference class: "[product type] companies at [founding stage / pre-revenue / post-launch] with [solo / small team] in [market geography]"

Require estimates with confidence levels for:
- Median Y1 market share capture for comparable companies (not funded outliers)
- Typical SOM as % of SAM in year 1 for bootstrapped vs funded products
- Time to reach meaningful penetration (5%+ of SAM) — historical range

If user's SOM exceeds 5% of SAM in Y1 → flag: "Top 10% territory. Requires explicit justification beyond conviction."
If user's SOM is less than 1% of SAM → no flag (appropriately conservative).

Tell the user where to verify: CB Insights stage data, Stripe Atlas bootstrapped company data, industry-specific SaaS benchmarks.

**Step 2 — questioner (SOM assumption check)**

Load bias IDs: `[14, 22, 3]`
- ID 14: Overconfidence (SOM estimate without evidence)
- ID 22: Planning Fallacy (timeline to SOM)
- ID 3: Representativeness (assuming your product trajectory matches successful comparable)

Generate 2 questions targeting the SOM number specifically:
- "Name two companies that entered this market at a similar stage. What market share did they capture in year 1?"
- "What specific constraint (sales capacity, marketing budget, product limitations) caps your SOM — and how did you calculate it?"

### Output format addition

Add a **SOM Stress Test** section after the market triangle output:

```
## SOM Stress Test (Sentinel)

Your SOM: $[X] ([Y]% of SAM in year [Z])
Reference class position: [bottom / mid / top] quartile
Base rate: Comparable companies typically capture [range]% in Y1
  Verify at: [specific source]

Questions to answer before presenting this number:
1. [questioner question 1]
2. [questioner question 2]
```

### Standalone output (Sentinel not installed)
Standard TAM/SAM/SOM triangle with top-down and bottom-up methods, assumptions registry. No change.

---

## 🛡️ Sentinel Integration

```python
SENTINEL_ROOT      = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

**Trigger**: After SOM calculation (the most bias-prone step).
**Standalone mode**: Skip entirely.

### If Sentinel installed — Outside view on the SOM

**Step A — reality-checker** (`../sentinel-v8/agents/reality-checker.md`)

After producing the SOM estimate, apply reference class forecasting:
- Reference class: `"bootstrapped [category] products, [stage], year 1 market capture"`
- Key metrics to estimate:
  - Median Y1 market share capture for products at this stage
  - Top-quartile capture rate (what "going well" looks like)
  - What % of similar products capture >5% of SAM in year 1
- Verify at: Indie Hackers revenue graphs, SaaS Capital benchmarks, Stripe Atlas cohort data
- Gap: "Your SOM estimate puts you at [X] percentile. State explicitly why you're in that percentile."

**Automatic flag**: If user's SOM > 5% of SAM in year 1:
> "⚠️ Your SOM exceeds 5% of SAM in year 1. Fewer than 10% of bootstrapped products achieve this. This is possible, but requires a specific justification — not ambition. What structural advantage makes you top-decile?"

**Step B — questioner** (`../sentinel-v8/agents/questioner.md`)

Pass `bias_ids: [14, 22, 3]` (Overconfidence, Planning Fallacy, Representativeness).

Ask 2 targeted questions:
1. "Name three companies that attempted to capture this exact niche in year 1. What market share did they actually achieve?" (Probes representativeness — the assumption that your situation is typical of the success stories you've heard)
2. "What would have to be true about your sales capacity, conversion rate, and channel reach for this SOM to be real?" (Forces planning fallacy into the open)

**Output integration** — append after SOM table:

```
## Outside View (Sentinel)

**Reference class**: [stated class]
**Median Y1 capture**: [X]% of SAM — your estimate: [Y]%
**Your estimate is in the [Z] percentile of comparable launches.**

[If >5% flag — see above]

**Questions to answer before using this SOM in a pitch or business plan:**
1. [Question 1]
2. [Question 2]
```
