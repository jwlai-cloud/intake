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
React (browser)                        Google Cloud
┌────────────────────────┐            ┌─────────────────────────────────┐
│ mic → 15–20s chunks    │──POST────▶ │ Cloud Run · ADK Python agent    │
│                        │            │   ├─ Vertex AI                  │
│ Firestore listener     │            │   │   gemini-3.6-flash          │
│  ├─ coverage ring      │            │   │   structured output         │
│  ├─ next-question card │            │   ├─ guidance-note retrieval    │
│  ├─ highlight chips    │            │   └─ practitioner style profile │
│  └─ three-state gate   │◀─realtime──│ Firestore (session state)       │
└────────────────────────┘            └─────────────────────────────────┘
```

One Gemini call per audio chunk performs transcription, slot adjudication,
conditional-branch evaluation, next-question generation and highlight
extraction together. The **slot state is the state**, not the transcript, so
context stays bounded regardless of interview length — a three-hour session
costs the same per chunk as a ten-minute one.

See `docs/ARCHITECTURE.md` for detail and `docs/adr/` for why.

## Spin-up

### Prerequisites

- A Google Cloud project with billing enabled, and Vertex AI and Firestore APIs on
- `gcloud` CLI authenticated (`gcloud auth application-default login`)
- Python 3.11+ with [`uv`](https://docs.astral.sh/uv/)
- Node 20+

### 1. Configure

```bash
cp .env.example .env
# then edit .env: set GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION
```

Enable the required services and create the Firestore database:

```bash
gcloud services enable aiplatform.googleapis.com firestore.googleapis.com run.googleapis.com
gcloud firestore databases create --location=us-central1
```

### 2. Backend, locally

```bash
cd backend
uv sync
uv run uvicorn intake_agent.main:app --reload --port 8000
```

### 3. Verify the adjudicator before anything else

The adjudicator is the product. Run its eval harness first:

```bash
cd eval
uv run python run_eval.py
```

This scores the model against the labelled cases in `eval/cases/`. The bar:
**it must never mark an answer sufficient that a case labels insufficient.**
Do not move on to the UI until this passes.

### 4. Front end

```bash
cd web
npm install
npm run dev        # http://localhost:5173
```

Grant microphone permission when prompted. A recording indicator stays visible
for the whole session.

### 5. Deploy to Cloud Run

```bash
cd backend
gcloud run deploy intake-agent \
  --source . \
  --region us-central1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GEMINI_MODEL=gemini-3.6-flash \
  --allow-unauthenticated
```

Then point the front end at the deployed URL via `VITE_API_BASE` and build:

```bash
cd web && VITE_API_BASE=https://intake-agent-xxxxx.run.app npm run build
```

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
  "guidance_ref": "p12 §4.2", // retrieval target for judging sufficiency
  "depends_on": { "item": "M13", "when": "count > 0" }
}
```

`templates/` holds two synthetic examples — community nursing and insurance
loss adjusting. Swapping between them requires no code change; that is the
point, and it is the test of whether the engine is honestly decoupled.

**Real client or employer forms are never committed.** `templates/private/`
and `*.private.json` are gitignored. The examples here are derived from
published standards.

## Privacy by architecture

Intake stores **no identity of the person being interviewed** — no names, no
identifiers, no per-subject history. Sessions are scoped to a job, not a
person, and the transcript can be discarded on session close.

Persistent memory is scoped to the *practitioner*: which highlight categories
she dismisses, how she phrases questions, her report voice.

## Scope of the agent's judgement

Intake tracks coverage against a human-authored form and quotes the transcript
span it relied on. It reports that *"item M14 has no recorded answer"* — never
that *"this may indicate falls risk"*. It does not diagnose, rank, recommend,
or imply a clinical or professional next action. For items marked `high_risk`
it offers no suggested answer at all: it shows the quote and the human writes
the answer.

## Built for

[All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/)
— Collaborative Partner track. Gemini 3.6 Flash via Vertex AI · Google ADK
(Python) · Cloud Run · Firestore.
