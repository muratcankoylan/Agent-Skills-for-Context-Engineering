# Test Method Catalog

Detailed setup for each of the 5 idea-test methods.

---

## 1. Smoke Test / Fake Door

**What it is:** A landing page or button that looks real but leads to a "coming soon" or waitlist message. Measures genuine demand by tracking who clicks / signs up before you build anything.

**When to use:** You want to know if people will actively seek out this solution. No workaround exists yet.

**Setup (1–3 days):**
1. Write one sentence: the core value proposition
2. Build a minimal landing page: headline + 3 bullet benefits + email sign-up (Carrd, Typedream, or a single Notion page)
3. Add one call-to-action: "Get early access" or "Join the waitlist"
4. Drive 100–500 targeted visitors (Reddit post, Twitter/X thread, a direct message to 20 people who fit the ICP, or €20 in ads)

**Success criteria examples:**
- 10%+ conversion (visitors → signups) = strong signal
- 5–10% = interesting, needs more traffic or tighter copy
- < 5% = weak signal — problem framing or audience targeting is off

**Disposal:** Archive the page after the test. Don't iterate into a real product until you've committed to building.

---

## 2. Concierge MVP

**What it is:** You manually deliver the value your product would deliver, using existing tools (email, spreadsheets, Google Docs, WhatsApp). No code. The user gets real value; you learn whether they use it and pay for it.

**When to use:** The product is an information/service workflow. You can do it manually for 5–10 users.

**Setup (3–7 days):**
1. Find 3–5 people who fit the ICP and have the problem
2. Offer to do the thing for them for free (or a small fee)
3. Do it manually using whatever tools you have
4. Observe: Do they engage? Do they come back? Would they pay?

**Success criteria examples:**
- 3/5 users engaged meaningfully + at least 1 said "I'd pay for this" = strong signal
- Users gave you more requests / referrals = strong signal
- Users were polite but didn't act on the output = weak signal

**Key insight:** If you can't deliver value manually, the product won't deliver it automatically either.

---

## 3. Wizard of Oz

**What it is:** A product-looking interface where the "automation" is actually a human doing work behind the scenes. Users think they're using software; you're manually fulfilling each request.

**When to use:** The UX and flow matter (not just the output), but the automation is what's hard to build. You want to validate the workflow before engineering it.

**Setup (3–7 days):**
1. Build a minimal interface (Typeform, Airtable form, a fake app page)
2. When a user submits, you receive a notification and manually complete the work
3. Deliver the result back as if it were automated (email reply, Slack message)
4. Watch for friction: confusion, missing information, wrong expectations

**Success criteria examples:**
- Users complete the workflow without asking "wait, how does this work?" = strong UX signal
- Users return and use it again = strong habit signal
- Users get stuck at a specific step = valuable friction map for design

---

## 4. Narrative / Video

**What it is:** A short video (2–5 min) or illustrated walkthrough that shows the product working — without the product existing. Like a product demo video, but fictional.

**When to use:** The concept is complex and needs showing, not telling. Or you need stakeholder/investor buy-in before committing to build.

**Setup (1–2 days):**
1. Write a simple script: problem → solution → result
2. Record a Loom walkthrough using mockups, slides, or even paper sketches
3. Share with 5–10 target users and ask: "Does this solve a problem you have?"
4. Watch their reaction — do they lean in, ask follow-up questions, want to try it?

**Success criteria examples:**
- "When is this available?" or "How do I sign up?" = strong signal
- "That's interesting" or "I can see how that would help some people" = weak signal
- "I don't quite get what it does" = your narrative needs work before building

---

## 5. Spike / Feasibility Check

**What it is:** A small technical experiment (1–2 days of code, throwaway) to answer a specific technical question. Not a prototype — just enough to confirm or deny one assumption.

**When to use:** The biggest risk is technical, not demand-based. You're not sure the key capability is achievable with your stack, time, or budget.

**Setup (1–2 days):**
1. Write the one technical question as precisely as possible: "Can I parse X from Y API in under 200ms?"
2. Write the minimum code to answer it — nothing else
3. Test it against real data or constraints
4. Document: Pass / Fail / Partial + what you learned

**Success criteria examples:**
- The capability works within your constraints → technically feasible, move forward
- It works but is too slow / expensive → need a different approach (pivot or constraint)
- It doesn't work at all → the core assumption is false (stop or redesign)

**Disposal:** Delete all spike code after documenting results. Never ship spike code.
