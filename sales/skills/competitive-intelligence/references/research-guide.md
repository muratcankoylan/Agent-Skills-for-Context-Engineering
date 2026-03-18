# Competitive Intelligence — Research Guide

## Research Methodology

### Step 1: Competitor Discovery

If the user doesn't list competitors, find them:
- Search: "[Your Company] alternatives", "[Your Company] vs", "[category] competitors"
- Check G2, Capterra, or TrustRadius for the category
- Ask: "Who do you most often compete against in deals?"

Limit to 1–5 competitors for a focused battlecard.

---

### Step 2: Per-Competitor Research (repeat for each)

**Product & Positioning:**
- Visit their homepage, pricing page, features page
- Note: target segment, key use cases, value proposition
- Extract 3–5 differentiators they claim

**Pricing:**
- Public pricing page (if available)
- Community forums, Reddit, review sites for pricing intel
- Note: model (per seat, usage, flat), tiers, free trial

**Recent Releases (last 90 days):**
- Their blog / changelog / release notes
- LinkedIn company page (product announcements)
- Press releases

**Weaknesses:**
- G2/Capterra reviews (filter 1–3 stars)
- Common complaints on Reddit, Hacker News
- Job postings (what they're hiring for = what they're lacking)

**Search query templates:**
```
"[Competitor] review site:g2.com"
"[Competitor] problems OR issues OR limitations"
"[Competitor] vs [Your Company]"
"[Competitor] pricing 2025"
"site:[competitor.com] changelog OR releases OR new"
```

---

### Step 3: Your Company Research

Gather your own recent releases to counter their claims:
- Your changelog / product blog (last 90 days)
- Recent case studies and proof points
- Win rates / deal data (from CRM if connected)

---

### Step 4: Build Differentiation Matrix

For each capability area, score:
- ✅ You win clearly
- ⚠️ Roughly equal / depends
- ❌ They win or you don't have it

| Capability | You | Competitor A | Competitor B |
|------------|-----|-------------|-------------|
| [Feature 1] | ✅ | ⚠️ | ❌ |
| [Feature 2] | ✅ | ✅ | ⚠️ |

---

## Talk Track Templates

### Positioning Against [Competitor]

**When a prospect mentions [Competitor]:**

> "[Competitor] is strong at [X]. Where we differentiate is [Y] — specifically for [use case], customers find [proof point]. Would it be useful to see a quick comparison?"

**Landmine questions** (expose their weaknesses naturally):

> "How important is [area where they're weak] to your team?"
> "What's your experience been with [known pain point]?"
> "Have you evaluated how [capability] would work at your scale?"

---

## HTML Battlecard Structure

The output is a single self-contained HTML file.

### Page Layout

```
Header: Your company logo | "Competitive Battlecard" | Date
Nav tabs: [Overview] [Competitor A] [Competitor B] ...

Overview tab:
  - Comparison matrix (all competitors × key capabilities)
  - Where you win summary
  - Where to be careful

Per-competitor tab:
  - Competitor overview (segment, pricing, strengths)
  - Head-to-head matrix (you vs. them only)
  - Recent releases (theirs vs. yours)
  - Talk tracks
  - Landmine questions
```

### CSS Design (Dark Theme)

```css
:root {
  --bg: #0d0d14;
  --card: #16161f;
  --border: rgba(255,255,255,0.07);
  --text: #e8e8f0;
  --muted: rgba(232,232,240,0.5);
  --win: #22c55e;
  --neutral: #f59e0b;
  --loss: #ef4444;
  --accent: #6366f1;
}
body { background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; }
.tab-active { border-bottom: 2px solid var(--accent); }
.win { color: var(--win); }
.neutral { color: var(--neutral); }
.loss { color: var(--loss); }
```

### JavaScript (Tab Switching)

```javascript
function showTab(id) {
  document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('tab-active'));
  document.getElementById(id).style.display = 'block';
  event.target.classList.add('tab-active');
}
```

---

## Connector Usage

| Connector | Queries to Run |
|-----------|---------------|
| **~~CRM** | `GET /deals?competitor=[name]&stage=closed` → win/loss ratio; `GET /activities?keyword=[competitor]` → mentions in notes |
| **~~knowledge base** | Search for "[competitor] battlecard", "[competitor] objections", "competitive" |
| **~~chat** | Search "#competitive", "[competitor]", "lost to [competitor]" in last 90 days |
| **~~conversation intelligence** | Filter transcripts for competitor mentions, extract objections raised |
