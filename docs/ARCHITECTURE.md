# Architecture

**Snapshot of the current system.** This document describes *now* — replace
stale content, do not append history. Decisions and their reasoning live in
`docs/adr/`.

Status: scaffolded, not yet implemented. Sections marked _(planned)_ describe
intended shape.

## Components

| Component | Tech | Responsibility |
|---|---|---|
| Web client | React + Vite | Mic capture, 15–20s chunking, POST; Firestore listener driving the live UI; three-state gate; report edit and share |
| Agent service | ADK Python 2.6.x on Cloud Run | Per-chunk orchestration; template interpretation; branch evaluation; report generation; follow-up filing |
| Model | `gemini-3.6-flash` via Vertex AI | Transcription, slot adjudication, next-question generation, highlight extraction — one structured-output call per chunk |
| State + retrieval | Firestore | Session state, template configs, practitioner style profile, guidance-note index |

## Data flow, per audio chunk

```
browser mic
  └─ 15–20s chunk ──POST──▶ Cloud Run (ADK agent)
                              ├─ load template (open items only)
                              ├─ load slot state (fixed-size struct)
                              ├─ retrieve guidance notes for open items
                              ├─ Vertex AI: one structured-output call
                              │    → { transcript_span, slot_verdicts,
                              │        next_question, candidate_flags }
                              ├─ evaluate depends_on → recompute required set
                              └─ write Firestore
                                   └─ realtime listener ──▶ UI updates
```

**The slot state is the state, not the transcript.** Each call carries only the
open template items, a fixed-size struct of current slot values, and the new
audio. Context is bounded and roughly constant regardless of interview length.
See ADR-0002.

## Session lifecycle

1. Practitioner selects a template. Required set computed from `required` plus
   `depends_on` evaluation against an empty slot state.
2. Recording starts; indicator stays visible for the whole session.
3. Per chunk: adjudicate, update slots, recompute the required set, propose
   highlights. Highlight confirm/dismiss writes to the practitioner profile.
4. Practitioner requests the report. The gate evaluates every required item.
5. Each unresolved item must reach **answered** (with span), **declined** (with
   reason), or **escalated** (agent drafts and files a follow-up action).
6. Report generated, edited in-browser, shared. Transcript may be discarded.

## Adjudication contract

The core judgement: *does what was said constitute a substantive answer to this
required item?* Inputs are the item definition, its retrieved guidance note, and
the candidate transcript span. Output per item is a verdict, a confidence, and
the span relied upon.

Scoped **per item**, so a wrong verdict on one item cannot corrupt another.

Correctness is measured, not assumed — see `eval/`. The bar: never mark an
answer sufficient that a labelled case marks insufficient.

## Data model _(planned)_

```
sessions/{sessionId}
  templateId, startedAt, status, practitionerId
  slots/{itemId}   → state: open|answered|declined|escalated
                     value, evidenceSpan, verdictConfidence, resolvedAt
  followups/{id}   → itemId, reason, destination, draftedAt
  chunks/{seq}     → receivedAt, processedAt, retryCount

templates/{templateId}          → the config artifact (ADR-0003)
guidance/{templateId}/{chunkId} → guidance note text + embedding
practitioners/{practitionerId}  → highlight acceptance rates by category,
                                  phrasing preferences, report voice
```

No interviewee identity is stored anywhere. See ADR-0007.

## External dependencies

- **Vertex AI** — `gemini-3.6-flash`, structured output, native audio input.
  Chosen over the Gemini API so Vertex AI logs double as the contest's required
  visual proof of Google Cloud deployment.
- **Firestore** — realtime listeners, offline persistence, vector search for
  guidance retrieval (verify GA status; a small in-memory index is an acceptable
  fallback).
- **Google ADK (Python)** — agent orchestration. Note ADK 2.x had breaking
  changes immediately before this project started; versions are pinned.

## Failure modes _(planned — required by the Architectural Discipline criterion)_

| Failure | Handling |
|---|---|
| Chunk POST fails | Local queue in the browser, retry with backoff, ordered replay |
| Malformed structured output | Retry once with a stricter reprompt, then mark the chunk degraded and continue — never drop the session |
| Network drops mid-session | Chunks queue locally; on reconnect, replay in order and reconcile slot state server-side |
| Cloud Run instance recycles | No impact — state lives in Firestore, not ADK sessions (ADR-0004) |

## Deployment

Cloud Run service (`intake-agent`), source deploy via Cloud Build. Firestore in
the same region. Web client built statically and served from anywhere. The app
does not need to be live during judging, but proof of Cloud deployment must be
captured in the demo video before anything is switched off.
