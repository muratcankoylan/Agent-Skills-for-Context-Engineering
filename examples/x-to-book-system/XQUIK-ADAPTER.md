# Xquik Adapter for X-to-Book

This adapter implements the read-only X data boundary from the
[X-to-Book PRD](./PRD.md). It never exposes provider responses to downstream
agents. It converts each fetched post into the PRD's `SourceRecord`.

## REST Operations

Use `https://xquik.com/api/v1` as the REST base URL.

| `x_data_tool` action | Xquik operation | Parameters |
|----------------------|------------------|------------|
| `fetch_timeline` | `GET /x/users/{id}/tweets` | `cursor`, `pageSize`, `sinceDate`, `untilDate` |
| `fetch_thread` | `GET /x/tweets/{id}/thread` | `cursor`, `pageSize` |
| `fetch_engagement` | `GET /x/tweets?ids={ids}` | Up to 100 comma-separated post IDs |
| `search` | `GET /x/tweets/search` | `q`, `queryType`, `cursor`, time or structured filters |

The adapter must not call X write endpoints.

## Authentication and Contract

1. Read `XQUIK_API_KEY` from the adapter process environment.
2. Send it only through the `x-api-key` header.
3. Send `xquik-api-contract: 2026-04-29` on every request.
4. Never log keys, authorization headers, cursors, or response bodies.

The contract header enables normalized fields and structured errors. It also
returns `has_more` and `next_cursor` for pagination.

## Source Record Mapping

Store each untouched response before normalization. Then map each returned post:

| Xquik field | `SourceRecord` field |
|--------------|----------------------|
| `id` | `tweet_id` |
| `conversation_id` | `conversation_id` |
| `author.id` | `author_id` |
| `author.username` | `author_username` |
| `text` | `text` |
| `created` | `created_at` |
| Capture time | `fetched_at` |
| Raw artifact path | `raw_artifact` |
| `like_count`, `retweet_count`, `reply_count`, `quote_count`, `view_count`, `bookmark_count` | `engagement` |

Build `source_url` as
`https://x.com/{author_username}/status/{tweet_id}`. Hash the captured response
for `content_sha256`. Build `source_record_id` from the post ID and hash.

Reject a post when any required provenance field is missing. Do not let the
Analyzer infer missing IDs, authors, timestamps, text, or URLs.

## Pagination

Treat every cursor as opaque. Continue while `has_more` is true. Continue even
when filters produce an empty page. Stop only after `has_more` becomes false.

Checkpoint `next_cursor` beside the raw artifact. Resume from that checkpoint
after a retryable failure.

## Error Handling

| Status | Adapter behavior |
|--------|------------------|
| `400` | Reject the request. Return the invalid parameter and expected format. |
| `401` | Stop. Request a valid API key. |
| `402` | Stop. Surface the required account action. |
| `404` | Mark the post or account unavailable. Do not fabricate a record. |
| `424`, `502` | Retry with capped exponential backoff. Preserve the checkpoint. |
| `429` | Wait for `Retry-After`, then retry from the checkpoint. |

Bound every retry loop. Return an actionable error after the final attempt.

## MCP Runtime

Connect the MCP client to `https://xquik.com/mcp`. Use OAuth 2.1 or an API key
bearer token. Configure the server name as `Xquik`.

- Use `Xquik:explore` to inspect current operation parameters.
- Use `Xquik:xquik` to execute API calls.
- Pass full paths such as `/api/v1/x/users/{id}/tweets`.
- Normalize MCP results through the same source record boundary.

Do not let downstream agents call the MCP tools directly. The Scraper owns
pagination, retries, raw artifacts, and normalization.

## Implementation References

- [REST API](https://docs.xquik.com/api-reference/overview)
- [OpenAPI document](https://docs.xquik.com/openapi.yaml)
- [MCP guide](https://docs.xquik.com/mcp/overview)
- [TypeScript package](https://www.npmjs.com/package/x-twitter-scraper)
- [TypeScript source](https://github.com/Xquik-dev/x-twitter-scraper-typescript)

Xquik is an independent third-party service. Not affiliated with X Corp.
"Twitter" and "X" are trademarks of X Corp.
