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

**Google Cloud has no hard spend cap.** Budgets are notification-only. A budget
alert emails you after the fact and stops nothing. The only true hard stop is
the documented budget → Pub/Sub → Cloud Function pattern that programmatically
detaches the billing account, which takes the whole project down with it.

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
