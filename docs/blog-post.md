# The difference between "mentioned" and "answered"

*Built for the All Things Agentic Hackathon, August 2026. Source:
[github.com/…/intake](https://github.com/) · Track: Collaborative Partner*

A community nurse has ninety minutes and a form she is legally required to
complete. She asks about falls in the last twelve months. The answer is:

> *"Oh, I've had a couple of wobbles."*

Every AI scribe on the market ticks that item. It was mentioned. It was never
answered. She finds the gap that evening, at her desk, with the door shut — and
now she needs a phone call, a guess, or a second visit.

That gap is the entire product.

## Why every competitor ticks the box

I looked at what's shipping. Microsoft Teams' Facilitator marks a topic covered
"once the discussion for that topic has started". Balto ticks when an item is
mentioned. Otter's Live Assist checks off objectives. None of them adjudicate
whether a required item actually *received a real answer*, and none of them gate
the output on it.

That's not laziness on their part — mention-detection is a much easier problem.
Deciding whether *"a couple of wobbles"* satisfies a form's requirement for "the
number of falls and the circumstances of the most recent" is a judgement call,
and judgement calls are where LLM products quietly go wrong.

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
question. A false *sufficient* is a silently blank field in a legal document.
So the prompt's first rule is: **default to insufficient — if you're weighing it
up, it's insufficient.**

Twelve of those cases are adversarial, and writing them was the single highest-
value hour of the build. They found a real bug immediately:

> *"Three falls, and the last was in May on the stairs."*
> *"No, hang on — I'm thinking of my sister. I've not actually fallen myself,
> not that I can bring to mind."*

The adjudicator read the retraction as a clean nil return and **ticked the
item**. The record now held a contradiction settled only by a hedge, which is a
practitioner's call, not the agent's. The fix was a rule: the later turn governs
only when it is itself a clear answer or a clear refusal.

I'd never have found that by hand-testing. The set that scores 100% is the set
that can't tell you anything.

## The architecture, and the two decisions worth defending

The backend is **Google ADK 2.6.2 on Cloud Run**, calling **Gemini 3.6 Flash on
Vertex AI**, with session state in **Firestore**. One audio chunk in, one bounded
turn out:

```
transcribe → route → adjudicate (fanned out) → coach
```

**The slot state is the state, not the transcript.** The naive design
accumulates the conversation and re-asks the model "what's still missing?" every
turn. A forty-five minute interview becomes tens of thousands of growing tokens —
expensive, and degrading as it grows. Instead each call gets the open items, a
fixed-size struct of current values, and the new audio. A three-hour interview
costs the same per chunk as a ten-minute one.

**Adjudication is one isolated call per open item, not one big prompt.** Three
reasons, in order: a wrong verdict on one item can't corrupt another; each item
is separately scoreable by the eval; and *k* concurrent calls cost about one
call's wall time. That last one surprises people — fanning out is usually the
expensive choice, and here it's free.

Between them sits a router. Without it, every open item was adjudicated against
every chunk, and each independently decided a vague remark was relevant to it —
so *"a couple of wobbles"* attached itself to mobility, memory, and low mood as
well as falls. One cheap classification call first cut items touched from seven
to two, and cut cost with it.

## The rules that are enforced by types, not prompts

Two constraints do a lot of work:

**The agent never authors domain content.** It tracks coverage against a
human-authored form and quotes the span it relied on. It says *"item M14 has no
recorded answer"*, never *"this may indicate falls risk"*. That's not a prompt
instruction — the coach's output schema has fields for a question and for quotes
and **no field an answer could go into**. It structurally cannot suggest one.

Behavioural evaluation found the hole in that anyway. The schema forbids an
answer *field*; it doesn't forbid an interpretive *label*. The agent had emitted
a highlight titled *"Formal decline to answer alcohol question"* — a
characterisation, not a quote. Titles are bare noun phrases now.

**No interviewee identity, ever.** No names, no identifiers, no per-subject
history. Sessions are scoped to a job, not a person. Persistent memory is scoped
to the *practitioner*.

The honest version of that claim is narrower than the slogan, and it's worth
stating precisely: recorded answers are verbatim quotes, and a real interviewee
says *"my daughter Sarah drives me on Mondays"*. Redacting that would break
adjudication, so identity is a **retention** answer, not a redaction one — quotes
live in the session document, are never written to logs, and go when the session
goes.

That last part was a real bug. A Vertex error response echoes the offending
request, and the adjudicator's request body *is* the transcript — so a malformed
chunk was writing interviewee speech into Cloud Logging, which outlives the
session document. Logs now carry the exception *type* only.

## Nothing is ever silently blank

The output is gated. Before a report is produced, every required item resolves
into exactly one of three states:

| | |
|---|---|
| **Answered** | with the transcript span it was drawn from |
| **Declined** | formally recorded, with a reason — and only where the form permits it |
| **Escalated** | the agent drafts the follow-up action itself and routes it |

The gate is a router, not a wall. That distinction matters: a copilot that only
says *no* is one practitioners switch off. When it refuses, the response carries
what's outstanding, what's missing from each, and whether a decline is even
permitted — so the UI can offer all three ways out.

The escalation is the part I'd point at. Given an unresolved item, the agent
writes what's still not recorded in the form's own terms, why it couldn't be
closed, and picks a destination from a closed list. *"Home access and hazards ·
not recorded during the visit → Occupational therapy queue."* Unprompted
judgement, a real artifact, filed.

## Things that cost me time

- **`GOOGLE_GENAI_USE_VERTEXAI=TRUE` is mandatory for ADK.** Without it, ADK
  builds its own AI Studio client and dies with "No API key was provided" — even
  though a hand-built `genai.Client(vertexai=True)` in the same process works.
- **`SequentialAgent` is deprecated in ADK 2.6.2**, and more importantly it emits
  a container event with no `content`. `agents-cli eval generate` rejects any
  content-less event, so ADK's deprecated orchestrator is incompatible with ADK's
  current eval tooling. Sequential composition is a four-line loop; I own it now.
- **`google-adk==2.6.2` requires `google-genai>=2.9`.** Pin them together.
- **An ADK agent may have exactly one parent.** Module-level `LlmAgent`
  singletons can't be shared between pipelines. Use factories.
- **Firestore native mode vs Datastore mode.** A Datastore-mode project builds a
  `firestore.Client` happily and fails only on the first write. A try/except
  around the constructor proves nothing; probe with a real read.

The general lesson, for an SDK this young: read signatures off the installed
package with `inspect`, not off documentation. Every API claim in this project
was verified that way, and the one time I trusted a note instead, it was wrong.

## Where it stands

47 labelled cases, **100% precision on `sufficient`** — it has never once ticked
an answer a human labelled insufficient. Accuracy moves between runs (45–47 of
47) because the adjudicator is occasionally stricter than a labelled case; every
one of those misses is a false *insufficient*, which costs a question and never a
wrong tick. 68 backend tests. A second template — insurance loss adjusting —
runs on the same engine with no code change, which is the test of whether the
vertical is really just config.

What I'd build next is memory: the app already records which proposed highlights
the practitioner keeps and which she throws away, and does nothing with it. The
useful thing to learn isn't about the people being interviewed — it's which
*question phrasings* actually close which items, across every interview. That's a
mentor. The other version isn't one, and it would break the privacy guarantee
that makes this deployable at all.
