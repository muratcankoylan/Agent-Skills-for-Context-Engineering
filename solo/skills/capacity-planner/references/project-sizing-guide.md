# Project Sizing Guide

Estimating project hours before you commit is a core skill. These benchmarks are starting points — build your own personal baseline by tracking actuals.

> **The solopreneur multiplier:** When in doubt, multiply your initial estimate by 1.3. Scope creep, client feedback rounds, and admin overhead are always larger than expected.

---

## By Service Type

### Web & Digital

| Project Type | Typical Range | Common Underestimates |
|---|---|---|
| Landing page (design + copy) | 15–30h | Client revisions (add 20–40%) |
| Full marketing website (5–8 pages) | 40–80h | Content gathering from client |
| E-commerce site (Shopify/WooCommerce) | 60–120h | Product uploads, payment setup |
| Web app MVP (no-code / low-code) | 80–200h | User testing and iteration |
| Brand identity (logo + guidelines) | 20–50h | Concepts → revisions rounds |
| UI/UX redesign | 40–100h | Stakeholder alignment |

### Writing & Content

| Project Type | Typical Range | Common Underestimates |
|---|---|---|
| Blog post (1,500 words, researched) | 3–6h | Research depth varies hugely |
| Case study | 5–10h | Interview, transcript, approval loop |
| White paper / long-form report | 15–30h | Source gathering, expert review |
| Email sequence (5 emails) | 8–15h | Strategy + iterations |
| Website copy (5 pages) | 15–25h | Client briefs are never complete |
| Ghostwritten article (thought leadership) | 4–8h | Interview + multiple voice-matching rounds |

### Strategy & Consulting

| Project Type | Typical Range | Common Underestimates |
|---|---|---|
| Discovery / audit (research + report) | 10–25h | Async Q&A with client adds hours |
| Marketing strategy document | 20–40h | Competitive research is open-ended |
| Positioning workshop + output | 15–30h | Prep + facilitation + writeup |
| Go-to-market plan | 25–50h | Stakeholder interviews |
| Roadmap prioritization | 10–20h | Alignment discussions |

### Development

| Project Type | Typical Range | Common Underestimates |
|---|---|---|
| API integration | 10–30h | Documentation gaps, edge cases |
| Dashboard / data visualization | 20–60h | Data cleaning, UX iteration |
| Automation / workflow build | 8–25h | Testing and error handling |
| Chrome extension | 20–50h | Browser compatibility |
| Python script / tool | 10–40h | Requirements creep |

### Coaching & Training

| Project Type | Typical Range | Common Underestimates |
|---|---|---|
| Workshop (half day, with slides) | 10–20h | Prep is 3× the delivery time |
| Training course (5 modules) | 40–80h | Content design + feedback loops |
| Coaching program (12 sessions) | 15–25h (admin) | Session prep, notes, follow-up |

---

## The Revision Buffer Formula

Every deliverable should include a revision buffer:

| Client Relationship | Revision Buffer |
|---------------------|----------------|
| New client | +30–40% |
| Established client with clear brief | +15–20% |
| Returning client, well-briefed | +10–15% |
| Ongoing retainer (defined scope) | +5–10% |

**Why new clients get a bigger buffer:**
- Their idea of "a few small changes" and yours differ
- Brief quality is unknown until the first feedback round
- Trust has not yet been established — more explanation required

---

## The Scope Creep Forecast

Before starting any project, ask: "What is this project most likely to expand into?"

Common expansion patterns:

| Original Scope | Typical Expansion |
|---|---|
| Landing page | "Can you also do the email opt-in sequence?" |
| Brand identity | "Can you apply it to the website too?" |
| Marketing strategy | "Can you implement it?" |
| MVP build | "Just one more feature before launch" |
| Monthly retainer | "This is a bit more this month but will be lighter next month" |

**Prevention:** Name the expansion explicitly in the "Out of Scope" section of every proposal. Use `scope-management` skill for change request handling.

---

## Building Your Personal Baseline

After each project, log to `data/4-Archives/project-actuals/`:

```markdown
## [Project Name] — [Date]

| Metric | Estimated | Actual |
|--------|-----------|--------|
| Total hours | [X]h | [Y]h |
| Client feedback rounds | [X] | [Y] |
| Scope changes | 0 | [Y] |
| On-time delivery | Yes | Yes/No |

Accuracy ratio: [Y/X × 100]% (>100% = underestimated)

Notes: [What drove the difference?]
```

**After 10 projects**, patterns emerge:
- Your personal multiplier (e.g., "I consistently underestimate by 1.4×")
- Which project types you size well vs. poorly
- Which client types create the most revision rounds

The capacity-planner uses these actuals to calibrate future estimates.

---

## The "When Can I Start" Calculation

When a client asks for a start date:

```
Today: [date]
Projects finishing before start:
  - [Project A]: done by [date]
  - [Project B]: done by [date]

Earliest available: [date after last project clears]
Buffer for ramp-up: +3 working days
Realistic start: [date]
```

Always give a date 3 working days later than your math says. This buffer absorbs the inevitable "one more thing" from the closing project.
