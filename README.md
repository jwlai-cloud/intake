# Intake

**Your second chair. Nothing leaves the room unanswered.**

Intake is a Collaborative Partner agent for professionals who run a structured
interview against a mandated form — a community nurse doing a care assessment,
an insurance loss adjuster inspecting damage, a safety inspector on site.

It listens to the conversation, tracks which required items have received a
**substantive answer**, surfaces the remaining gaps **while the interview is
still running and the person can still answer**, and resolves every mandatory
item before producing the report.

> Every AI scribe tells you what you said. Intake tells you what you haven't
> asked yet.

## The distinction that matters

Existing tools tick an item when it is **mentioned**. Intake ticks when it is
**answered**.

Ask *"falls in the last 12 months"* and get *"oh, I've had a couple of
wobbles"* — a mention-level tracker marks the topic covered. Intake does not.
It keeps the item open and says what's still needed: a count and the
circumstances.

## Nothing is ever silently blank

Before Intake will produce a report, every mandatory item resolves into
exactly one of three states:

| State | Meaning |
|---|---|
| **Answered** | With the transcript span it was drawn from, as evidence |
| **Declined** | Formally recorded as declined, with a reason |
| **Escalated** | The agent drafts and files a follow-up action: what is outstanding, why it could not be closed, and where it needs to go |

The gate is a router, not a wall. It never forces a fabricated answer and it
never lets an omission pass silently.

## Architecture

```
React (browser)                       Google Cloud
┌───────────────────────┐            ┌──────────────────────────────────────┐
│ mic → 18s chunks      │──POST────▶ │ Cloud Run · FastAPI + ADK Python     │
│ local queue + replay  │            │  SequentialAgent "intake_turn"       │
│                       │            │   1. transcriber   LlmAgent          │
│ coverage ring         │            │   2. adjudication  custom BaseAgent  │
│ next-question card    │            │      └─ one call per open item,      │
│ highlight chips       │            │         fanned out concurrently      │
│ three-state gate      │            │   3. coach         LlmAgent          │
│ report editor         │◀───────────│ Vertex AI gemini-3.6-flash           │
└───────────────────────┘            │ Firestore (session state)            │
                                     └──────────────────────────────────────┘
```

Each chunk costs one transcription call, one adjudication call **per still-open
item** run concurrently, and one coaching call. Adjudication is fanned out
rather than folded into a single prompt so that a wrong verdict on one item
cannot corrupt another, and so each item's judgement is separately scoreable by
`eval/`.

The **slot state is the state**, not the transcript. The coach sees a brief of
open items and this chunk's quotes; adjudication sees a 12-turn window. Context
stays bounded regardless of interview length — a three-hour session costs the
same per chunk as a ten-minute one.

See `docs/ARCHITECTURE.md` for detail and `docs/adr/` for why.

## Spin-up

### Prerequisites

- A Google Cloud project with billing enabled and the Vertex AI API on
- `gcloud auth application-default login`
- Python 3.11+ with [`uv`](https://docs.astral.sh/uv/), and Node 20+

### 1. Configure

```bash
cp .env.example .env
# edit .env: GOOGLE_CLOUD_PROJECT, and leave GOOGLE_GENAI_USE_VERTEXAI=TRUE
gcloud services enable aiplatform.googleapis.com firestore.googleapis.com \
  run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

If your shell exports `GOOGLE_APPLICATION_CREDENTIALS`, **unset it**. A service
account key file in that variable silently overrides
`gcloud auth application-default login`, so every call authenticates as that
service account against whichever project owns it — including, if you are not
watching, a completely different one from the project in your `.env`.

```bash
unset GOOGLE_APPLICATION_CREDENTIALS
```

Firestore must be in **native mode**. If your project's default database is in
Datastore mode, create a named one and point at it:

```bash
gcloud firestore databases create --database=intake --location=us-central1 --type=firestore-native
echo 'FIRESTORE_DATABASE=intake' >> .env
```

You can also skip Firestore entirely — set `INTAKE_STORE=memory` and everything
runs, minus durability. `GET /health` always tells you which store is live.

### 2. Verify the adjudicator before anything else

The adjudicator is the product, so it is the first thing to run:

```bash
uv run --group dev pytest backend/tests -q   # 51 tests, no network
cd eval && uv run python run_eval.py         # 47 labelled cases, real Vertex calls
```

`run_eval.py` prints a confusion matrix and **exits non-zero if any answer
labelled insufficient was marked sufficient**. Current score: **46/47, precision
on `sufficient` 100%** over 47 cases, with one deliberate non-critical miss.
Do not move on to the UI until this passes.

### 3. Run it locally

```bash
# terminal 1 — agent service
set -a && . ./.env && set +a
uv run uvicorn intake_agent.main:app --port 8000 --app-dir backend

# terminal 2 — web client
cd web && npm install && npm run dev      # http://localhost:5173
```

Pick a template, press **Start recording** and grant microphone permission — or
type turns into the box beside it, which drives the identical pipeline and is
the fallback when the room is too noisy to record.

### 4. Deploy to Cloud Run

```bash
printf 'choose-a-long-random-string' | gcloud secrets create intake-api-key --data-file=-
./backend/deploy.sh
```

Then build the client against it:

```bash
cd web && VITE_API_BASE=https://intake-agent-xxxx.run.app npm run build
```

**The access code is never built in.** Vite inlines `import.meta.env.*` at build
time, so a `VITE_API_KEY` would ship readable inside the JS bundle — a published
credential to an endpoint that spends money on Vertex AI per request. The app
asks for the code instead and keeps it in `sessionStorage` for that tab only.

Every request that costs money requires `X-Intake-Key` and is rate limited per
key. The service refuses to start ungated: with no `INTAKE_API_KEY` set it
answers 503 unless `INTAKE_ALLOW_UNGATED=1` is set explicitly, which belongs in
local `.env` and never in a deploy.

## Templates

The entire vertical lives in a JSON template. No domain logic exists in code.

```jsonc
{
  "id": "M14",
  "prompt": "Falls in the last 12 months",
  "required": true,
  "answer_type": "structured",
  "high_risk": true,          // no AI suggestion — quote only, human writes it
  "accepts_declined": true,   // "declined, reason X" is a real answer
  "guidance_ref": "§3.4",     // where the guidance note came from
  "guidance": "A sufficient answer records the number of falls and the circumstances of the most recent occurrence. Vague quantifiers such as 'a few' are not sufficient.",

  // Conditional items become required only when the condition holds.
  // `when` is a closed set — answered | answered_and_matches — not an
  // expression language: templates are authored by domain experts, and an
  // eval'd expression in a config file is an injection surface.
  "depends_on": { "item": "M14", "when": "answered_and_matches", "pattern": "(?i)\\b(one|two|three|[1-9][0-9]*)\\b" }
}
```

The `guidance` note is what the adjudicator judges against, and it is
authoritative over the model's own taste. That is the whole mechanism: change
the note, change what counts as an answer, with no code change.

`templates/` holds two synthetic examples — community nursing and insurance
loss adjusting. Swapping between them requires no code change; that is the
point, and it is the test of whether the engine is honestly decoupled.

**Real client or employer forms are never committed.** `templates/private/`
and `*.private.json` are gitignored. The examples here are derived from
published standards.

## Privacy by architecture

Intake **never solicits, indexes or keys on the identity of the person being
interviewed.** There is no name field, no subject identifier, and no
per-subject history; sessions are scoped to a job, not a person.

Stated precisely, because the honest version is narrower than the slogan:
recorded answers are **verbatim quotes**, and a real interviewee may say a name
in passing — *"my daughter Sarah drives me on Mondays"*. That span is stored as
spoken, because quoting exactly is the evidence the product rests on and
redacting it would break adjudication. What follows from that is a retention
answer rather than a redaction one: quotes live in the session document, they
are never copied into logs, and they are deleted when the session is.

Persistent memory is scoped to the *practitioner*: which highlight categories
she dismisses, how she phrases questions, her report voice.

## Scope of the agent's judgement

Intake tracks coverage against a human-authored form and quotes the transcript
span it relied on. It reports that *"item M14 has no recorded answer"* — never
that *"this may indicate falls risk"*. It does not diagnose, rank, recommend,
or imply a clinical or professional next action. For items marked `high_risk`
it offers no suggested answer at all: it shows the quote and the human writes
the answer.

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE.md) — source-available, free for any
noncommercial purpose, and free to read, fork and run for the judging of this
contest. Commercial use requires a separate licence. This is deliberately not
an OSI-approved open-source licence; the contest requires a public repo, not a
permissive one.

## Built for

[All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/)
— Collaborative Partner track. Gemini 3.6 Flash via Vertex AI · Google ADK
(Python) · Cloud Run · Firestore.
