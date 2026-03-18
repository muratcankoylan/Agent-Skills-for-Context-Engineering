---
name: email-coach
description: >
  Real-time review of sales emails before you hit send. Catches weak subject lines, slop phrases,
  poor CTAs, tone mismatches, and structural issues. Returns a scored review with a rewrite.
  Triggers: "review this email before I send it", "is this email good?", "improve my follow-up", "score this outreach".
bundle: coaching-quality
triggers:
  - "review this email before I send it"
  - "is this email good?"
  - "score this outreach"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Skill: Email Coach

The last line of defense between a weak email and your prospect's inbox.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ 5-dimension email score (0–100)                             │
│  ✓ Subject line analysis + 3 alternatives                      │
│  ✓ Slop detection: kills "Hope this finds you well" and kin    │
│  ✓ CTA strength check: clear ask or vague hope?                │
│  ✓ Full rewrite in your Voice DNA                               │
│  ✓ Bilingual: EN and FR email norms are different — we know    │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~email)                                 │
│  + Pull prospect's email history for context                    │
│  + Check CRM for prior commitments to reference                 │
│  + A/B subject line testing recommendations                     │
└─────────────────────────────────────────────────────────────────┘
```

## 🧠 Core Philosophy

1. **Every word must earn its place**: If removing a sentence makes the email no worse, remove it.
2. **One email, one ask**: If the email asks for two things, it gets zero.
3. **Prospects don't owe you attention**: The email must earn it in the first line.
4. **Authentic > polished**: A slightly rough email that sounds human beats a perfectly polished template that reads like GPT output.

---

## 🛠 Agent Instructions

### Phase 1: Score the Email

**Trigger**: User pastes an email.

**Load Context**:
- `data/2-Domaines/voice-dna.json` — What does the user's natural voice sound like?
- `data/2-Domaines/icp.json` — Who is this email going to?
- `data/2-Domaines/sales-profile.json` — What language mode?

**Score on 5 Dimensions** (20 points each):

#### 1. Subject Line (20 pts)
See `references/subject-line-guide.md` for full criteria.
- Length (3–6 words ideal): +5
- Lowercase formatting: +5
- Curiosity gap or specificity: +5
- No click-bait or dishonest framing: +5

#### 2. Opening Line (20 pts)
The first sentence must hook or it's over.
- Does NOT start with "I", "We", or "Hope": +5
- References something prospect-specific (news, trigger event, their words): +7
- Creates forward momentum (opens a loop vs. closes with pleasantry): +8

#### 3. Body (20 pts)
- < 100 words for cold outreach, < 150 for follow-up: +5
- Problem-framing before solution (they care about pain, not features): +7
- No hollow adjectives (seamless, robust, cutting-edge): +4
- Antislop pass clean: +4

#### 4. CTA (20 pts)
- Exactly one ask (not "let me know if interested" + "would love to connect" + "check out our site"): +7
- Specific and low-friction (15-min call > "a conversation at your convenience"): +7
- Makes it easy to say yes AND easy to say no: +6

#### 5. Voice Match (20 pts)
Compare against `voice-dna.json`:
- Matches sentence length variance: +5
- Contains signature phrases or structural patterns: +5
- Free of forbidden words in voice-dna: +5
- Tonal match (formal/casual, warm/direct): +5

**Thresholds**:
- 80–100: Strong. Send as-is or with minor tweaks.
- 60–79: Decent. One clear area to fix.
- 40–59: Needs work. Two or more structural issues.
- Below 40: Do not send. Full rewrite recommended.

---

### Phase 2: Line-by-Line Annotations

Output the email with inline comments. Format:

```
[ORIGINAL]: Hope this email finds you well.
[FLAG]: Slop opener — costs you credibility before your first real sentence. Delete entirely.

[ORIGINAL]: I wanted to reach out because I noticed you recently expanded to DACH.
[GOOD]: Strong hook — specific trigger event. Keep this but move it to line 1.

[ORIGINAL]: Our platform is a seamless solution that helps companies like yours...
[FLAG]: "Seamless" is hollow. "Companies like yours" is lazy. Replace with the specific problem you solve.
```

---

### Phase 3: Rewrite

**Always offer a full rewrite** after the score. The rewrite must:
- Preserve the user's voice (from `voice-dna.json`) — not default to corporate English
- Keep the prospect's context (company, name, trigger event if provided)
- Score ≥ 80 on the same rubric

**Output Format for Rewrite**:

```markdown
## ✉️ Rewrite

**Subject**: [new subject]

[Body — paragraph format, not bullet points, < 100 words for cold]

---

### What Changed

1. **Subject**: Changed from "[old]" → "[new]" because [reason]
2. **Opener**: Moved trigger event to line 1
3. **Body**: Removed [specific hollow phrase]; replaced with [specific claim]
4. **CTA**: Consolidated to one specific ask
```

---

### Phase 4: Subject Line Alternatives

Always provide 3 alternative subject lines with explanations:

| Subject | Strategy | Why It Works |
|---------|----------|-------------|
| [Option 1] | Curiosity Gap | [Explanation] |
| [Option 2] | Specificity | [Explanation] |
| [Option 3] | Direct/Provocative | [Explanation] |

---

## Language Mode (FR)

If `language_preference == "fr"`:

**French email norms differ from English**:
- Formal opener is standard for first contact: "Bonjour [Prénom]," (never "Salut")
- Sentence length is naturally longer — don't over-shorten
- Vouvoiement (vous) vs. tutoiement (tu): default to vous unless ICP is a startup environment
- Subject line in French: lowercase rules apply, but full sentences are more acceptable
- CTA phrasing: "Seriez-vous disponible 15 minutes cette semaine?" > "Grab 15 minutes?"

---

## 📂 System Integration

- **Antislop**: Run `antislop-expert` logic on every email before scoring
- **Voice DNA**: All rewrites must pass Voice DNA match check
- **Output**: Optionally save reviewed email to `data/1-Projets/campaigns/[campaign]-reviewed.md`

## 📚 References

- `references/subject-line-guide.md`: Subject line formulas, do/don't examples, EN + FR.
- `references/cta-patterns.md`: CTAs ranked by conversion strength with examples.
- `references/before-after-examples.md`: Real before/after rewrites demonstrating the scoring rubric.
