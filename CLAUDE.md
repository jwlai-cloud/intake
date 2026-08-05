# Intake — agent working notes

*Your second chair. Nothing leaves the room unanswered.*

Read `docs/PROGRESS.md` before doing anything. It is the source of truth for
current state — do not re-derive state from the diff or from memory.

## What this is

A web app for a professional running a structured interview against a
**mandated form** (a community nurse doing a care assessment; an insurance
loss adjuster inspecting damage). It listens to the conversation, tracks
which required items have a **substantive answer**, surfaces the remaining
gaps **while the interview is still running**, and resolves every mandatory
item into one of three states before producing the report.

## The one-sentence differentiator

Every competitor ticks an item when it is **mentioned**. Intake ticks when it
is **answered**. Microsoft Teams' Facilitator marks a topic "once the
discussion for that topic has started"; Balto ticks when an item is
mentioned; Otter Live Assist checks off objectives. None of them adjudicate
whether a required item actually received a real answer, and none of them
gate the output.

If a change would weaken answer-level adjudication, it is the wrong change.

## Hard constraints (contest)

All Things Agentic Hackathon · **deadline 31 Aug 2026, 5:00pm PT** · track
Collaborative Partner.

- **Mandatory stack:** Gemini 3.5+ via Gemini API or Vertex AI · one Google
  agent framework (we use **ADK Python**) · one Google Cloud infra service
  (we use **Cloud Run + Firestore**). All three must be genuinely used.
- **New work only.** Everything must be created during 3–31 Aug 2026. Any
  pre-existing code must be disclosed in the submission text.
- The demo video must show **unedited live execution** and **visible proof of
  Google Cloud** (Vertex AI logs or the Cloud Run dashboard).
- Repo is **public**, and the README's spin-up instructions are explicitly
  scored. Keep them accurate and runnable.

## Locked decisions (see docs/adr/)

| Decision | Where |
|---|---|
| Web-first React; iOS deferred to Shipaton in September | ADR-0001 |
| Chunked audio, not bidirectional streaming — bounded state model | ADR-0002 |
| Template-as-config; zero domain logic in code | ADR-0003 |
| Own session state in Firestore, not ADK's default sessions | ADR-0004 |
| Three-state gate: answered / declined / escalated | ADR-0005 |
| The agent never authors domain content | ADR-0006 |
| Practitioner-scoped memory only; no interviewee identity | ADR-0007 |

## Rules that are not negotiable

**Never commit real client or employer material.** `templates/private/` and
`*.private.json` are gitignored. The repo and the demo video both use a
**synthetic** template derived from published standards, never a real
employer form. This repo is public and the video is public on YouTube.

**No interviewee identity, ever.** No names, no identifiers, no per-subject
history. Sessions are scoped to a job, not a person. Memory is scoped to the
practitioner (which highlight categories she dismisses, her phrasing, her
report voice). This is a design guarantee, not a policy — do not add a
"client name" field.

**The agent never authors domain content.** It tracks coverage against a
human-authored form and quotes the transcript span it relied on. Say
"item M14 has no recorded answer", never "this may indicate falls risk".
For items flagged `high_risk`, offer **no** suggested answer at all — show
the transcript quote and let the human write it.

**Do not build bidirectional streaming.** Chunk audio at 15–20s and POST.
This is a deliberate architectural decision (ADR-0002), not a shortcut: the
**slot state is the state**, not the transcript, so context stays bounded
regardless of interview length. Also: no audio output — suggestions render on
screen only.

## Build order

The adjudicator comes first, before any UI. It is the whole product.

1. **Adjudicator + eval harness.** `eval/` holds ~30 labelled cases: for each
   required item, answers that should count and answers that shouldn't.
   Target: never ticks an answer labelled insufficient. Run it before writing
   UI. If it can't separate *"a couple of wobbles"* from *"three falls, the
   last in May on the stairs"*, stop and tell the human.
2. ADK agent on Cloud Run wrapping it. Firestore session schema. Conditional
   branching (`depends_on`).
3. React front end: mic → chunks → POST; Firestore listener → coverage ring,
   next-question card, highlight chips.
4. Three-state gate. Report generation, in-browser edit, share.
5. Second template (loss adjusting). If this needs code changes, the engine
   isn't decoupled — fix the engine, not the template.
6. Failure tolerance: chunk retry with local queue, malformed-output reprompt,
   network-drop reconciliation. Named on the architecture diagram.

## Working practice

- Read `docs/PROGRESS.md` first; update it at the **end of every session**
  with what's done, what's next in priority order, and new open questions.
- Write the ADR when a decision is made, not retroactively.
- Keep `docs/ARCHITECTURE.md` a snapshot of *now* — replace, don't append.
- **Check current SDK docs before writing integration code.** ADK 2.x had
  breaking changes in the week before this project started (2.6.2 shipped
  4 Aug 2026); agents subclass `BaseNode`, callbacks and event schemas moved.
  Any tutorial predating ADK 2.0 will not copy-paste. Pin versions.
- Small, reviewable commits with messages that make sense in `git log` later.
  A judge sometimes reads commit history.
