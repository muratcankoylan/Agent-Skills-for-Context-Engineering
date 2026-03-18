---
name: prd-development
description: >
  Turns your problem statement and persona into a one-page build spec.
  Defines what to build, who it's for, the v1 feature scope, and exactly when it's done.
  Trigger with "write a build spec", "what should I build", "define the MVP",
  "write my spec", "scope the first version", or "create a PRD".
version: 2.0.0
bundle: product-build
triggers:
  - "create PRD"
  - "product requirements"
  - "write PRD for"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Build Spec (PRD)

Produces a one-page spec you can code from, or hand to a freelancer, in 30 minutes.

This is not a strategy document — it answers five questions and stops. Read it in two minutes, build from it directly.

---

## When to Use

After validation (`idea-test`) returns a GO decision. You have a confirmed problem and a persona. Now you need to define exactly what to build for v1.

If you haven't validated yet, run `/solo:build validate` first.

---

## The 5-Section Build Spec

### Section 1: What

One paragraph. What are we building and what does it do?

**Template:**
> [Product name] is a [type of thing] that lets [who] [do what] so they can [outcome].
> It works by [brief mechanism]. The v1 focus is [one core loop].

**Example:**
> InvoiceBot is a Claude command that lets freelancers generate professional invoices from a single chat message so they can bill clients in under 2 minutes instead of 20.
> It works by reading client details from a local markdown file and filling an invoice template. The v1 focus is: one command → one invoice → one PDF.

---

### Section 2: Who

Don't repeat the full persona — link to it and add one sentence of context.

**Template:**
> Primary user: [persona name] (see `persona.md`)
> This spec is scoped for [one specific situation they're in].

**Example:**
> Primary user: Solopreneur Sarah (see `data/1-Projets/invoicebot/persona.md`)
> This spec is scoped for when she finishes a project and needs to invoice the client the same day.

---

### Section 3: Why

The specific pain being solved. Two sentences maximum — no strategy, no market sizing.

**Template:**
> [Persona] currently [pain behavior]. This costs them [time/money/frustration].
> We're building this because [evidence from discovery or validation].

**Example:**
> Sarah currently manually copies client details into a Google Docs invoice template, exports to PDF, then emails it. This takes 20–30 minutes per invoice and she invoices 4–6 clients a month.
> We're building this because 5/5 discovery interviewees said invoice admin is their most hated task.

---

### Section 4: Scope (v1 only)

Bulleted feature list. Ruthlessly minimal. Everything not listed is explicitly excluded.

**Rules:**
- Each feature is one thing a user can do
- If a feature needs more than 2 days to build, split it or cut it
- The "Not in v1" list is as important as the "In v1" list — it's a written commitment

**Template:**
```
**In v1:**
- [ ] [Feature: what the user can do]
- [ ] [Feature: what the user can do]

**Not in v1:**
- [Thing that seems necessary but isn't core]
- [Thing users might ask for but can wait]
```

**Example:**
```
**In v1:**
- [ ] Generate an invoice from a single Claude command (`/solo:invoice create Client Amount`)
- [ ] Auto-number invoices (INV-YYYY-001 format)
- [ ] Read client name and address from `clients/[name].md`
- [ ] Output a formatted markdown invoice to `invoices/`

**Not in v1:**
- PDF export (markdown copy-paste works for now)
- Payment tracking (separate command)
- Multi-currency support
- Invoice templates / branding
```

---

### Section 5: Done When

3–5 plain-English criteria. If all are true, ship it.

**Rules:**
- Each criterion is observable — you can check it without ambiguity
- Written from the user's perspective, not the developer's
- No metrics tables, no secondary metrics, no OKRs

**Template:**
```
**Done when:**
- [ ] A user can [do X] without [needing Y]
- [ ] [Specific behavior] works correctly
- [ ] [Edge case] is handled with a clear message
```

**Example:**
```
**Done when:**
- [ ] Sarah can run `/solo:invoice create` and get a correctly numbered invoice in under 2 minutes
- [ ] Invoice reads client address correctly from the client file
- [ ] Running the command twice doesn't duplicate the invoice number
- [ ] A clear error message appears if the client file doesn't exist
```

---

## How to Write It

1. Open the relevant discovery files:
   - `data/1-Projets/[project]/persona.md`
   - `data/1-Projets/[project]/problem.md`
   - `data/1-Projets/[project]/validation-results.md`

2. Fill sections in order — don't jump to features until you've written What and Why

3. Review Section 4: ask "what can I cut and still have a usable thing?" Cut that.

4. Save to `data/1-Projets/[project]/PRD.md`

5. Hand off to the `user-story` skill to break each feature into feature cards

---

## Tips

**One user, one problem.** If Section 2 has two personas or Section 3 has two problems, you have two products. Pick one.

**Features are not requirements.** "Export to PDF" is a feature. "PDF must comply with French invoice law" is a requirement — and a reason to cut it from v1.

**"Not in v1" is a written promise.** It prevents scope creep mid-build and gives you a ready-made v2 list.

**30 minutes is enough.** If writing the spec takes longer, the product idea isn't clear yet. Stop and return to discovery.
