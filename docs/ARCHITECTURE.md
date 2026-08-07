# Architecture

**Snapshot of the current system.** This document describes *now* — replace
stale content, do not append history. Decisions and their reasoning live in
`docs/adr/`.

Status: **deployed and verified end to end on Cloud Run**, backed by a native
Firestore database, in project `agent-era`.

    https://intake-agent-320877670799.us-central1.run.app

## Diagrams

Interactive, self-contained HTML — pan, zoom, search, click a node to trace its
relationships, and step the guided views.

| Diagram | Shows | Source spec |
|---|---|---|
| [`diagrams/intake-architecture.html`](diagrams/intake-architecture.html) | Components, boundaries, where each model call happens | `diagrams/intake.architecture.json` |
| [`diagrams/intake-sequence.html`](diagrams/intake-sequence.html) | One 18-second chunk end to end, then the gate refusing a report | `diagrams/intake.sequence.json` |
| [`diagrams/intake-orchestration.html`](diagrams/intake-orchestration.html) | Inside the turn: which stages are ADK LlmAgents, which are ours, where each Vertex call happens | `diagrams/intake.orchestration.json` |

The workflow renderer has a fixed 80px column pitch and a 92px minimum node
width, so connected nodes must sit **two columns apart** or they overlap. That
caps a lane's main path at three boxes, which is why routing and adjudication
share one — the split is in its sublabel and the cards.

Regenerate after a change rather than hand-editing the HTML:

```bash
node ~/.claude/skills/archify/bin/archify.mjs deliver architecture \
  docs/diagrams/intake.architecture.json docs/diagrams/intake-architecture.html --quality showcase
```

## Components

| Component | Tech | Responsibility | State |
|---|---|---|---|
| Web client | React 18 + Vite | Mic capture, 18s chunking, local chunk queue, live coverage UI, three-state gate, report edit | Built |
| Agent service | FastAPI + ADK Python 2.6.2 | HTTP surface, turn orchestration, gate, report assembly | Built |
| Turn pipeline | ADK custom `BaseAgent` (`TurnPipeline`) | transcribe → route → adjudicate → coach | Built |
| Router | `gemini-3.6-flash`, schema-constrained | Which open items does this chunk bear on? | Built |
| Adjudicator | `gemini-3.6-flash` via Vertex AI, schema-constrained | Answer-level judgement, one call per item | Built, precision 100% on eval |
| Session store | Firestore, with in-memory fallback | Durable slot state, follow-ups, highlights | Built |
| Templates | JSON config | The entire vertical | Two shipped |

## Data flow, per audio chunk

```
browser mic
  └─ MediaRecorder, 18s timeslice
       └─ base64 ──POST /sessions/{id}/chunks {seq, audio_b64}
             │        (failed posts queue locally and replay in order)
             ▼
        Cloud Run · FastAPI
             ├─ claim_chunk(seq) ──▶ already seen? return current state, no work
             └─ ADK SequentialAgent "intake_turn"
                  ├─ 1. transcriber   LlmAgent, audio in → speaker-attributed turns
                  ├─ 2. adjudication  custom BaseAgent
                  │       ├─ load open required items from Firestore
                  │       ├─ route(): one call — which items is this chunk about?
                  │       ├─ fan out: one adjudicate() call per routed item, concurrently
                  │       ├─ discard verdicts marked not-addressed
                  │       ├─ fold verdicts into slot state, atomically
                  │       └─ recompute depends_on → the required set changes mid-interview
                  └─ 3. coach         LlmAgent, reads the brief → next question + highlights
             ▼
        Firestore session document
             └─ returned to the client (a realtime listener can replace the response)
```

**The slot state is the state, not the transcript** (ADR-0002). The coach never
sees a transcript — it sees a brief listing open items, what each is missing,
and this chunk's quotes. Adjudication sees a capped window of the last 12
interviewee turns, which is what lets an answer arrive across two turns without
letting context grow without bound. A three-hour interview costs the same per
chunk as a ten-minute one.

## Evaluation, at two levels

| Harness | Question it answers | Where |
|---|---|---|
| `eval/run_eval.py` | Is the adjudicator's *judgement* right, item by item? | 47 labelled cases, 46/47, precision 100% |
| `agents-cli eval` | Does the *pipeline* behave — does it obey ADR-0006, does it ask about something genuinely open? | 6 cases, `tests/eval/`, all metrics 5/5 |

The second is not a nicety. Its first clean run found a real ADR-0006 hole that
the schema could not catch: the coach's highlight `title` is free text, and it
had written "Formal decline to answer alcohol question" — an interpretation, not
a label. See ADR-0010.

Running it needs an ADK server, because `eval generate` speaks ADK's HTTP
protocol rather than ours:

```bash
cd backend && PYTHONPATH=. uv run adk api_server adk_apps --port 8001
agents-cli eval run --dataset tests/eval/datasets/turn-pipeline.json \
  --url http://localhost:8001 --app-name intake --config tests/eval/eval_config.yaml
```

## Why adjudication is not an LlmAgent

It is a custom `BaseAgent` that fans out one constrained call per open item.
Three reasons, in order of importance:

1. **Isolation.** A wrong verdict on M14 cannot corrupt M06. One prompt judging
   fourteen items at once has no such guarantee.
2. **Measurability.** The per-item contract is exactly what `eval/` scores. A
   combined call would not be scoreable case by case.
3. **Latency.** Fourteen concurrent calls cost about one call's wall time.

## Session lifecycle

1. Practitioner picks a template. Required set = `required` items plus any
   `depends_on` conditions already satisfied (none, at the start).
2. Recording starts. A recording indicator is visible for the whole session.
3. Per chunk: transcribe, adjudicate every open item, fold verdicts, recompute
   the required set, propose the next question and highlights.
4. Practitioner asks for the report. The gate evaluates every required item.
5. Anything unresolved must reach **answered** (with its span), **declined**
   (with a reason, and only where the template permits it), or **escalated**
   (the agent drafts and files a follow-up action).
6. Report assembled deterministically, edited in-browser, exported.

## Adjudication contract

Input: one template item, its human-authored guidance note, and the recent
interviewee turns. Output, schema-constrained:

| Field | Meaning |
|---|---|
| `verdict` | `sufficient` · `insufficient` · `declined` |
| `addressed` | Did this chunk bear on this item at all? |
| `evidence` | Verbatim transcript span relied on; empty when not addressed |
| `missing` | Guidance elements still unrecorded, in the guidance's own terms |
| `reason` | One sentence for the practitioner, about the record not the person |

`addressed` exists because "insufficient" is otherwise ambiguous between *asked
and dodged* and *never came up* — and without it the UI quotes a remark about
falls underneath the continence item.

Correctness is measured, not assumed. See `eval/`. The bar: never mark an
answer sufficient that a labelled case marks insufficient. Current: **precision on `sufficient` 100%**, the property the gate depends on.
Accuracy varies 45–46 of 47 between runs; every miss is a false *insufficient*,
never a false tick. Twelve of those cases are
adversarial, and one of them found a real defect the first time it ran: a
retracted answer being read as a clean nil return.

## Data model

```
sessions/{session_id}
    template_id, practitioner_id, status, started_at, updated_at
    slots: { item_id: { state, value, evidence, missing[], reason,
                        resolved_at, source } }
    highlights: [ {id, item_id, title, quote, status} ]
    next_question: {item_id, prompt, why}
    followups:  [ {item_id, outstanding, why, destination, drafted_at} ]
    processed_chunks: [seq, ...]
    recent_turns: [str, ...]        # capped at 12
    report: {...} | null

practitioners/{practitioner_id}     # planned, not yet written
    dismissed_categories, phrasing_notes, report_voice
```

Slot states: `open` → `partial` → `answered` | `declined` | `escalated`.
`partial` is the state no competitor has: discussed, but not answered.

Slots are a map on the session document rather than a subcollection, so the
whole coverage view arrives in one realtime snapshot and each chunk is a single
atomic write. Templates have tens of items, so the 1MiB document ceiling is not
in play.

**No interviewee identity is solicited, indexed, or used as a key** (ADR-0007),
and a test asserts the schema has no field for one.

The precise version: `evidence`, `value`, `quote` and `recent_turns` hold
verbatim interviewee speech, which can contain a name said in passing. Quoting
exactly is the product, so this is a retention question, not a redaction one —
the spans stay in the session document, are never written to logs (provider
exceptions are logged by type only, since a Vertex 400 echoes the request body),
and go when the session goes. A Firestore TTL policy on `sessions/` is the
outstanding piece.

## External dependencies

- **Vertex AI** — `gemini-3.6-flash`, structured output, native audio input.
  Chosen over the Gemini API so Vertex logs double as the contest's required
  proof of Google Cloud. `GOOGLE_GENAI_USE_VERTEXAI=TRUE` is what makes ADK pick
  this backend; without it ADK looks for an AI Studio key and fails.
- **Firestore** — session state. Native mode required; a Datastore-mode project
  fails on first write, which is why startup probes with a real read.
- **Google ADK (Python) 2.6.2** — pinned. Requires `google-genai>=2.9`.

## Failure modes

| Failure | Handling | Where |
|---|---|---|
| Chunk POST fails | Queued in the browser, replayed in order on the next success | `web/src/api.js` `ChunkQueue` |
| Chunk replayed after a drop | `claim_chunk` makes it a no-op; the response says `replayed` | `store.claim_chunk` |
| One item's adjudication errors | Logged, that item stays open and retries next chunk; its neighbours still land | `AdjudicationAgent` |
| A whole turn raises | Response is `degraded: true`, session intact, recording continues | `POST /chunks` |
| Malformed model output | Schema-constrained decode; a non-JSON body yields an empty dict, not a crash | `_loads` |
| Firestore unusable | Startup probe fails → in-memory store with a loud warning | `default_store` |
| Cloud Run instance recycles | No impact; durable state is Firestore's, not ADK's (ADR-0004) | — |
| Oversized/invalid audio | 413 / 400 before decoding | `POST /chunks` |
| Model unavailable — spend cap, quota, outage | Chunks return `degraded`; escalation still files the follow-up with a destination, flagged `degraded`, rather than 500ing and holding the report hostage | `POST /chunks`, `POST /resolve` |

## Deployment

Cloud Run service `intake-agent`, built from `backend/Dockerfile` via
`backend/deploy.sh` (which stages `templates/` into the build context). Deployed
with `--no-allow-unauthenticated` and an `INTAKE_API_KEY` secret: every endpoint
spends money on Vertex AI. The web client builds statically and can be served
anywhere.
