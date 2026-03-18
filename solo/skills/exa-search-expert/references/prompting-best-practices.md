# Search Prompting Best Practices

This guide provides best practices for formulating effective queries for advanced, AI-powered search tools.

---

## 1. Use Full Sentences and Questions

Instead of just using keywords, frame your query as a natural language question or a descriptive statement. This provides more context for neural search models.

-   **Bad:** `AI sales tools`
-   **Good:** `What are the most innovative AI-powered tools that can help a sales team improve their outbound prospecting?`

## 2. Provide Context

Include details about the *perspective* you want the search results to have.

-   **Instead of:** `benefits of remote work`
-   **Try:** `What are the financial benefits for early-stage startups that switch to a fully remote model?`

## 3. Specify the Desired Format

If you are looking for a specific type of content, mention it in the prompt.

-   `Find a tutorial on how to use the Figma API.`
-   `Show me case studies of companies that have successfully implemented a 4-day work week.`
-   `I'm looking for a market analysis report on the pet food industry.`

## 4. Use "Find Similar"

After you find a perfect result, use the tool's "find similar" or "expand" feature. This is often more effective than trying to craft a new prompt from scratch. Start with one good "seed" document and branch out from there.

## 5. Leverage Deep Research Agents

For complex topics that require synthesis from multiple sources, use a deep research agent if the tool supports it.

-   **Good prompt for a deep agent:** `Generate a comprehensive report on the current state of the carbon capture market, including key players, emerging technologies, and regulatory challenges.`
-   This is more effective than running ten separate searches and trying to synthesize them yourself.
