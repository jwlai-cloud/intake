# Demo video — shot script

**Limit: 4:00** (`docs/strategy/02-rubric-fit.md` — "Demo video ≤4 min, public
on YouTube/Vimeo, English"). **Target 3:50.** Re-check the rules page before
uploading; over a hard limit disqualifies on some platforms.

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

## The pacing problem, and the honest fix

A chunk takes **19–23 seconds** end to end. Measured on the deployed service.
Two answer beats therefore cost ~40s of waiting that cannot be edited away.

`01-build-plan.md:47` already had the answer: **don't shrink the form to fit
the video.** Load the real 15-item form, open with coverage already partway
complete, and run the unedited window across the last few items. A short form
makes the gate look trivial; a full form with a short live window keeps the
stake and fits the runtime.

So: run a session up to ~11 of 15 *before* recording, then start the take.
Say so on camera — "we're forty minutes into this visit". An unlabelled jump
reads as concealment; a labelled one reads as considerate.

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

## Shot list — 3:50

### Act 1 · The friction (0:00–0:25)

| # | Time | On screen | Said |
|---|---|---|---|
| 1 | 0:00–0:16 | Title card, then the app at 11 of 15 | "A community nurse has ninety minutes and a form she is legally required to complete. She asks about falls. The answer is *'oh, I've had a couple of wobbles.'* Every AI scribe on the market ticks that item. It was mentioned. It was never answered. She finds the gap that evening, at her desk, with the door shut." |
| 2 | 0:16–0:25 | Point at the ring: 11 of 15 | "This visit is forty minutes in. Eleven of fifteen required items are resolved. Everything from here is live and uncut." |

### Act 2 · Unedited live execution (0:25–2:15)

Say "live and uncut" once, then never break the take until 2:15.

| # | Time | On screen | Said / done |
|---|---|---|---|
| 3 | 0:25–0:36 | Click **Start recording**; red indicator | Ask aloud: *"Have you had any falls in the last year?"* → *"Oh, I've had a couple of wobbles."* |
| 4 | 0:36–0:56 | **Alt-tab: Cloud Run logs**, requests arriving live | "While it works — this is Cloud Run. Each chunk runs an ADK pipeline: transcribe, route the chunk to the items it's actually about, then one Vertex AI call per open item, in parallel." Let log lines sit legible for 3s+. |
| 5 | 0:56–1:10 | Back. **M14 amber: MENTIONED** | "There. Not answered — *mentioned*. Still missing: the number of falls, and the circumstances of the most recent one. And it quotes what it heard." **Stop talking for 3 seconds.** |
| 6 | 1:10–1:22 | Next-question card | "It's written the question to ask next — and only the question. For a high-risk item it drafts no answer at all. That's the output schema, not a prompt instruction." |
| 7 | 1:22–1:34 | Ask it | *"How many times, and what happened the last one?"* → *"Three times since Christmas. The last one was in May, I slipped coming down the stairs."* |
| 8 | 1:34–1:52 | **Alt-tab: Firestore**, the live document, scrolled to `slots` | "The state lives here — one document, one slot per required item. Not the transcript. That's why a three-hour interview costs the same per chunk as a ten-minute one." Watch `M14` flip in the console. |
| 9 | 1:52–2:04 | Back. **M14 green: ANSWERED**, **M15 appears** | "Now it counts. And answering it *opened a new required item* — injury from that fall — which wasn't on the form until there was a fall to ask about. Fourteen items became fifteen." |
| 10 | 2:04–2:15 | **Finish & generate report** → gate | "She asks for the report. It refuses." (409 is instant — let it land.) |

### Act 3 · The gate (2:15–2:40)

| # | Time | On screen | Said / done |
|---|---|---|---|
| 11 | 2:15–2:28 | Gate modal. Hover the **disabled** decline on a mandatory item, then click **Escalate** | "Three ways to close an item: ask now, record a formal decline — and note the form decides which items may be declined at all — or escalate." |
| 12 | 2:28–2:40 | Follow-up appears, routed | "The agent drafts the follow-up itself and routes it. Occupational therapy queue. Nothing is ever left silently blank." |

### Act 4 · Architecture, explained (2:40–3:10) — *scored explicitly*

| # | Time | On screen | Said |
|---|---|---|---|
| 13 | 2:40–2:56 | `intake-architecture.html`, then the sequence diagram | "Three technical choices. One: the slot state is the state, not the transcript — context is bounded, so length doesn't degrade it. Two: adjudication is one isolated call per open item, fanned out — a wrong verdict on one item can't corrupt another, and each item is separately scoreable." |
| 14 | 2:56–3:10 | Sequence diagram, the adjudicate row | "Three: the agent never authors domain content. Its output schema has no field an answer could go in. That's a rule enforced by a type, not by asking a model nicely." |

### Act 5 · Proof (3:10–3:50)

| # | Time | On screen | Said / done |
|---|---|---|---|
| 15 | 3:10–3:24 | Click **New session** → pick **Property damage · loss adjuster** | "Same engine, different profession. Loss adjusting — escape of water, habitability, previous claims. No code changed; the vertical is a JSON template." |
| 16 | 3:24–3:44 | Terminal: `uv run python run_eval.py` — runs in **26s**, prints the matrix | "And it's measured, not asserted. Forty-seven labelled cases, real calls to Vertex, running now. Forty-six of forty-seven — and a hundred percent precision on 'sufficient'. It has never ticked an answer a human labelled insufficient." |
| 17 | 3:44–3:50 | Closing card | "Every competitor ticks on mention. Intake ticks on answered." |

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

## If you need to cut

In order, least damage first:

1. Shot 15, the template swap (14s) — the repo shows it.
2. Shot 6, the next-question card (12s) — visible anyway in shot 5.
3. Shot 14, the third architecture point (14s) — **last resort**; architecture
   is explicitly scored.

Never cut shots 5, 9, 10 or 16. They are the differentiator, the conditional
item, the refusal, and the evidence.

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
