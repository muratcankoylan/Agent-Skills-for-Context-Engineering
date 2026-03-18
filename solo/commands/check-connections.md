---
description: "Check which integrations are connected and get optimization recommendations"
allowed-tools: mcp__filesystem, read_file, list_directory
model: sonnet
---

# /solo:check-connections

Diagnose your Solo setup and get personalized recommendations for improving your workflow.

---

## What This Command Does

1. **Scans your environment** - Detects which MCP servers are connected
2. **Analyzes your usage** - Reviews which commands you use most
3. **Recommends optimizations** - Suggests which tools to connect based on your workflow
4. **Shows capability tiers** - Explains what each connection level unlocks

---

## Output Example

```
🔍 Solo Plugin Connection Status
Generated: 2026-02-13 14:30

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ CONNECTED (3/14)

  ✓ Filesystem
    Status: Active
    Purpose: Core storage for all your data
    Performance: Good (read: 12ms, write: 8ms)
    
  ✓ Exa Search
    Status: Active
    Purpose: Enhanced web research
    API Calls Today: 15/100
    
  ✓ Slack
    Status: Active  
    Purpose: Notifications and collaboration
    Last Used: 2 hours ago

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  HIGH-IMPACT RECOMMENDATIONS (Connect These Next)

  ○ HubSpot CRM
    Why: You've used /solo:clients 23 times this month
    Benefit: Automatic client sync, no manual file updates
    Impact: Save ~45 minutes/week
    Setup: https://docs.claude.com/mcp/hubspot
    
  ○ Stripe  
    Why: You've generated 18 invoices manually
    Benefit: Auto-send invoices, track payments
    Impact: Reduce payment delays by 40%
    Setup: https://docs.claude.com/mcp/stripe

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 NICE-TO-HAVE (Optional Enhancements)

  ○ Figma
    Benefit: Interactive prototypes for /solo:build
    When to add: When you need design mockups
    
  ○ Notion
    Benefit: Alternative to filesystem for knowledge management
    When to add: If you already use Notion heavily
    
  ○ Clay
    Benefit: Enhanced lead enrichment
    When to add: When prospecting at scale (>50 leads/week)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 YOUR CURRENT CAPABILITIES

┌─────────────────────────┬──────────┬─────────────┬──────────────┐
│ Feature Area            │ Current  │ w/ HubSpot  │ w/ All Tools │
├─────────────────────────┼──────────┼─────────────┼──────────────┤
│ Client Management       │ BASIC    │ PRO         │ SUPERCHARGED │
│ Invoicing              │ BASIC    │ BASIC       │ SUPERCHARGED │
│ Content Creation       │ BASIC    │ BASIC       │ PRO          │
│ Research               │ PRO      │ PRO         │ SUPERCHARGED │
│ Product Development    │ OFFLINE  │ OFFLINE     │ PRO          │
│ Lead Generation        │ BASIC    │ BASIC       │ PRO          │
└─────────────────────────┴──────────┴─────────────┴──────────────┘

Legend:
  OFFLINE      - No automation, manual workflows
  BASIC        - File-based, manual updates
  PRO          - Partial automation, some sync
  SUPERCHARGED - Full automation, live sync

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 USAGE INSIGHTS (Last 30 Days)

Most Used Commands:
  1. /solo:write (45 times) - ✅ Fully operational
  2. /solo:clients (23 times) - ⚠️ Could be automated with HubSpot
  3. /solo:invoice (18 times) - ⚠️ Could be automated with Stripe
  4. /solo:research (12 times) - ✅ Optimized with Exa
  5. /solo:build (5 times) - ⚠️ Limited without Figma

Workflow Pattern Detected:
  clients → invoice → email (15 times)
  💡 Suggestion: Connect Stripe to automate this entire flow

Average Time Saved vs Manual:
  Content Creation: ~2.5 hours/week
  Research: ~3 hours/week
  Potential with HubSpot+Stripe: ~4.5 hours/week more

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 QUICK ACTIONS

Connect a tool:
  • claude mcp add hubspot
  • See all options: https://docs.claude.com/mcp/servers

Test your setup:
  • /solo:test filesystem
  • /solo:test all

Update configuration:
  • /solo:configure connections

Need help?
  • /solo:help connections
  • Troubleshoot: /solo:diagnose
```

---

## Agent Instructions

### Step 1: Detect Connected MCP Servers

```python
def detect_connections():
    """Probe for available MCP servers"""
    servers = {
        "filesystem": check_server("filesystem"),
        "exa": check_server("exa"),
        "slack": check_server("slack"),
        "hubspot": check_server("hubspot"),
        "stripe": check_server("stripe"),
        "figma": check_server("figma"),
        "notion": check_server("notion"),
        "ms365": check_server("ms365"),
        "linkedin": check_server("linkedin"),
        "clay": check_server("clay"),
        "fireflies": check_server("fireflies"),
        "remotion": check_server("remotion"),
        "google-calendar": check_server("google-calendar"),
        "google-drive": check_server("google-drive"),
        "tally": check_server("tally")
    }
    
    return {k: v for k, v in servers.items() if v["connected"]}

def check_server(server_name):
    """Test if a specific MCP server responds"""
    try:
        # Attempt a basic operation
        result = call_mcp_server(server_name, "ping")
        return {
            "connected": True,
            "latency": result.latency,
            "version": result.version,
            "status": "healthy"
        }
    except ConnectionError:
        return {"connected": False}
```

### Step 2: Load Usage Analytics

```python
def load_usage_analytics():
    """Read usage data from memory"""
    analytics_file = "${CLAUDE_PLUGIN_ROOT}/data/memoire/usage-analytics.json"
    
    if file_exists(analytics_file):
        return json.load(analytics_file)
    else:
        return {
            "commands_used": {},
            "skills_triggered": {},
            "workflow_patterns": []
        }
```

### Step 3: Calculate Impact Scores

```python
def calculate_recommendations(connections, usage):
    """Score each missing connection by potential impact"""
    recommendations = []
    
    # HubSpot - high impact if using /solo:clients frequently
    if not connections.get("hubspot"):
        client_usage = usage["commands_used"].get("/solo:clients", 0)
        if client_usage > 5:
            recommendations.append({
                "tool": "HubSpot CRM",
                "impact": "HIGH",
                "reason": f"You've used /solo:clients {client_usage} times",
                "benefit": "Automatic client sync, no manual updates",
                "time_saved": f"~{client_usage * 2} minutes/month"
            })
    
    # Stripe - high impact if generating invoices
    if not connections.get("stripe"):
        invoice_usage = usage["commands_used"].get("/solo:invoice", 0)
        if invoice_usage > 3:
            recommendations.append({
                "tool": "Stripe",
                "impact": "HIGH",
                "reason": f"You've generated {invoice_usage} invoices manually",
                "benefit": "Auto-send invoices, track payments",
                "time_saved": f"~{invoice_usage * 15} minutes/month"
            })
    
    # Figma - medium impact if building products
    if not connections.get("figma"):
        build_usage = usage["commands_used"].get("/solo:build", 0)
        if build_usage > 2:
            recommendations.append({
                "tool": "Figma",
                "impact": "MEDIUM",
                "reason": f"You've used /solo:build {build_usage} times",
                "benefit": "Interactive prototypes instead of static mockups",
                "time_saved": f"Better prototypes, not just time saved"
            })
    
    # Tally - high impact if using /solo:diagnose share
    if not connections.get("tally"):
        diagnose_usage = usage["commands_used"].get("/solo:diagnose", 0)
        if diagnose_usage > 2:
            recommendations.append({
                "tool": "Tally (~~forms)",
                "impact": "HIGH",
                "reason": f"You've used /solo:diagnose {diagnose_usage} times",
                "benefit": "Publish diagnostics as real Tally forms — share a URL instead of a prompt block. Responses sync back automatically for scoring.",
                "time_saved": "~30 min saved per diagnostic you share async",
                "setup": "https://tally.so/settings/api-keys"
            })
    
    return sorted(recommendations, key=lambda x: x["impact"], reverse=True)
```

### Step 4: Generate Capability Matrix

```python
def generate_capability_matrix(connections):
    """Show what each tier unlocks"""
    features = [
        {
            "name": "Client Management",
            "offline": "Manual markdown files",
            "basic": "Local file storage",
            "with_hubspot": "Live CRM sync",
            "supercharged": "Full automation + insights"
        },
        {
            "name": "Invoicing",
            "offline": "Template filling",
            "basic": "PDF generation",
            "with_stripe": "Auto-send + tracking",
            "supercharged": "Payment reminders + analytics"
        },
        # ... more features
    ]
    
    current_tier = determine_tier(connections)
    return format_matrix(features, current_tier)

def determine_tier(connections):
    """Calculate current capability tier"""
    count = len(connections)
    if count == 0:
        return "OFFLINE"
    elif count <= 2:
        return "BASIC"
    elif count <= 5:
        return "PRO"
    else:
        return "SUPERCHARGED"
```

### Step 5: Format Output

```python
def format_connection_status(connections, recommendations, matrix, usage):
    """Generate the full status report"""
    
    output = f"""
🔍 Solo Plugin Connection Status
Generated: {datetime.now()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ CONNECTED ({len(connections)}/14)

{format_connected_list(connections)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  HIGH-IMPACT RECOMMENDATIONS

{format_recommendations(recommendations, impact="HIGH")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 NICE-TO-HAVE

{format_recommendations(recommendations, impact="MEDIUM")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 YOUR CURRENT CAPABILITIES

{matrix}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 USAGE INSIGHTS

{format_usage_insights(usage)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 QUICK ACTIONS

{format_quick_actions()}
"""
    return output
```

---

## Diagnostic Tests

### Test Individual Connections

```bash
# Test filesystem connection
/solo:test filesystem

Output:
✅ Filesystem: Healthy
   - Read speed: 12ms
   - Write speed: 8ms
   - Storage: 2.3 GB used / 100 GB available
   - Data directory: /home/user/.claude/solo/data/
```

### Test All Connections

```bash
/solo:test all

Output:
Running diagnostics on all configured connections...

✅ filesystem - Healthy (12ms)
✅ exa - Healthy (45ms, 85/100 API calls remaining)
❌ hubspot - Not connected
⚠️  slack - Connected but slow (320ms latency)
✅ stripe - Healthy
```

---

## Connection Guides

### Quick Setup Links

For each unconnected tool, provide direct setup instructions:

```markdown
## Setting Up HubSpot

1. Get your API key:
   • Go to: Settings → Integrations → API Key
   • Copy the key

2. Add to Claude:
   • Run: claude mcp add hubspot
   • Enter your API key when prompted

3. Test the connection:
   • Run: /solo:test hubspot
   • Should see: ✅ Connected

4. Verify sync:
   • Run: /solo:clients sync
   • Your HubSpot contacts will appear
```

---

## Error Messages

### No Connections Detected

```
⚠️  No MCP servers detected

You're running in OFFLINE mode. Solo works, but with limited automation.

To unlock more features:
1. Read: CONNECTORS.md
2. Choose a tool to connect
3. Follow setup guide

Minimum recommended: Filesystem (for persistent storage)
```

### Connection Failed

```
❌ Connection Test Failed: HubSpot

Possible causes:
  • API key expired or invalid
  • Network connectivity issues  
  • MCP server not running

Troubleshooting:
  1. Check API key: Settings → API Keys
  2. Test manually: curl https://api.hubspot.com/...
  3. Restart Claude: claude restart
  4. Check logs: claude logs
```

---

## Integration with Other Commands

This command should be suggested contextually:

```python
# In /solo:clients when no CRM connected
if not has_crm_connection():
    suggest("💡 Tip: Connect HubSpot for automatic client sync. Run /solo:check-connections")

# In /solo:invoice when no payment provider  
if not has_payment_provider():
    suggest("💡 Tip: Connect Stripe to auto-send invoices. Run /solo:check-connections")
```

---

## Privacy & Security

- Connection status is stored locally
- No API keys logged in output
- Usage analytics are anonymized
- Can be disabled: `/solo:configure analytics off`

---

## Success Metrics

After running `/solo:check-connections`, users should:
- ✅ Know exactly which tools are connected
- ✅ Understand what they're missing out on
- ✅ Have clear next steps to improve their setup
- ✅ See personalized recommendations based on actual usage
- ✅ Estimate time savings from connections
