# Demo video — shot script

**Limit: 4:00** (`docs/strategy/02-rubric-fit.md` — "Demo video ≤4 min, public
on YouTube/Vimeo, English"). **Target 4:00 exactly.** Re-check the rules page before
uploading; over a hard limit disqualifies on some platforms. **Uses the full
four minutes — nothing padded, nothing rushed.**

## What the rubric actually asks the video to do

Straight from `02-rubric-fit.md`, because it shapes every choice below:

> *"Does the 4-minute video clearly define the friction being solved **and
> explain the architecture**?"*
>
> *"**The Proof of Action:** Does the video show an unedited, live execution of
> the agent performing its task (via **terminal logs, database updates**, or UI
> changes)?"*
>
> *"Is there **visual proof of Google Cloud deployment** in the video?"*

Three consequences:

1. **Architecture must be explained on camera.** Not implied by the demo. It
   gets its own segment.
2. **Terminal logs and database updates count as proof of action** — so the
   Cloud Run log stream and the live Firestore document are doing double duty:
   proof of action *and* proof of Google Cloud.
3. **The live segment must be unedited**, so the 19–23s per chunk cannot be cut
   out. It gets filled with (1) and (2) rather than removed.

## What must be unedited, and what must not waste a second

The rubric asks whether the video shows *"an unedited, live execution of the
agent performing its task"*. That is a claim about **the agent executing** — not
about the whole four minutes.

So the video has two régimes, and they get opposite treatment:

**The live window (2:25) — one continuous take, real time, no cuts.**
From pressing record to the report appearing. The agent transcribing, routing,
adjudicating, refusing the report and drafting an escalation all happen inside
it. The ~20s waits stay on camera, filled with the Cloud Run log stream and the
live Firestore document, which are themselves the scored proof of action. No
speed-ups anywhere — `04-full-spec-superseded.md` floated a labelled "×8" and
that document is superseded.

**Everything else — cut ruthlessly.** Hook, architecture, template swap, eval,
close. These are not the agent performing its task, so they carry no unedited
obligation, and every second in them must earn its place. Trim the moment a
point lands. Cut the eval's 26-second run down to the command and the result.

Budget the full 4:00. Nothing is padded and nothing is rushed.

| | Régime | Time |
|---|---|---|
| Hook | edited, tight | 0:00–0:22 |
| **Live window** | **unedited, real time** | **0:22–2:47** |
| Architecture | edited | 2:47–3:17 |
| Template swap + eval | edited | 3:17–3:47 |
| Close | edited | 3:47–4:00 |

## The pacing problem, and the honest fix

A chunk takes **19–23 seconds** end to end. Measured on the deployed service.
Two answer beats therefore cost ~40s inside the live window that cannot be
edited away — and should not be, because that is where the Cloud Run and
Firestore proof lives.

`01-build-plan.md:47` already had the answer: **don't shrink the form to fit
the video.** Load the real 15-item form, open with coverage already partway
complete, and run the unedited window across the last few items. A short form
makes the gate look trivial; a full form with a short live window keeps the
stake and fits the runtime.

So: run a session up to ~11 of 15 *before* recording, then start the take.

**Say what is actually true, not a flattering version of it.** The session was
run minutes ago by you, not over forty minutes by a nurse. So the line is *"I
have already run part of this interview — eleven of fifteen items are
resolved"*, not *"this visit is forty minutes in"*. The first is a fact about
the recording; the second invents a history. A judge who suspects one invented
detail re-reads everything else with suspicion, and what is really on screen is
strong enough not to need it.

## Before you press record

```bash
# Client against the deployed service. 8s chunks: the first coverage update
# lands ~28s in rather than ~40s. Processing is ~20s either way; you just wait
# less for it.
cd web && VITE_API_BASE=https://intake-agent-320877670799.us-central1.run.app \
  VITE_CHUNK_MS=8000 npm run dev
```

- [ ] Session pre-run to ~11 of 15 resolved, **M14 still open**.
- [ ] Access code already saved. Never film typing a secret.
- [ ] Tab 2: **Cloud Run → intake-agent → Logs**, loaded and streaming.
- [ ] Tab 3: **Firestore → `intake` → `sessions` → the live document**, loaded.
- [ ] Tab 4: `docs/diagrams/intake-architecture.html` and `intake-sequence.html`.
- [ ] Terminal: `cd eval`, command typed but **not run**.
- [ ] Mic tested. **One full rehearsal minimum** — live human speech through a
      real microphone is the one path never tested; only synthesised speech.
- [ ] Notifications off. Browser at ~125% so the ring and item list read at 1080p.

**The two phrasings are pre-tested against the deployed adjudicator and produce
the right verdict every time. Do not improvise them** — a wrong tick cannot be
edited out of an unedited take.

> *"Oh, I've had a couple of wobbles."* → M14 **partial**
>
> *"Three times since Christmas. The last one was in May, I slipped coming down
> the stairs."* → M14 **answered**

---

## Shot list — 4:00

### Act 1 · The friction (0:00–0:22) — *edited, tight*

| # | Time | On screen | Said |
|---|---|---|---|
| 1 | 0:00–0:14 | Title card, cut to the app at 11 of 15 | "A community nurse has ninety minutes and a form she is legally required to complete. She asks about falls. The answer is *'oh, I've had a couple of wobbles.'* Every AI scribe on the market ticks that item. It was mentioned. It was never answered." |
| 2 | 0:14–0:22 | The ring: 11 of 15 | "I've already run part of this interview. Everything from here is one continuous take, real time, no speed-ups." |

### Act 2 · The live window (0:22–2:47) — *unedited, one take, real time*

**Press record once at 0:22. Do not stop until the report is on screen.**
Everything in this act is the agent performing its task, which is exactly what
the Proof of Action criterion is asking to see.

| # | Time | On screen | Said / done |
|---|---|---|---|
| 3 | 0:22–0:33 | Click **Start recording**; red indicator | *"Have you had any falls in the last year?"* → *"Oh, I've had a couple of wobbles."* |
| 4 | 0:33–0:53 | **Cloud Run → Logs**, requests arriving | "While it works — this is Cloud Run, in my project, right now. Each chunk runs an ADK pipeline: transcribe, route the chunk to the items it's actually about, then one Vertex AI call per open item, in parallel." Hold the log lines legible 3s+. |
| 5 | 0:53–1:08 | Back. **M14 amber: MENTIONED** | "There. Not answered — *mentioned*. Still missing: the number of falls, and the circumstances of the most recent one. And it quotes what it heard." **Then stop talking for three seconds.** |
| 6 | 1:08–1:20 | Next-question card | "It's written the question to ask next — and only the question. For a high-risk item it drafts no answer at all. That's the output schema, not a prompt." |
| 7 | 1:20–1:32 | Ask it | *"How many times, and what happened the last one?"* → *"Three times since Christmas. The last one was in May, I slipped coming down the stairs."* |
| 8 | 1:32–1:52 | **Firestore → `sessions` → the live doc**, scrolled to `slots` | "State lives here — one document, one slot per required item. Not the transcript. That's why a three-hour interview costs the same per chunk as a ten-minute one." Watch `M14` flip in the console. |
| 9 | 1:52–2:06 | Back. **M14 green: ANSWERED**, **M15 appears** | "Now it counts. And answering it *opened a new required item* — injury from that fall — which wasn't on the form until there was a fall to ask about. Fourteen became fifteen." |
| 10 | 2:06–2:16 | **Finish & generate report** → gate modal | "She asks for the report. It refuses." |
| 11 | 2:16–2:31 | Hover the **disabled** decline, then click **Escalate** | "Three ways to close an item: ask now, record a formal decline — and the form itself decides which items may be declined — or escalate." |
| 12 | 2:31–2:47 | Follow-up drafted and routed → report appears | "The agent writes the follow-up itself and routes it. Occupational therapy queue. Nothing is ever left silently blank." **Stop recording here.** |

### Act 3 · Architecture (2:47–3:17) — *edited · explicitly scored*

| # | Time | On screen | Said |
|---|---|---|---|
| 13 | 2:47–3:02 | `intake-architecture.html` | "Two choices worth defending. The slot state is the state, not the transcript — context stays bounded, so length never degrades it. And adjudication is one isolated call per open item, fanned out: a wrong verdict on one item can't corrupt another, and every item is separately scoreable." |
| 14 | 3:02–3:17 | `intake-sequence.html`, the adjudicate row | "And the agent never authors domain content. Its output schema has no field an answer could go in — a rule enforced by a type, not by asking a model nicely." |

### Act 4 · Proof (3:17–3:47) — *edited, cut tight*

| # | Time | On screen | Said |
|---|---|---|---|
| 15 | 3:17–3:29 | **New session** → **Property damage · loss adjuster** | "Same engine, different profession. Escape of water, habitability, previous claims. No code changed — the vertical is a JSON template." |
| 16 | 3:29–3:47 | Terminal: run the eval. **Cut the 26s wait**; land on the matrix | "And it's measured. Forty-seven labelled cases, real Vertex calls. Forty-six of forty-seven — and a hundred percent precision on 'sufficient'. It has never ticked an answer a human labelled insufficient." |

### Act 5 · Close (3:47–4:00)

| # | Time | On screen | Said |
|---|---|---|---|
| 17 | 3:47–4:00 | Closing card, held still | "Every competitor ticks on mention. Intake ticks on answered." |

## The closing card

On screen as text — a judge can pause and read; they cannot pause your voice.

```
Intake — nothing leaves the room unanswered

  47 labelled adjudication cases · 46/47 · precision on "sufficient" 100%
  Behavioural eval over the agent pipeline · 5/5
  66 backend tests

  Gemini 3.6 Flash on Vertex AI · Google ADK 2.6.2 · Cloud Run · Firestore

  github.com/<user>/intake
```

**Every number must match the written submission exactly.** If the eval score
moves before you record, update both.

## If you run long

The live window is fixed — you cannot trim it without re-recording. So take the
time out of the edited acts, in this order:

1. Shot 15, the template swap (12s) — the repo shows it anyway.
2. Shot 14, the third architecture point (15s).
3. Shot 1, tighten the hook to a single sentence (5s).

Never cut shots 5, 9, 10 or 16 — the differentiator, the conditional item, the
refusal, and the evidence. If the live window itself overruns, the fix is a
cleaner re-take, not a cut.

## If something goes wrong mid-take

Unedited means restart the take, not patch it.

- **A chunk returns degraded.** Keep going and say so — "that chunk failed, and
  it recovers on the next one" is a good look for failure tolerance. Restart
  only if two in a row fail.
- **The adjudicator ticks the vague answer.** Restart. That is the one thing
  the video cannot show, and it is why the phrasings are pre-tested.

## Things a sharp judge may spot

Better known than discovered:

- **"Wobbles" also lands on M06, mobility.** Routing narrowed it from seven
  items to two, not one. Defensible — a wobble is unsteadiness — and both
  correctly stay *open*. Don't draw attention to it.
- **Coverage goes 14 → 15 required items** mid-interview. That's the
  conditional item. Shot 9 explains it, so it reads as a feature rather than a
  counting bug.
