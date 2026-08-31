---
title: "The difference between \"mentioned\" and \"answered\""
published: false
description: "Building an agent that adjudicates whether a required form item actually got answered — and refuses to file the report until every one has. Google ADK 2.6, Gemini 3.6 Flash, Cloud Run."
tags: googlecloud, ai, python, showdev
cover_image: https://raw.githubusercontent.com/jwlai-cloud/intake/master/docs/diagrams/gallery-1-scene.jpg
canonical_url: https://github.com/jwlai-cloud/intake
---

*I built this for the All Things Agentic Hackathon (August 2026). Code:
[github.com/jwlai-cloud/intake](https://github.com/jwlai-cloud/intake).
Set `published: true` in the front matter when you post it.*

A community nurse has ninety minutes and a form she is legally required to
complete. She asks about falls in the last twelve months. The answer is:

> *"Oh, I've had a couple of wobbles."*

Every AI scribe on the market ticks that item. It was mentioned. It was never
answered. She finds the gap that evening, at her desk — and now it needs a phone
call, a guess, or a second visit. The person who knew the answer was sitting
three feet away an hour ago.

That gap is the entire product.

## Why every competitor ticks the box

I looked at what's shipping. Microsoft Teams' Facilitator marks a topic covered
"once the discussion for that topic has started". Balto ticks when an item is
mentioned. Otter's Live Assist checks off objectives. None of them adjudicate
whether a required item actually *received a real answer*, and none of them gate
the output on it.

That's not laziness. Mention-detection is a much easier problem. Deciding
whether *"a couple of wobbles"* satisfies a form's requirement for "the number
of falls and the circumstances of the most recent" is a judgement call, and
judgement calls are where LLM products quietly go wrong.

So the whole project reduces to one question: **can you make that judgement
reliably enough to gate a report on it?**

## Build the judge first, and measure it

The first thing I built wasn't the UI. It was an eval harness.

`eval/` holds 47 labelled cases — for each required item, answers that should
count and answers that shouldn't. It scores the adjudicator against the live
service and **exits non-zero if any answer labelled insufficient was marked
sufficient**. That failure is the one that destroys the product, because it's
indistinguishable from the mention-level behaviour I'm claiming to beat.

The bar is asymmetric on purpose. A false *insufficient* costs one extra
question. A false *sufficient* is a silently blank field in a legal document. So
the prompt's first rule is: **default to insufficient — if you're weighing it up,
it's insufficient.**

Twelve of those cases are adversarial, and writing them was the single
highest-value hour of the build. They found a real bug immediately:

> *"Three falls, and the last was in May on the stairs."*
> *"No, hang on — I'm thinking of my sister. I've not actually fallen myself,
> not that I can bring to mind."*

The adjudicator read the retraction as a clean nil return and **ticked the
item**. The record now held a contradiction settled only by a hedge, which is a
practitioner's call, not the agent's. The fix was a rule: the later turn governs
only when it is itself a clear answer or a clear refusal.

I'd never have found that by hand-testing. A set that scores 100% on its first
run can't tell you anything.

## The architecture, and the two decisions worth defending

**Google ADK 2.6.2 on Cloud Run**, calling **Gemini 3.6 Flash on Vertex AI**,
with session state in **Firestore**. One audio chunk in, one bounded turn out:

```
transcribe → route → adjudicate (fanned out) → coach
```

**The slot state is the state, not the transcript.** The naive design
accumulates the conversation and re-asks the model "what's still missing?" every
turn. A forty-five minute interview becomes tens of thousands of growing tokens
— expensive, and degrading as it grows. Instead each call gets the open items, a
fixed-size struct of current values, and the new audio. A three-hour interview
costs the same per chunk as a ten-minute one.

**Adjudication is one isolated call per open item, not one big prompt.** Three
reasons, in order: a wrong verdict on one item can't corrupt another; each item
is separately scoreable by the eval; and *k* concurrent calls cost about one
call's wall time. That last one surprises people — fanning out is usually the
expensive choice, and here it's close to free.

Between them sits a router. Without it, every open item was adjudicated against
every chunk, and each independently decided a vague remark was relevant to it —
so *"a couple of wobbles"* attached itself to mobility, memory and low mood as
well as falls. One cheap classification call first cut items touched from seven
to two, and cut cost with it.

## The rules that are enforced by types, not prompts

**The agent never authors domain content.** It tracks coverage against a
human-authored form and quotes the span it relied on. It says *"item M14 has no
recorded answer"*, never *"this may indicate falls risk"*. That's not a prompt
instruction — the coach's output schema has fields for a question and for quotes
and **no field an answer could go into**. It structurally cannot suggest one.

Behavioural evaluation found the hole in that anyway. The schema forbids an
answer *field*; it doesn't forbid an interpretive *label*. The agent had emitted
a highlight titled *"Formal decline to answer alcohol question"* — a
characterisation, not a quote. Titles are bare noun phrases now, and that exact
string is a test case.

**No interviewee identity, ever.** Sessions are scoped to a job, not a person.
Persistent memory is scoped to the *practitioner*.

The honest version of that claim is narrower than the slogan. Recorded answers
are verbatim quotes, and a real interviewee says *"my daughter Sarah drives me on
Mondays"*. Redacting that would break adjudication, so identity is a
**retention** answer, not a redaction one — quotes live in the session document,
never in logs, and go when the session goes.

That last part was a real bug. A Vertex error response echoes the offending
request, and the adjudicator's request body *is* the transcript — so a malformed
chunk was writing interviewee speech into Cloud Logging, which outlives the
session document. Logs now carry the exception *type* only.

## What the agent learns, and what it refuses to

It gets better at helping one practitioner across her interviews. It learns
nothing about the people she interviews.

Two things, both about the professional: a question phrasing that closed an item
on the first ask, and the item ids whose highlights she keeps dismissing. From
her second interview the coach offers back a wording that worked, and stops
proposing chips she's binned — while still asking the required question, because
muting a suggestion must never mute an obligation.

The version that would demo better is the one it refuses to build. *"People like
this one usually under-report falls"* would be useful and would permanently
break the privacy property. The line between them is the line between a question
and an answer: the agent's own composition may cross sessions, a person
describing their own health may not. A guard rejects any candidate that's
quoted, isn't a question, or has a first-person subject — and a test feeds it
five samples of real interviewee speech and fails if any survives.

## Nothing is ever silently blank

Before a report is produced, every required item resolves into exactly one of
three states:

| | |
|---|---|
| **Answered** | with the transcript span it was drawn from |
| **Declined** | formally recorded, and only where the form permits it |
| **Escalated** | the agent drafts the follow-up itself and routes it |

The gate is a router, not a wall. A copilot that only says *no* is one
practitioners switch off. When it refuses, the response carries what's
outstanding, what's missing from each, and whether a decline is even permitted.

The escalation is the part I'd point at. Given an unresolved item, the agent
writes what's still not recorded in the form's own terms, why it couldn't be
closed, and picks a destination from a closed list. *"Home access and hazards ·
not recorded during the visit → Occupational therapy queue."* Unprompted
judgement, a real artifact, filed.

## Things that cost me time

- **`GOOGLE_GENAI_USE_VERTEXAI=TRUE` is mandatory for ADK.** Without it, ADK
  builds its own AI Studio client and dies with "No API key was provided" — even
  though a hand-built `genai.Client(vertexai=True)` in the same process works.
- **`SequentialAgent` is deprecated in 2.6.2**, and it emits a container event
  with no `content`. `agents-cli eval generate` rejects any content-less event,
  so ADK's deprecated orchestrator is incompatible with ADK's current eval
  tooling. Then I measured the replacement: the graph `Workflow` emits
  `Event(output=…, content=None)` and **fails identically**. A four-line custom
  `BaseAgent` is the only one of the three that can be evaluated.
- **I had the reason backwards for three days.** My notes said the graph
  migration was blocked because "Workflow cannot take an LlmAgent as a
  sub-agent". The warning says the *reverse* — a Workflow can't be nested
  *inside* an LlmAgent. Both are `BaseNode` subclasses and compose fine.
- **A 403 that looked like a spend cap wasn't.** `GOOGLE_APPLICATION_CREDENTIALS`
  in my shell pointed at an unrelated project's service account. It silently
  overrides application default credentials.
- **I was wrong about my own costs by a hundredfold.** I was sure the demo's
  text-to-speech dominated Vertex spend. Cloud Monitoring said TTS was 0.8% of
  tokens and the app itself was 66%. I'd estimated by counting files on disk
  instead of reading billing.

The general lesson, for an SDK this young: read signatures off the installed
package with `inspect`, not off documentation. Every API claim in this project
was verified that way, and the one time I trusted a note instead, it was wrong.

## The bug I found by finally doing the obvious thing

Two days before the deadline I asked someone to try the deployed app with a real
microphone. Nothing visibly happened.

Chunks were arriving, HTTP 200, the ADK pipeline was running — and every turn
finished in about a tenth of a second having done nothing. A real turn takes six
seconds.

The transcriber labels each turn `practitioner` or `interviewee`, and
adjudication only looks at `interviewee` turns. **One person testing alone is a
single voice, and the model reasonably labelled it `practitioner`.** Every chunk
was discarded. The screen sat inert — which is exactly what a judge trying it
alone would have seen.

I'd tested the API with curl, the text path, and an automated browser capture.
But that capture runs Chromium with `--use-fake-device-for-media-stream`. I had
verified a proxy for the product and called it the product.

The fix is one instruction, and *where* it went matters. My first attempt
relaxed the filter in the adjudicator, and it immediately broke a test asserting
that a nurse restating an answer must never close an item. Same input, two
opposite correct answers — the adjudicator can't tell a lone tester from a
professional summarising. The transcriber can: it's the only stage that hears
how many people are in the room. So it labels a lone voice as the interviewee,
and the downstream guarantee is untouched.

## Where it stands

47 labelled cases, **100% precision on `sufficient`** — it has never once ticked
an answer a human labelled insufficient. Accuracy moves between 45 and 47 across
runs because the adjudicator is occasionally *stricter* than a labelled case;
every one of those misses is a false insufficient, which costs a question and
never a wrong tick. 133 backend tests. A behavioural eval over the pipeline
scoring 18/18, graded by deterministic code rather than an LLM judge — asking a
model "is this quote verbatim?" is slower, costs money, and is worse than `in`.

A second template — insurance loss adjusting — runs on the same engine with no
code change, which is the test of whether the vertical is really just config.

What I'd build next is per-user identity. Access control today is a capability
model: one shared key, and session ids that are 128 bits of randomness. It
holds, but it stops holding the moment an id reaches a log or a shared screen.
