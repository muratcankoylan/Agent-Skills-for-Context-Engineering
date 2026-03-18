#!/usr/bin/env python3
"""
Reddit MCP Server for Copywriter Plugin
Provides Voice-of-Customer research by mining Reddit for honest user insights,
pain points, and unfiltered language patterns.

Setup:
  1. Create a Reddit app at https://www.reddit.com/prefs/apps (script type)
  2. Set environment variables:
       REDDIT_CLIENT_ID     — from your Reddit app
       REDDIT_CLIENT_SECRET — from your Reddit app
  3. Or pass via .mcp.json env block (already configured)

Usage (via MCP):
  - search_subreddit(subreddit, query, limit) → top posts + top comments
  - get_pain_points(subreddit, keyword)       → comments filtered by frustration signals
  - get_voice_of_customer(keyword, subreddits) → cross-subreddit language mining
"""

import argparse
import json
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Reddit MCP Server")
    parser.add_argument("--client_id", default=os.environ.get("REDDIT_CLIENT_ID", ""))
    parser.add_argument("--client_secret", default=os.environ.get("REDDIT_CLIENT_SECRET", ""))
    return parser.parse_args()


def check_dependencies():
    """Verify required packages are available."""
    missing = []
    try:
        import praw  # noqa: F401
    except ImportError:
        missing.append("praw")
    try:
        import mcp  # noqa: F401
    except ImportError:
        missing.append("mcp")
    return missing


def startup_check(args):
    """Validate credentials and dependencies before starting server."""
    missing_deps = check_dependencies()
    if missing_deps:
        print(
            json.dumps({
                "error": "missing_dependencies",
                "message": f"Install required packages: pip install {' '.join(missing_deps)}",
                "packages": missing_deps
            }),
            file=sys.stderr
        )
        sys.exit(1)

    if not args.client_id or not args.client_secret:
        print(
            json.dumps({
                "error": "missing_credentials",
                "message": (
                    "Reddit API credentials required. "
                    "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET, "
                    "or pass --client_id and --client_secret. "
                    "Create a Reddit app at https://www.reddit.com/prefs/apps"
                )
            }),
            file=sys.stderr
        )
        sys.exit(1)


def build_reddit_client(args):
    import praw
    return praw.Reddit(
        client_id=args.client_id,
        client_secret=args.client_secret,
        user_agent="copywriter-mcp/1.0 (content research tool)"
    )


def search_subreddit(reddit, subreddit: str, query: str, limit: int = 10) -> list:
    """Search a subreddit and return top posts with top comments."""
    results = []
    sub = reddit.subreddit(subreddit)
    for post in sub.search(query, sort="relevance", limit=limit):
        post.comments.replace_more(limit=0)
        top_comments = [
            {"body": c.body, "score": c.score}
            for c in sorted(post.comments.list(), key=lambda x: x.score, reverse=True)[:5]
        ]
        results.append({
            "title": post.title,
            "score": post.score,
            "url": post.url,
            "selftext": post.selftext[:500] if post.selftext else "",
            "top_comments": top_comments
        })
    return results


def get_pain_points(reddit, subreddit: str, keyword: str, limit: int = 20) -> list:
    """Extract comments containing frustration signals for VoC research."""
    pain_signals = [
        "frustrated", "annoying", "hate", "can't believe", "worst",
        "problem", "issue", "broken", "doesn't work", "wish",
        "why can't", "so hard", "impossible", "terrible", "awful"
    ]
    results = []
    sub = reddit.subreddit(subreddit)
    for post in sub.search(keyword, sort="relevance", limit=limit):
        post.comments.replace_more(limit=0)
        for comment in post.comments.list():
            body_lower = comment.body.lower()
            if any(signal in body_lower for signal in pain_signals) and len(comment.body) > 50:
                results.append({
                    "comment": comment.body[:600],
                    "score": comment.score,
                    "post_title": post.title
                })
    return sorted(results, key=lambda x: x["score"], reverse=True)[:15]


def get_voice_of_customer(reddit, keyword: str, subreddits: list, limit: int = 5) -> dict:
    """Mine language patterns across multiple subreddits for copywriting."""
    all_phrases = []
    for sub_name in subreddits:
        try:
            posts = search_subreddit(reddit, sub_name, keyword, limit)
            for post in posts:
                all_phrases.append(post["title"])
                for c in post["top_comments"]:
                    all_phrases.append(c["body"])
        except Exception:
            continue
    return {
        "keyword": keyword,
        "subreddits_searched": subreddits,
        "raw_phrases": all_phrases[:50],
        "note": "Use antislop-expert to extract power words and authentic language patterns"
    }


def run_mcp_server(args):
    """Start the MCP server with Reddit tools exposed."""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    import asyncio

    reddit = build_reddit_client(args)
    server = Server("reddit-mcp")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="search_subreddit",
                description="Search a subreddit for posts matching a query. Returns top posts with comments.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subreddit": {"type": "string", "description": "Subreddit name (without r/)"},
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "default": 10, "description": "Max posts to return"}
                    },
                    "required": ["subreddit", "query"]
                }
            ),
            Tool(
                name="get_pain_points",
                description="Extract comments containing frustration signals for Voice-of-Customer research.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subreddit": {"type": "string", "description": "Subreddit name (without r/)"},
                        "keyword": {"type": "string", "description": "Topic or product to research"},
                        "limit": {"type": "integer", "default": 20, "description": "Posts to scan"}
                    },
                    "required": ["subreddit", "keyword"]
                }
            ),
            Tool(
                name="get_voice_of_customer",
                description="Mine authentic language patterns across multiple subreddits for copywriting.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "Topic or product name"},
                        "subreddits": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of subreddit names to search"
                        },
                        "limit": {"type": "integer", "default": 5, "description": "Posts per subreddit"}
                    },
                    "required": ["keyword", "subreddits"]
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name == "search_subreddit":
                result = search_subreddit(reddit, arguments["subreddit"], arguments["query"], arguments.get("limit", 10))
            elif name == "get_pain_points":
                result = get_pain_points(reddit, arguments["subreddit"], arguments["keyword"], arguments.get("limit", 20))
            elif name == "get_voice_of_customer":
                result = get_voice_of_customer(reddit, arguments["keyword"], arguments["subreddits"], arguments.get("limit", 5))
            else:
                result = {"error": f"Unknown tool: {name}"}
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())


if __name__ == "__main__":
    args = parse_args()
    startup_check(args)
    run_mcp_server(args)
