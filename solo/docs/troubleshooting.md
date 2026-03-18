# Troubleshooting Guide 🛠️

Having trouble with Solo? Check here for common issues and their solutions.

---

## 🔌 MCP & Connection Issues

### "Tool not found" or "Connection refused"

- **Cause**: The MCP server is not running or the URL is incorrect.
- **Fix**: Run `/solo:check-connections`. Any server marked with ❌ is not responding. Ensure your `.mcp.json` has the correct authentication keys (e.g., `EXA_API_KEY`).

### Stripe/HubSpot/Figma not syncing

- **Cause**: Authentication expired or permissions missing.
- **Fix**: Visit the URL in `.mcp.json` (e.g., `https://mcp.hubspot.com/anthropic`) and ensure you have authorized the connection for the correct workspace.

---

## 📁 Data & File Issues

### "Cannot find client card"

- **Cause**: File naming or location issue.
- **Fix**: Ensure your client cards are stored in `data/1-Projets/clients/` and end with `.md`. Use the standard `_TEMPLATE.md` to ensure correct formatting.

### Invoices not appearing in dashboard

- **Cause**: Incorrect status tag.
- **Fix**: Solo looks for `Status: [Draft | Sent | Paid | Overdue]`. If you use different wording (e.g., "Mailed"), the agent won't recognize it. Use the provided templates.

---

## 🤖 Agent Issues

### "Agent didn't run"

- **Cause**: Most agents run on a schedule (Cron). They won't trigger unless you are actively using the plugin during that window, or if your environment supports background execution.
- **Fix**: You can trigger any agent manually by asking: "Can you run the [Invoice Reminder] workflow?"

### "Content Multiplier didn't create posts"

- **Cause**: Hook trigger failure or missing Voice DNA.
- **Fix**: Ensure your blog post was saved in the expected directory. Verify that `data/2-Domaines/voice-dna.json` exists; the agent needs it to match your style.

---

## 🇫🇷 Language Issues

### "Command is in English but I want French"

- **Fix**: Solo uses the `.fr.md` version of commands if your profile language is set to `fr`. Run `/solo:start fr` to reset your language preference.

---

## Resetting Solo

If all else fails, you can reset your configuration.

1. Delete `data/2-Domaines/skill-config.json`.
2. Delete `data/2-Domaines/business-profile.json`.
3. Run `/solo:start` to begin the onboarding again.

**Note**: This will NOT delete your client data, projects, or invoices. It only resets your business profile and active skill list.
