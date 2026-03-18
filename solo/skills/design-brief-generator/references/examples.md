# Design Brief Examples

3 example design briefs for different project types.

---

## Example 1: Web App (Invoice Management)

See the complete example in the main SKILL.md file (Invoice Creation Flow with user flows, screen inventory, interaction patterns, visual requirements, and timeline).

---

## Example 2: Mobile App (Fitness Tracker)

```markdown
# Design Brief: Workout Logging Feature

**Created:** 2026-02-13  
**Based on:** PRD: Fitness App v2.0  
**Platform:** iOS + Android  
**Target Completion:** 2026-03-01

## Project Overview

**Problem:** Users struggle to log workouts quickly during gym sessions  
**Solution:** One-tap workout logging with pre-filled templates  
**Target User:** Gym-goers, 25-40, log 3-5 workouts/week

## User Flows

### Primary Flow: Quick Log

1. User opens app → Home screen
2. Taps "Start Workout" → Workout template selector
3. Selects template (e.g., "Upper Body") → Exercise list
4. Taps exercise, enters reps/weight → Logs set
5. Repeats for all exercises → Completes workout
6. Taps "Finish" → Workout summary

**Success Criteria:** Log workout in <2 minutes (currently 5-7 minutes)

## Screen Inventory

| Screen            | Purpose             | Key Elements                            |
| ----------------- | ------------------- | --------------------------------------- |
| Home              | Entry point         | "Start Workout" button, recent workouts |
| Template Selector | Choose workout type | Pre-made templates, custom option       |
| Exercise List     | Log exercises       | Exercise cards, add set button          |
| Set Logger        | Enter reps/weight   | Number input, quick increment buttons   |
| Summary           | Review workout      | Total volume, duration, save button     |

## Interaction Patterns

### Quick Increment Buttons

**When:** User enters reps/weight  
**What:** +/- buttons for quick adjustments (no typing)  
**Example:** Strong app's number picker

### Swipe to Complete

**When:** User finishes a set  
**What:** Swipe right to mark set complete  
**Example:** Todoist's swipe gesture

## Visual Requirements

**Brand:** Fitness-focused (energetic, motivating)  
**Colors:** Primary (#FF6B35 orange), Secondary (#004E89 blue)  
**Typography:** Montserrat (bold, athletic feel)  
**Accessibility:** WCAG AA, large touch targets (min 44px)

## Success Metrics

- Workout logging time: <2 minutes (from 5-7 minutes)
- Completion rate: 90%+ (users finish logging workout)
- Daily active users: +20%

## Timeline

| Phase      | Deliverable           | Due Date |
| ---------- | --------------------- | -------- |
| Wireframes | Lo-fi screens         | Feb 17   |
| Design     | Hi-fi mockups         | Feb 22   |
| Prototype  | Interactive prototype | Feb 27   |
| Handoff    | Dev specs             | Mar 1    |
```

---

## Example 3: Landing Page (SaaS Product)

```markdown
# Design Brief: Product Landing Page

**Created:** 2026-02-13  
**Based on:** Marketing Brief: Q1 Launch Campaign  
**Platform:** Web (responsive)  
**Target Completion:** 2026-02-20

## Project Overview

**Problem:** Current landing page has 2% conversion rate (industry avg: 5-10%)  
**Solution:** Redesign with clear value prop, social proof, and strong CTA  
**Target User:** Solopreneur designers, 30-40, looking for business tools

## User Flow

1. User arrives from ad/SEO → Hero section
2. Scrolls to see features → Feature section
3. Reads testimonials → Social proof section
4. Clicks "Start Free Trial" → Sign-up form

**Success Criteria:** 5%+ conversion rate (from 2%)

## Screen Inventory (Sections)

| Section      | Purpose           | Key Elements                                  |
| ------------ | ----------------- | --------------------------------------------- |
| Hero         | Hook + CTA        | Headline, subheadline, CTA button, hero image |
| Problem      | Show pain point   | Problem statement, relatable scenario         |
| Solution     | Show value prop   | 3 key benefits, screenshots                   |
| Features     | Detail features   | Feature cards with icons                      |
| Social Proof | Build trust       | Testimonials, logos, stats                    |
| Pricing      | Show pricing      | 3 tiers, feature comparison                   |
| FAQ          | Answer objections | 5-7 common questions                          |
| Final CTA    | Convert           | CTA button, guarantee                         |

## Visual Requirements

**Brand:** Professional but approachable  
**Colors:** Primary (#2563EB blue), Accent (#10B981 green)  
**Typography:** Inter (modern, clean)  
**Imagery:** Product screenshots, real user photos (not stock)

## Copy Requirements

**Headline:** Clear value prop in <10 words  
**Example:** "The only business tool solopreneurs need"

**Subheadline:** Expand on value prop in <20 words  
**Example:** "Manage clients, send invoices, and track projects in one place. No more tool overload."

**CTA:** Action-oriented, specific  
**Example:** "Start Free Trial" (not "Sign Up" or "Get Started")

## Success Metrics

- Conversion rate: 5%+ (from 2%)
- Bounce rate: <40% (from 60%)
- Time on page: 2+ minutes

## Timeline

| Phase       | Deliverable          | Due Date |
| ----------- | -------------------- | -------- |
| Wireframes  | Lo-fi layout         | Feb 15   |
| Copywriting | Headlines, body copy | Feb 16   |
| Design      | Hi-fi mockups        | Feb 18   |
| Development | Live page            | Feb 20   |
```

---

## How to Use These Examples

1. **Pick the closest match** — Web app, mobile app, or landing page
2. **Customize** — Replace project details, user flows, and requirements
3. **Add specifics** — Include actual PRD links, user research, and brand guidelines
4. **Share with team** — Use as handoff document for designers and developers

---

## Template Structure

Every design brief should include:

- **Project Overview** (problem, solution, target user)
- **User Flows** (step-by-step journey)
- **Screen Inventory** (list of screens/sections)
- **Interaction Patterns** (how users interact)
- **Visual Requirements** (brand, colors, typography)
- **Success Metrics** (how to measure success)
- **Timeline** (phases and deadlines)
