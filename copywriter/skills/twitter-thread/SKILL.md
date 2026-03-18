---
name: twitter-thread
description: Craft viral Twitter/X threads. Optimized for hooks, retention, and "cliffhangers".
model: sonnet
bundle: social-content
triggers:
  - "write a Twitter thread"
  - "X thread about"
  - "craft a thread"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Twitter/X Thread Architect

This skill designs threads that "stop the scroll" and maximize retweets. It understands the unique cadence of X: punchy, visual, and high-velocity.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Hook Engineering: Viral openers (Contrarian, Data, Story).   │
│  ✓ Pacing: 1 idea per tweet + "Bridge Tweets".                  │
│  ✓ CTA: Thread-ending offer or newsletter plug.                 │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~linkedin-post)                         │
│  + Repurposing: Converts LinkedIn posts to 10-tweet threads.    │
│  + Visuals: Suggests image/chart concepts for Tweet 1.          │
│  + Anti-Slop: Scrubs "corporate" language for "native" tone.    │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "Turn this idea into a thread"
- "Write a twitter thread about [Topic]"
- "Repurpose this article for X"

## 🛠 Agent Instructions

### Before Writing

1.  **Load Context Profiles**:
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/voice-dna.json` (Crucial for "Twitter Voice").
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/icp.json` (What hooks them?).
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/business-profile.json` (Where are we driving traffic?).

---

## 🏛 The Thread Architecture

### 1. The Hook (Tweet 1)

- **Goal**: The only goal is to get them to read Tweet 2.
- **Formats**:
  - _The "Hero's Journey"_: "I lost $10k. Here's how."
  - _The "Listicle"_: "10 tools to replace your team."
  - _The "Contrarian"_: "SEO is dead. Here is why."

### 2. The Meat (Tweets 2-N)

- **One Tip Per Tweet**: Never stack ideas.
- **Whitespace**: Use line breaks aggressively.
- **The Bridge**: Use "Bucket Brigades" (e.g., "But that's not all...", "Here is the crazy part...").

### 3. The CTA (The Last Tweet)

- **The Ask**: "If you enjoyed this, RT the first tweet." (Growth).
- **The Plug**: "Sub to my newsletter." (Conversion).

---

## 📝 Output Format

```markdown
# Twitter Thread Draft

**Hook Style**: [Chosen Style]

---

**1/ [The Hook]**
[Text]
[Image Concept]

**2/ [Context]**
[Text]

**3/ [Point 1]**
[Text]

...

**10/ [The Summary]**
TL;DR:

1.
2.
3.

**11/ [The CTA]**
If you found value:

1. Follow @[Handle] for more.
2. RT the first tweet to share.
```
