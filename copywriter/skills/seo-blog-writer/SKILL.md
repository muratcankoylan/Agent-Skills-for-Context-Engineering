---
name: seo-blog-writer
description: >
  Create comprehensive, SEO-optimized blog posts that rank in search engines and establish authority. Includes deep E-E-A-T compliance.
  Trigger with "write a blog post", "write a how-to guide", "thought leadership post", "authoritative essay", or "SEO article about".
model: sonnet
bundle: content-strategy
triggers:
  - "write a blog post"
  - "SEO article about"
  - "thought leadership post"
tools:
  standalone: []
  supercharged: [WebSearch]
version: 1.0.0
---

# SEO Blog Writer

This skill creates high-ranking, authoritative blog content. It doesn't just "write a post"; it constructs a semantic resource optimized for Google's E-E-A-T guidelines.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ E-E-A-T Structure: Automatic "Experience" injection.         │
│  ✓ SEO Optimization: Keyword placement & header hierarchy.      │
│  ✓ Anti-Slop Check: Filters corporate jargon automatically.     │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~web_search / WordPress)                │
│  + Live Research: Cites real-time stats and news.               │
│  + Competitor Gap Analysis: Reads top 3 results to beat them.   │
│  + Auto-Publish: Deploys directly to your CMS via MCP.          │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "Write a blog post about [Topic]"
- "Turn this transcript into an SEO article"
- "Update this old post to rank better"
- "Create a content outline for [Keyword]"

## 🛠 Agent Instructions

### Before Writing

1.  **Load Context Profiles**:
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/voice-dna.json` to match the user's voice precisely.
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/icp.json` to align with the audience's pain points.
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/business-profile.json` to ensure alignment with offers.
2.  **Check Source Material**:
    - If repurposing, search `${CLAUDE_PLUGIN_ROOT}/data/3-Resources/`.
    - If researching, use `exa-search-expert` or `web_search`.

### 2. SEO Parameters

Before writing, confirm or define:

- **Secondary Keywords**: 3-5 LSI (Latent Semantic Indexing) keywords.
- **Search Intent**: Informational, Commercial, or Transactional?

---

## 🏛 The "Rank-Worthy" Architecture

Rank-worthy content follows a specific psychological and structural flow.

### Phase 1: The Hook & Introduction

- **The Problem**: Address `{{icp.pain_points}}` immediately.
- **The Agitation**: Why hasn't it been solved yet?
- **The Solution**: Your unique mechanism.
- **The Promise**: "By the end of this guide, you will..."

### Phase 2: The Meat (H2s and H3s)

- **Structure**: Use logical headers.
- **Snippet Bait**: Definitive answers placed immediately after headers.
- **Anti-Slop**: Compare constantly against `{{voice_dna.forbidden_words}}`.

### Phase 3: The Conclusion & CTA

- **Summary**: Recap main takeaways.
- **CTA**: Connect value to `{{business.primary_cta}}`.

---

## ✍️ Step-by-Step Writing Process

### Step 1: Outline Generation

Create a skeletal outline.

1.  **H1 Title**: Must include Primary Keyword.
2.  **Meta Description**: <160 chars.
3.  **Header Hierarchy**: List H2s/H3s.

### Step 2: Drafting (The Deep Work)

Write section by section.

- **Tone Check**: Ensure `{{voice_dna.tone}}` is respected.
- **Experience**: Use "I" statements to demonstrate E-E-A-T.

### Step 3: Optimization

- **Internal Links**: Suggest linking to `data/3-Resources`.
- **External Links**: Cite 2-3 authoritative sources.

---

## 📝 Output Format

Deliver the final artifact as a Markdown file.

```markdown
# [Title]

**Meta Description**: [Text]
**Slug**: [url-slug]
**Primary Keyword**: [Keyword]

---

[Introduction matching {{voice_dna.tone}}]

## [H2 Header]

[Content addressing {{icp.pain_points}}...]

> [!TIP]
> [Actionable advice]

## Conclusion

[Summary]

**[CTA Headline]**
[CTA Body aligned with {{business.primary_cta}}]
[Link]
```
