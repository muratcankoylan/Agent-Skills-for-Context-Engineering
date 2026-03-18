---
description: "Quick start onboarding - set up your Solo profile in 3 minutes"
argument-hint: "[profile-type: content|service|product|full]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /solo:start

Welcome! Let's get you set up with Solo. This will take about 3 minutes.

## Quick Start Path

I'll help you configure Solo based on how you work. Choose one:

**1. Content Creator** - Blogs, newsletters, social media  
**2. Service Provider** - Freelancing, consulting, client work  
**3. Product Builder** - SaaS, digital products, prototypes  
**4. Full Setup** - All features (recommended for later)

> If you're not sure, pick **Service Provider** - it's the most versatile starting point.

---

## What I'll Set Up

Based on your choice, I'll:

1. Create your business profile (who you are, what you do)
2. Capture your writing voice (so content sounds like you)
3. Define your ideal client (who you help)
4. Enable relevant skills (only what you need)
5. Set up your PARA file structure

Everything stays local on your machine.

---

## Onboarding Flow

### Step 0: Language Selection (New)

First, I'll ask for your preferred language:

1. **English** (Default)
2. **Français**

I'll save this to `business-profile.json` so all future outputs use your language.

---

### Step 1: Choose Your Profile (30 seconds)

I'll ask: "Which best describes you?"

**If Content Creator:**

- Enable: voice-dna-creator, content-calendar-planner, newsletter-writer, linkedin-post, seo-blog-writer
- Skip: client-management, invoice-generator, pipeline-orchestrator
- Primary commands: `/solo:write`, `/solo:plan`

**If Service Provider:**

- Enable: business-profile-creator, client-management, invoice-generator, proposal-generator, discovery-call
- Skip: pipeline-orchestrator, remotion-video-generator
- Primary commands: `/solo:clients`, `/solo:invoice`, `/solo:prospect`

**If Product Builder:**

- Enable: pipeline-orchestrator, prd-development, validation-checkpoint, figma-prototype, user-story
- Skip: invoice-generator, newsletter-writer
- Primary commands: `/solo:build`, `/solo:research`

**If Full Setup:**

- Enable: All 60+ skills
- All commands available
- Longer onboarding (~10 minutes)

---

### Step 2: Quick Profile Questions (2 minutes)

I'll ask 5-7 questions based on your profile choice:

#### For Everyone:

1. "What do you do in one sentence?"
2. "Who do you help?"
3. "Share a writing sample or describe your style"

#### Service Provider Extra:

4. "What services do you offer?"
5. "What's your typical rate? (hourly/project/retainer)"
6. "Describe your ideal client"

#### Product Builder Extra:

4. "What problem are you solving?"
5. "Who is your target user?"
6. "What's your current stage? (idea/mvp/launched)"

#### Content Creator Extra:

4. "What platforms do you publish on?"
5. "How often do you publish?"
6. "What topics do you cover?"

---

### Step 3: File Structure Setup (30 seconds)

I'll create:

```
solo/data/
├── 0-Inbox/              # New items land here
├── 1-Projets/            # Active work
│   ├── clients/          # (Service Provider only)
│   ├── invoices/         # (Service Provider only)
│   └── products/         # (Product Builder only)
├── 2-Domaines/           # Your identity
│   ├── business-profile.json
│   ├── voice-dna.json
│   └── icp.json
├── 3-Ressources/         # Templates & knowledge
└── 4-Archives/           # Completed items
```

---

### Step 4: Activation Summary (30 seconds)

```
✅ Solo Setup Complete!

Your Profile: Service Provider
Enabled Features: 8/60 skills

📝 Your Identity
- Business: [Your business name]
- Focus: [What you do]
- Clients: [Who you help]

🚀 Next Steps
1. Add your first client: /solo:clients add
2. Create an invoice: /solo:invoice
3. Browse all features: /solo:skills

💡 Tips
- Enable more skills anytime: /solo:skills
- Check connections: /solo:check-connections
- Get help: /solo:help
```

---

## Workflow Examples

### Content Creator Workflow

```
> /solo:write blog "productivity tips"
[Generates SEO-optimized blog post in your voice]

> /solo:plan
[Creates content calendar for next month]

> /solo:write newsletter
[Generates newsletter from recent blog posts]
```

### Service Provider Workflow

```
> /solo:clients add
[Interactive form to add new client]

> /solo:invoice "Acme Corp"
[Generates professional invoice]

> /solo:prospect research "SaaS companies in fintech"
[Finds leads, drafts outreach]
```

### Product Builder Workflow

```
> /solo:build discover
[Starts discovery phase: persona, problem, journey]

> /solo:build validate
[Runs validation checkpoint]

> /solo:build design
[Creates PRD and design brief]

> /solo:build prototype
[Generates interactive prototype]
```

---

## Advanced Options

### Skip Onboarding (If You Have Existing Docs)

```
/solo:start --scan path/to/your/docs/
```

I'll analyze your existing materials to extract:

- Business positioning from pitch decks
- Writing voice from blog posts
- Client profile from proposals

### Update Your Profile Later

```
/solo:start --update business
/solo:start --update voice
/solo:start --update icp
```

Re-run any section without starting over.

### Switch Profile Type

```
/solo:configure profile content-creator
```

Enable different skill sets as you grow.

---

## Agent Instructions

### Execution Steps

```python
config_file = "${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/skill-config.json"
if file_exists(config_file):
    ask("You're already set up. Want to: [Update] [Reset] [Cancel]?")
```

2. **Language Selection**

   ```python
   language = ask_choice(["English", "Français"])
   lang_code = "fr" if language == "Français" else "en"
   ```

3. **Profile selection**

   ```python
   profile = ask_choice([
       "Content Creator - blogs, newsletters, social",
       "Service Provider - freelancing, consulting",
       "Product Builder - SaaS, digital products",
       "Full Setup - everything (advanced)"
   ])
   ```

4. **Run appropriate profile setup**

   ```python
   if profile == "service-provider":
       run_skill("business-profile-creator", quick_mode=True, language=lang_code)
       run_skill("voice-dna-creator", quick_mode=True, language=lang_code)
       run_skill("icp-creator", quick_mode=True, language=lang_code)
       enable_skills([
           "client-management",
           "invoice-generator",
           "proposal-generator",
           "discovery-call",
           "pricing-strategy"
       ])
   ```

5. **Create PARA structure**

   ```bash
   mkdir -p ${CLAUDE_PLUGIN_ROOT}/data/{0-Inbox,1-Projets,2-Domaines,3-Ressources,4-Archives}

   # Profile-specific subdirectories
   if [[ $profile == "service-provider" ]]; then
       mkdir -p ${CLAUDE_PLUGIN_ROOT}/data/1-Projets/{clients,invoices,proposals}
   fi
   ```

6. **Save configuration**

   ```json
   {
     "profile": "service-provider",
     "language": "fr",
     "enabled_skills": ["client-management", "invoice-generator", ...],
     "onboarding_complete": true,
     "onboarding_date": "2026-02-13",
     "version": "2.0.0"
   }
   ```

7. **Update CLAUDE.md**

   ```markdown
   # Solo-Brain: Working Memory

   ## 👤 Me

   - **Name:** [from business-profile]
   - **Business:** [from business-profile]
   - **Profile:** Service Provider
   - **Focus:** [from business-profile]

   ## 🎯 Active Skills (8 enabled)

   - client-management
   - invoice-generator
   - proposal-generator
     ...
   ```

8. **Show completion summary**

---

## Error Handling

### If files already exist

```
⚠️  Found existing configuration:
- business-profile.json (created 2026-01-15)
- voice-dna.json (created 2026-01-15)

Options:
[Update] - Keep existing, update specific sections
[Reset] - Start fresh (backs up old files)
[Cancel] - Exit without changes
```

### If user cancels mid-flow

```
Saving partial progress...
✅ Saved: business-profile.json
⏸️  Paused: voice-dna.json (incomplete)

Resume anytime with: /solo:start --resume
```

### If invalid input

```
❌ Business description is required.

Let's try again. What do you do in one sentence?
Example: "I help B2B SaaS founders reduce churn through customer success consulting"
```

---

## Success Criteria

Onboarding is complete when:

- ✅ Profile type selected
- ✅ 3 identity files created (business-profile, voice-dna, icp)
- ✅ PARA directories exist
- ✅ skill-config.json saved
- ✅ CLAUDE.md updated
- ✅ User sees "Next Steps" summary

---

## Tips for Users

1. **Be specific** - "I help B2B SaaS founders reduce churn" beats "I help businesses grow"
2. **Bring examples** - One blog post tells me more than 10 descriptions
3. **Start narrow** - Choose one profile, enable more features later
4. **You can redo anything** - `/solo:start --update voice` to refresh just your writing style
5. **Everything is local** - Your data stays on your machine unless you connect cloud tools

---

## What Happens Next

After onboarding, you can:

- **Add your first client:** `/solo:clients add`
- **Create content:** `/solo:write [type]`
- **Research your market:** `/solo:research [topic]`
- **Check what's connected:** `/solo:check-connections`
- **Browse all skills:** `/solo:skills`
- **Get help:** `/solo:help [topic]`

The plugin learns as you use it - commands become more contextual over time.
