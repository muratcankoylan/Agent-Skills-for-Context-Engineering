---
description: "Unified Copywriting Command: Blog, Social, Newsletter, Script, Sales"
argument-hint: "[blog | social | newsletter | script | sales] [topic]"
allowed-tools: Read, Write, WebSearch, WebFetch
model: sonnet
---

# /copywriter:write

Your All-In-One Copywriting Studio. Generate world-class content for any channel.

## Usage

```bash
/copywriter:write blog "AI for Lawyers"          # SEO Deep Dive
/copywriter:write social "My biggest failure"    # LinkedIn/Twitter Viral Post
/copywriter:write newsletter "Weekly Roundup"    # Email to list
/copywriter:write script "How to use ChatGPT"    # YouTube/TikTok Script
/copywriter:write sales "Course Launch"          # Sales Email Sequence
```

---

## 🏗 content_router

When executed, the agent analyzes the `intent` (first argument) and routes to the specific **Agent Specialist**.

| Argument     | Agent Triggered    | Output Goal                      |
| :----------- | :----------------- | :------------------------------- |
| `blog`       | `blog-agent`       | SEO-Optimized Article (Markdown) |
| `social`     | `social-agent`     | LinkedIn Post + Twitter Thread   |
| `newsletter` | `newsletter-agent` | Structured Email Draft           |
| `script`     | `script-agent`     | Visual A-Roll/B-Roll Script      |
| `sales`      | `sales-copy-agent` | Conversion-Focused Sequence      |

---

## /copywriter:write blog

**Focus**: E-E-A-T, SEO Structure, Depth.
**Skill Chain**: `web_search` -> `title-brain` -> `seo-blog-writer` -> `antislop-expert`.

### Example

`User: /copywriter:write blog "The future of remote work"`

**Agent Action**:

1.  **LOAD CONTEXT**: Read `data/2-Domaines/voice-dna.json`, `icp.json`, and `business-profile.json`.
2.  Research "remote work trends 2026".
3.  Generate 5 Hook Titles.
4.  Draft 1,500 words using `{{voice_dna.tone}}`.
5.  Apply `antislop` check.

---

## /copywriter:write social

**Focus**: Hooks, Whitespace, Virality.
**Skill Chain**: `title-brain` -> `linkedin-post` / `twitter-thread`.

### Example

`User: /copywriter:write social "I quit my job"`

**Agent Action**:

1.  **LOAD CONTEXT**: Read `voice-dna.json` to capture the Tone.
2.  Draft LinkedIn "Story Post" (Hook -> Conflict -> Lesson).
3.  Draft Twitter Thread (10 Tweets).
4.  Suggest Image/Visual.

---

## /copywriter:write script

**Focus**: Visual Retention, Pattern Interrupts.
**Skill Chain**: `video-script-generator`.

### Example

`User: /copywriter:write script "Review of iPhone 16"`

**Agent Action**:

1.  **LOAD CONTEXT**: Read `icp.json` to understand the Viewer's retention triggers.
2.  Ask: "YouTube Long Form or TikTok?"
3.  Draft Script with [Visual Cues] and Timecodes.

---

## /copywriter:write sales

**Focus**: Conversion, Scarcity, Psychology.
**Skill Chain**: `sales-email-sequence`.

### Example

`User: /copywriter:write sales "Black Friday Sale"`

**Agent Action**:

1.  **LOAD CONTEXT**: Read `business-profile.json` (Offer) and `icp.json` (Pain).
2.  Draft 5-Email "Cash Injection" Sequence.
3.  Include Subject Lines, Previews, and CTAs.
