---
name: contract-templates
description: >
  Provides freelancer-friendly legal document templates with customization placeholders.
  Includes service agreements, NDAs, and clause library. Triggers on "draft contract",
  "NDA template", "service agreement", or "terms and conditions".
version: 1.0.0
bundle: client-work
triggers:
  - "create contract"
  - "freelance contract"
  - "NDA template"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Contract Templates

Provides a library of common legal templates for solopreneurs, with customization placeholders and a clause library for mix-and-match flexibility.

**Disclaimer:** These templates are for informational purposes only and do not constitute legal advice. Consult a legal professional before using. Templates default to French/EU law for solopreneurs.

## Template Library

| Template | Use Case | Reference |
|----------|----------|-----------|
| **Service Agreement** | Standard client engagement contract | `references/service-agreement.md` |
| **NDA** | Mutual non-disclosure before sharing sensitive info | `references/nda-template.md` |

## Customization Process

### Step 1: Select Template
Identify which template the user needs based on their request.

### Step 2: Gather Parameters
For a Service Agreement, collect:
- Your business name and SIRET
- Client name and company
- Service description (pull from proposal if exists)
- Total fee and payment schedule
- Start and end dates
- Deliverables list

### Step 3: Customize
Fill placeholders in the template. Apply relevant clauses from the clause library below.

### Step 4: Present with Disclaimer
Always remind the user: "This is a starting point. Have a legal professional review it before sending."

## Clause Library

Mix and match these clauses based on the engagement:

### Payment Terms
- **Standard:** "Payment due within [30] days of invoice date."
- **Milestone:** "50% upon project start, 50% upon final delivery."
- **Retainer:** "Monthly fee of [X] due on the 1st of each month."
- **Late payment (French law):** "Late payments incur penalties at 3x the legal interest rate, plus 40 EUR fixed recovery fee (Articles L441-10 and D441-5 Code de Commerce)."

### Intellectual Property
- **Full transfer:** "All work product becomes Client property upon full payment."
- **License:** "Service Provider retains ownership; Client receives an exclusive, perpetual license."
- **Portfolio rights:** "Service Provider may use anonymized work samples in their portfolio."

### Termination
- **Mutual notice:** "Either party may terminate with [14/30] days written notice."
- **For cause:** "Either party may terminate immediately for material breach if not cured within 10 days of written notice."
- **Kill fee:** "If Client terminates before completion, Client pays for all work completed plus [25%] of remaining scope."

### Liability
- **Cap:** "Service Provider's total liability shall not exceed the total fees paid under this Agreement."
- **Exclusion:** "Service Provider is not liable for indirect, consequential, or lost profit damages."

### Confidentiality
- **Mutual:** "Both parties agree to keep all confidential information private for [2] years."
- **One-way:** "Client information shared during the engagement is treated as confidential."

### Dispute Resolution
- **French law (default):** "This Agreement is governed by French law. Disputes shall be resolved by the courts of [City]."
- **Mediation first:** "Parties agree to attempt mediation before pursuing legal action."

## Jurisdiction Awareness

Default to French/EU law for solopreneurs:
- SIRET number instead of company registration
- TVA considerations (micro-entrepreneur exemption)
- French Commercial Code for late payment penalties
- RGPD (GDPR) data processing clause if applicable

## Key References

- **`references/service-agreement.md`**: Full service agreement template
- **`references/nda-template.md`**: Mutual NDA template
