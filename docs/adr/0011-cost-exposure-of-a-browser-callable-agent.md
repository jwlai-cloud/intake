# 0011 — Cost exposure of a browser-callable agent

- **Status:** Accepted
- **Date:** 2026-08-06

## Context

The deployed service is `--allow-unauthenticated` with an application-layer
`X-Intake-Key` header, because the client is a browser and the product
deliberately has no user accounts, so it cannot mint a Google identity token.
The key ships inside the built JS bundle and is therefore public to anyone who
opens the file.

Every request spends money on Vertex AI, and not a little: one chunk costs a
transcription call, a routing call, one adjudication call per routed item, and a
coaching call.

Two facts drive this decision.

**Correction, same day.** This ADR originally stated that Google Cloud has no
hard spend cap and that budgets are notification-only. That is out of date.
Cloud Billing now offers **spend cap enforcement** (Preview): a monthly budget
scoped to one project and one service that *pauses* the service when the cap is
reached. Enforcement is not instantaneous — overage is still billed — so the cap
belongs below the real limit.

The trap it replaces the old one with: the cap is scoped to a single named
service, and `Gemini API (generativelanguage.googleapis.com)` is **not** the
service this project spends on. Intake calls Vertex AI (`vertexai=True`,
`GOOGLE_GENAI_USE_VERTEXAI=TRUE`), so the cap must name
`aiplatform.googleapis.com`. Both APIs are enabled on the project, which makes
the wrong choice look right.

**The deployed defaults were wide open.** `maxScale: 20` with
`containerConcurrency: 80` allows 1,600 concurrent requests.

## Decision

Bound the blast radius at the Cloud Run layer rather than chase a cap that does
not exist:

- `--max-instances=2`, `--concurrency=4` — at most 8 requests in flight.
- `--timeout=120s` — a stuck request cannot hold a slot indefinitely.
- Treat the service as **ephemeral**: deploy it for a demo, delete it after.
  `backend/deploy.sh` records the teardown command.

Vertex AI per-minute quota overrides were considered and rejected for now: they
are the only real throttle, but they apply to the whole project and would
equally throttle `eval/run_eval.py` and `agents-cli eval`, which are the
project's main legitimate consumers.

## Consequences

Worst-case sustained load is roughly 30 requests per minute rather than
unbounded. That is a real bound, not a cap — a determined abuser with the bundle
key could still run up a bill over hours, which is precisely why the service
should not be left running between demos.

The residual risk is accepted knowingly and written down rather than discovered
on an invoice. If this ever becomes a product rather than a contest entry, the
browser must authenticate a real user and the endpoint must move behind Cloud
Run IAM.
