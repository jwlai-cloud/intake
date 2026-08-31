# Devpost story — copy into the submission form

> Written in first person singular. If you're entering as a team, swap "I" for
> "we" throughout.

## Inspiration

A community nurse gets ninety minutes for a home visit, and a form she legally
has to finish. She asks about falls in the last twelve months. The person says:

> *"Oh, I've had a couple of wobbles."*

Every AI scribe I looked at ticks that item. It got mentioned, so it's covered.
But nothing was actually recorded. The nurse finds out that evening, back at her
desk, when the person is no longer in front of her. Now it's a phone call, or a
guess, or another visit.

So I went and checked what's shipping. Microsoft Teams' Facilitator marks a
topic covered "once the discussion for that topic has started". Balto ticks on
mention. Otter checks off objectives. None of them ask whether the item actually
got answered, and none of them stop you filing a report that's missing things.

I don't think that's laziness. Mention-detection is easy. Deciding whether "a
couple of wobbles" satisfies a rule that asks for "the number of falls and the
circumstances of the most recent" is a judgement call, and judgement calls are
where these products usually go wrong. That's the whole bet: can you make that
judgement reliably enough to gate a legal document on it?

## What it does

Intake sits alongside a professional running an interview against a mandated
form. A community nurse doing a care assessment. An insurance loss adjuster
inspecting damage.

It listens in 15 to 20 second chunks. For each required item on the form, it
decides whether that item has actually been answered, judged against a guidance
note a human wrote. Then it does three things a scribe doesn't do.

It shows you the gap while the person is still there. A coverage ring, the next
question worth asking phrased so you can just say it, and highlight chips
quoting what was actually said.

It won't produce the report while anything is blank. Every required item has to
land in one of three states first:

- **Answered**, with the exact words it came from
- **Declined**, recorded properly, and only on items where the form allows it
- **Escalated**, with a follow-up the agent writes and routes itself

The refusal isn't a dead end. If it were, people would switch it off. When it
blocks you it tells you what's outstanding, what each item is still missing, and
whether you're even allowed to record a decline — so the screen offers all three
ways forward.

The escalation is the part I'd point at. Give it an item nobody could close and
it writes what's still not recorded, in the form's own language, plus why it
couldn't be closed, then picks a destination off a fixed list. "Home access and
hazards, not recorded during the visit, to the occupational therapy queue." It
decided that on its own and filed it.

Two rules are enforced by code, not by asking the model nicely. The agent never
writes answers — the coach's output schema has a slot for a question and a slot
for quotes and literally nowhere to put an answer, so it can't. And no
interviewee identity is stored anywhere. Sessions belong to a job and a
practitioner, never to a named person.

## How we built it

Gemini 3.6 Flash on Vertex AI. Google ADK 2.6.2 in Python. Cloud Run, with state
in Firestore, the API key in Secret Manager, and the agent's own audit trail in
Cloud Logging.

It is audio in, not text. Real speech, chunked at 15 to 20 seconds, transcribed
with speaker attribution and then judged. The transcription is Gemini 3.6 Flash
itself rather than a speech-to-text service — I need to know *who* said
something, not just what was said, because an answer only counts when it came
from the person being interviewed and not from the nurse restating it. One
multimodal call gives me both — the vagueness of a spoken answer is
the whole signal, and it does not survive a text-only pipeline.

One chunk of audio in, one turn of work out:

```
transcribe → route → adjudicate (one call per open item) → coach
```

The important design decision is that the slot state is the state, not the
transcript. The obvious way to build this is to keep the whole conversation and
ask the model "what's missing?" every turn. A forty-five minute interview then
costs tens of thousands of tokens and gets worse as it grows. Instead every call
only sees the still-open items, a fixed-size struct, and the new audio. A
three-hour interview costs the same per chunk as a ten-minute one.

Adjudication is one separate call per open item rather than one big prompt.
Three reasons. A wrong verdict on one item can't leak into another. Each item
becomes its own scoreable eval case. And running them concurrently costs about
the same wall time as running one, which surprised me — fanning out is normally
the expensive option.

There's a routing step in front of it. Without it every open item got judged
against every chunk, and each one separately decided a vague remark was relevant
to it. "A couple of wobbles" was landing under mobility, memory and low mood as
well as falls. One cheap classification call first dropped items touched from
seven to two, and the bill with it.

I wrote the eval before the UI. There are 47 labelled cases — for each item,
answers that should count and answers that shouldn't — and the harness exits
non-zero if anything labelled insufficient ever gets marked sufficient. The bar
is deliberately lopsided. Being too strict costs one extra question. Being too
lenient leaves a blank field in a legal document. So the first line of the
prompt is: default to insufficient.

Everything domain-specific is config. A second template for insurance loss
adjusting runs on the same engine with no code changed.

## Challenges we ran into

ADK 2.x moves fast, and my own notes about it were wrong. I'd written down that
I couldn't migrate to the new graph Workflow API because "Workflow can't take an
LlmAgent as a sub-agent". The actual deprecation warning says the opposite — a
Workflow can't be nested *inside* an LlmAgent. When I retested it properly I
found the real problem, which is different: graph nodes emit events with no
`content`, and ADK's own eval CLI throws those out and fails the entire case. So
the deprecated orchestrator and the current graph are both incompatible with
ADK's current eval tooling, and a four-line custom BaseAgent is the only version
I can actually evaluate. After that I stopped trusting write-ups and started
running `inspect` against the installed package for every API claim.

The one that actually mattered I found two days before the deadline, by asking
someone to open the deployed app and talk into it. Nothing visibly happened.

Chunks were arriving, HTTP 200, the pipeline was running — and every turn
finished in about a tenth of a second having done nothing. A real turn takes six
seconds. The transcriber labels each turn `practitioner` or `interviewee`, and
adjudication only reads `interviewee` turns. One person testing alone is a
single voice, and the model reasonably labelled it `practitioner`. Every chunk
was discarded and the screen sat inert.

I had tested the API with curl, the text path, and an automated browser capture
— but that capture runs Chromium with a fake audio device. I had verified a
proxy for the product and called it the product.

Where the fix went matters more than the fix. My first attempt relaxed the
filter in adjudication, and it immediately broke a test asserting that a nurse
restating an answer must never close an item. Same input, two opposite correct
answers — the adjudicator can't tell a lone tester from a professional
summarising. The transcriber can: it's the only stage that hears how many people
are in the room.

I also caused a privacy leak and had to fix it. Vertex errors echo the request
that caused them, and the adjudicator's request body is the interviewee talking.
So a malformed chunk was writing what a patient said into Cloud Logging, which
sticks around longer than the session does. Logs only carry the exception type
now.

The demo video failed twice before it rendered, and neither error said what was
actually wrong. The capture script was seeding the access code into
sessionStorage after the client had switched to localStorage. And the web app
was still pointed at a local backend that wasn't running.

## Accomplishments that we're proud of

47 labelled cases, and 100% precision on "sufficient". It has never once ticked
an answer a human marked insufficient. Accuracy moves around between 45 and 47
depending on the run, because sometimes it's stricter than my label — but every
one of those is it being too careful, which costs a question, not a wrong tick.
Precision is the number that holds. I'd rather say that than quote my best run.

Twelve of the cases exist specifically to break it, and one of them did:

> *"Three falls, and the last was in May on the stairs."*
> *"No, hang on, I'm thinking of my sister. I've not actually fallen myself, not
> that I can bring to mind."*

It read the retraction as a clean "no falls" and ticked the item. But a
contradiction settled by a hedge is the nurse's call, not the agent's. The fix
was a rule: a later turn only overrides an earlier one if it's itself a clear
answer or a clear refusal. Hand-testing would never have caught that.

There's a second eval over the whole pipeline, six scenarios, scoring 18/18. All
the metrics are plain Python rather than an LLM judge — asking a model whether a
quote is verbatim is slower, costs money, and is worse than `in`. Those metrics
caught something real: the coach's schema stops it writing an answer, but it
doesn't stop it writing an opinion in the title. It had produced a highlight
called "Formal decline to answer alcohol question". That's a characterisation of
a person, not a topic. Titles are plain noun phrases now and that exact string
is a test.

116 backend tests. An OWASP pass over the HTTP surface. And quotes are checked
in code now — if the span isn't actually in the transcript it gets dropped
rather than shown to a nurse as something the person said.

## What we learned

Write the nasty eval cases first. Mine found a real bug within an hour. A test
set that passes 100% the first time isn't telling you anything.

Read the installed package instead of the docs. The one time I trusted a written
note, it was wrong in the exact direction that blocked me for three days.

A feature can be wired, deployed, and quietly doing nothing. Memory shipped and
persisted, and I'd written it into the description as working. When someone
asked what it did, I looked at the production data instead of the code: every
practitioner record had learned exactly zero phrasings. The condition required
an item to go straight from open to answered, and items are normally raised
vaguely first — so the one case that actually happens was the one case excluded.
Nothing errored. Nothing logged. It just never fired.

And a guarantee that only exists in a prompt isn't a guarantee. Every rule that
survived is enforced by a schema, a fixed list, or a substring check. The ones
that lived in an instruction are the ones that broke.

## What's next for Intake

More memory. It now learns two things across a practitioner's interviews: a
question phrasing that closed an item on the first ask, and the categories whose
highlights she keeps dismissing. From her second interview the coach offers back
a wording that worked, and stops suggesting the chips she throws away — while
still asking the required question, because muting a suggestion must never mute
an obligation.

What it deliberately doesn't learn is anything about the people interviewed.
"People like this one usually under-report falls" would be useful and would
break the privacy property that makes this deployable, so there's a guard that
refuses any candidate that's quoted, isn't a question, or has a first-person
subject — and a test that feeds it five samples of real interviewee speech and
fails if any of them survives.

Next would be report voice, and letting a whole team pool phrasings rather than
each nurse starting cold.

Real per-user auth. Right now access is one shared key plus session ids that are
128 bits of randomness. It works, but it stops working the moment an id ends up
in a log or on a shared screen. Firebase Auth with an owner on each session is
designed and not built.

Transactional writes. Firestore updates are read-then-write with no transaction,
so two chunks arriving together can lose one. The browser sends them in order so
it doesn't happen normally, but "doesn't happen normally" isn't good enough for
a clinical record.

All three are in the README under Known limitations. If a reviewer is going to
find them, I'd rather they find them there.
