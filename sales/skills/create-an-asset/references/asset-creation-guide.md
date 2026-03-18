# Create an Asset — Phase-by-Phase Guide

## Phase 0: Detect Seller Context

Identify who the seller is before building anything.

**Detection order:**
1. Check `data/2-Domaines/sales-profile.json` for `seller_company` and `language_preference`
2. If not found, ask: "What company do you work for? (I'll use this to brand the asset correctly)"
3. If an email is visible in context, extract domain → company name

**Language:** If `language_preference: "fr"` → generate entire asset in French.

---

## Phase 1: Collect Prospect Context

Gather deal context before designing. Ask only what's missing.

**Required:**
- Prospect company name
- Primary contact(s) and titles
- Deal stage (awareness / evaluation / decision / close)

**Optional but improves output:**
- Pain points or goals mentioned by the prospect
- Existing materials (pitch deck, email thread, call notes) — paste or attach
- Competitor(s) in the deal
- Budget/timeline signals

**Shortcut:** If the user says "create an asset for [Company]", start with web research on that company instead of asking.

---

## Phase 2: Collect Audience + Purpose

| Question | Options |
|----------|---------|
| Who is the primary audience? | Economic buyer / Technical evaluator / Champion / Mixed exec group |
| What is the goal of this asset? | Build awareness / Drive evaluation / Accelerate close / Leave-behind |
| What action should they take after viewing? | Schedule next meeting / Share internally / Sign / Approve POC |
| Tone? | Formal / Conversational / Technical / Executive |

Max 2 rounds of clarifying questions. If context is rich, skip to format selection.

---

## Phase 3: Select Format

| Format | Best For | When to Suggest |
|--------|----------|-----------------|
| **Interactive landing page** | Exec alignment, intros, value prop | Multi-stakeholder, async review needed |
| **Deck-style** | Formal meetings, board presentations | Live meeting, linear narrative needed |
| **One-pager** | Leave-behinds, quick summaries | Post-meeting, short attention span |
| **Workflow / Architecture demo** | Technical deep-dives, POC demos | Technical evaluator, solution validation |

If the user doesn't specify, recommend based on deal stage:
- Awareness → Landing page
- Evaluation → Deck or one-pager
- Decision → One-pager + workflow demo
- Close → One-pager

---

## Phase 4: Research

Depth depends on context richness. If prospect materials were provided, skip public research.

**Always research:**
- Company size, industry, HQ
- Recent news (funding, product launches, leadership changes)
- Primary use case for your product

**If time allows:**
- Leadership team (LinkedIn, company page)
- Brand colors (hex codes from website or logo)
- Competitor landscape for this prospect

**Brand color extraction:**
Visit `[company].com` and extract primary brand colors. Use for asset styling. Default to dark theme if colors unavailable.

---

## Phase 5: Plan Structure

Map sections based on format × audience × purpose.

### Landing Page Structure (default)

```
Tab 1: Welcome / Executive Summary
  - Hook headline (their language, their pain)
  - 3 key messages
  - CTA button

Tab 2: The Problem
  - Industry context
  - Specific pain points (mirror their words)
  - Cost of inaction

Tab 3: Our Solution
  - How it works (3-step or visual)
  - Key capabilities relevant to their use case
  - Live demo embed or screenshot tour

Tab 4: Proof
  - Relevant case study (same industry/size)
  - Key metrics (time saved, revenue impact, cost reduction)
  - Logos (if available)

Tab 5: Next Steps
  - Clear CTA (schedule meeting / start POC / approve budget)
  - Contact info
  - FAQ (optional)
```

### One-Pager Structure

```
Header: Company logo + prospect company name + date
Section 1: The Challenge (2-3 sentences, their words)
Section 2: Our Solution (3 bullet points)
Section 3: Why Us (differentiation + proof point)
Section 4: Next Step (single CTA)
Footer: Contact + website
```

### Deck Structure (10 slides max)

```
Slide 1: Cover (prospect name + theme + date)
Slide 2: Agenda
Slide 3: The Problem (their reality)
Slide 4: Root Cause / Insight
Slide 5: Our Approach
Slide 6: How It Works
Slide 7: Proof (case study)
Slide 8: ROI / Business Case
Slide 9: Implementation / Timeline
Slide 10: Next Steps + Q&A
```

### Workflow / Architecture Demo Structure

```
Frame 1: Title + context
Frames 2-N: Step-by-step animated diagram
  - Each frame = one step in the workflow
  - Highlight the "before" pain and "after" outcome
  - Label each component with prospect's terminology
Final frame: Summary + CTA
```

---

## Phase 6: Generate Content

**Voice and tone:**
- Use the prospect's language (mirror words from their website, job postings, or call notes)
- Lead with their pain, not your features
- ROI framing: time saved, revenue impact, cost reduction, risk reduced

**Proof points:**
- Use specific numbers where available ("reduced onboarding time by 60%")
- Match proof to their industry where possible
- If no exact match, use category-level proof ("enterprise customers in [industry]...")

**Bilingual handling:**
- If `language_preference: "fr"`, translate all user-facing copy
- Keep technical terms in their original form unless a French equivalent is standard
- Section headings, CTAs, and navigation: always translate

---

## Phase 7: Apply Visual Design

### CSS Design System

```css
/* Dark theme base */
:root {
  --bg-primary: #0a0a0f;
  --bg-card: #12121a;
  --border: rgba(255,255,255,0.08);
  --text-primary: #ffffff;
  --text-secondary: rgba(255,255,255,0.6);
  --accent: [prospect-primary-color];       /* extracted from brand */
  --accent-secondary: [prospect-secondary]; /* complementary */
}

/* Typography */
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
h1 { font-size: clamp(2rem, 5vw, 3.5rem); font-weight: 700; }
h2 { font-size: clamp(1.5rem, 3vw, 2.5rem); font-weight: 600; }

/* Cards */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 2rem;
}

/* Accent gradient */
.accent-gradient {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-secondary) 100%);
}
```

**Animations:** Use CSS transitions and `@keyframes` for entrance animations. No JavaScript libraries. Keep animations subtle (fade-in, slide-up).

**Responsive:** Mobile-first. Breakpoints at 768px and 1200px.

---

## Phase 8: Clarification Checkpoint

Before building, confirm understanding with a single message:

> "Here's what I'm building:
> - **Format:** [format]
> - **Audience:** [title(s)]
> - **Goal:** [goal]
> - **Key message:** [one sentence]
> - **CTA:** [action]
>
> Ready to build, or want to adjust anything?"

Only one round of adjustments before building.

---

## Phase 9: Build & Deliver

**Output requirements:**
- Self-contained HTML file (all CSS and JS inline)
- No external CDN dependencies
- File name: `[ProspectName]-[format]-[YYYY-MM-DD].html`
- Tested at 1440px wide and 375px (mobile)

**Delivery message:**

> "Your [format] for [Prospect] is ready.
>
> **File:** `[filename].html`
>
> **To share:**
> - Email directly as attachment
> - Host on GitHub Pages (free): drag into repo → enable Pages
> - Host on Netlify Drop: drag file to netlify.com/drop
>
> **To edit:** Open in any text editor to change copy or colors."
