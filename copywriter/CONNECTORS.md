# Connectors & Integrations

The `copywriter` plugin works **Standalone** (out of the box) and can be **Supercharged** by connecting external tools via MCP.

## Integration Overview

| Category | Placeholder | Default | Alternatives |
| :------- | :---------- | :------ | :----------- |
| **CMS** | `~~CMS` | WordPress MCP | Ghost, Webflow, Notion |
| **Search** | `~~search` | WebSearch (built-in) | Exa, Tavily |
| **Social** | `~~social` | LinkedIn MCP | Buffer, Twitter/X API |
| **Files** | `~~filesystem` | Filesystem MCP | Google Drive, Dropbox |
| **Email** | `~~email-platform` | (manual export) | Beehiiv, Mailchimp, ConvertKit |

---

## Fallback Logic

If a connector is **not** configured, the plugin degrades gracefully:

- **~~CMS** → Generates a Markdown file ready to copy-paste into your CMS.
- **~~search** → Uses Claude's built-in `WebSearch`.
- **~~social** → Generates a formatted text file ready to paste.
- **~~email-platform** → Outputs plain HTML + text version for manual import.

---

## Configuration Examples

### WordPress (~~CMS)

```json
"wordpress": {
  "command": "npx",
  "args": ["-y", "@wordpress/mcp-server", "--url", "https://your-site.com", "--username", "your-user", "--password", "your-app-password"]
}
```

### Exa Search (~~search)

```json
"exa-search": {
  "command": "npx",
  "args": ["-y", "exa-mcp-server", "--api-key", "YOUR_EXA_KEY"]
}
```

### LinkedIn (~~social)

Configure via your LinkedIn MCP provider. Run `/copywriter:check-connections` to verify status.

---

## Companion Plugins

| Plugin | Handles | Install |
| :----- | :------ | :------ |
| **solo** | Business profile, ICP, Voice DNA, client management, invoicing, pipeline | `knowledge-work-plugins/solo` |
| **solo-studio** | Figma prototypes, Remotion demo videos, Stitch mockups | `knowledge-work-plugins/solo-studio` |

**Shared data files**: Solo creates `data/2-Areas/voice-dna.json`, `data/2-Areas/icp.json`, and `data/2-Areas/business-profile.json`. Copywriter reads these automatically — no reconfiguration needed. Install solo first and run `/solo:start` to generate these files.
