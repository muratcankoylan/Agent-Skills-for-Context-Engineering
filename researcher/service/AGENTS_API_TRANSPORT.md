# OpenAI Agents API transport boundary

This is the first independently reviewable implementation slice for the
OpenAI Agents API migration. It is not a complete research service, a Codex
desktop automation, an SDK wrapper, or production activation.

The adapter uses the Python standard library for HTTP and exposes `AgentsClient.create`, `retrieve`, `turns`,
`items`, and `cancel`. The caller must provide the credential explicitly and
own authorization, durable submission intent, spending controls, observation,
and remote reconciliation. Importing this module performs no network calls.
Its integrated tracing/schema imports require the existing hash-locked
`requirements-dev.txt` dependency closure; the complete module is not stdlib-only.

The fixed endpoint is `https://api.openai.com/v1/agents/sessions`; the beta header
is `OpenAI-Beta: agents=v1`. Each call makes at most one HTTP request. Redirects,
ambient proxies, credential reflection, malformed records, unbounded output and
unknown response formats are rejected. The real HTTP worker has a wall deadline
and a minimal environment. A timeout does not cancel a remote session.

`AgentsError(code, ambiguous, session_id)` distinguishes uncertain write effects
from failed reads. A safe session ID decoded before a later schema failure is
retained for cancellation/reconciliation. Caller-provided IDs and cursors cannot
carry the explicit credential into a URL. No response diagnostic is interpolated
into exception text.

There is no documented create-time hard session spending/token cap in the reviewed
public-beta contract. Do not treat one create as one model call. Session/turn usage
is nullable, may change, and is not a final invoice. The caller must not retry an
unknown create outcome or claim that a cancel acknowledgement proves termination.
The documented event Idempotency-Key is used for cancellation only; no equivalent
session-create guarantee is invented.

Items are returned as complete original pages. `turn_id` is validated as caller
intent but is not sent as an undocumented query parameter. Filter by turn only
after handling the original page cursor. Streams are not implemented by this
adapter; the managed API's saved items/turns are the recovery source.

## Offline conformance tests

```sh
python -m unittest discover -s researcher/service/tests -p test_openai_agents.py -v
```

Tests use injected HTTP responses and subprocess fixtures. They make no paid
API calls and establish no live account availability, research effectiveness,
tool capability, cloud deployment or production readiness.

## Follow-on implementation gates

1. Persist exact context/manifest, create intent, safe remote ID, cancellation and
   terminal-turn observations. Never duplicate work after a lost acknowledgement.
2. Compile selected skill baselines and provenance-linked evidence into a bounded
   structured research/critique/proposal request with no external tools initially.
3. Evaluate frozen candidates outside the proposing session, with no-skill,
   baseline and candidate controls and failure-inclusive reporting.
4. Integrate registered source tools, authenticated UI, spending/retention controls,
   complete recovery, scoped GitHub delivery and explicit human launch approval.

References, reviewed 2026-09-10:

- [Agents API quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart)
- [Create session](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/methods/create)
- [Create input events](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/subresources/events/methods/create)
- [Session recovery](https://developers.openai.com/api/docs/guides/agents-api/sessions/events)
- [Usage and cost limitations](https://developers.openai.com/api/docs/guides/agents-api/observability)
- [Project spending controls](https://developers.openai.com/api/docs/guides/spend-limits)
