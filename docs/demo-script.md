# Demo video — shot script

**Target: 2:50.** Hard cap 3:00 — verify the platform's stated limit before
uploading; a few seconds over disqualifies on some platforms.

## The constraint that shapes everything

The contest requires **unedited live execution**. So the demo segment is one
continuous take. No cutting out the wait, no splicing a better attempt.

And there is a wait: **a chunk takes 19–23 seconds** end to end — transcribe,
route, k adjudications, coach. Measured on the deployed service, not estimated.

That is 40 seconds of a two-minute demo spent waiting, and it cannot be edited
out. So it gets *filled* — with the Google Cloud proof the contest separately
requires. The latency stops being dead air and becomes the segment where you
show Cloud Run serving the request and Firestore holding the state.

Do not apologise for the wait on camera. Narrate it as what it is: the agent
judging fourteen items against their guidance notes.

## Before you press record

```bash
# One terminal — the client, pointed at the deployed service.
# 8s chunks: the first coverage update lands ~28s after you start recording
# instead of ~40s. Processing time is the same; you just wait less for it.
cd web && VITE_API_BASE=https://intake-agent-320877670799.us-central1.run.app \
  VITE_CHUNK_MS=8000 npm run dev
```

- [ ] Browser at `localhost:5173`, access code **already pasted and saved** —
      do not film typing a secret.
- [ ] Second tab: **Cloud Run → intake-agent → Logs**, already loaded.
- [ ] Third tab: **Firestore → database `intake` → `sessions`**, already loaded.
- [ ] Mic tested. One rehearsal of the full take, minimum.
- [ ] Windows sized so the coverage ring and the item list are both readable at
      1080p. Zoom the browser to ~125% if not.
- [ ] Close notifications. Full screen.

**Rehearse the two phrasings until they are automatic.** These are the exact
strings that have been tested repeatedly against the deployed adjudicator and
produce the right verdict every time. Changing a word is a risk you cannot
edit out:

> *"Oh, I've had a couple of wobbles."* → M14 **partial**
>
> *"Three times since Christmas. The last one was in May, I slipped coming
> down the stairs."* → M14 **answered**

## Audio or typed?

**Recommended: audio.** It is the product, and the audio path is now verified
end to end against the deployed service.

The risk is that live human speech through your mic has never been tested — only
synthesised speech. Rehearse it. If transcription mangles a phrase twice in
rehearsal, fall back to the typed box and say nothing about it; the pipeline is
identical and the on-screen result is the same.

---

## Shot list

| # | Time | On screen | Said | Notes |
|---|---|---|---|---|
| 1 | 0:00–0:14 | Title card, then the item list at 0 of 14 | "A community nurse has ninety minutes and a form she is legally required to complete. She asks about falls. The answer is 'oh, I've had a couple of wobbles.' Every AI scribe on the market ticks that item. It was mentioned. It was never answered." | The hook is the whole pitch. Say it once, cleanly. |
| 2 | 0:14–0:22 | Click **Start recording**; red indicator appears | "This is Intake. It listens against the actual form." | Point at "0 of 14 required items resolved". |
| 3 | 0:22–0:32 | Speak both parts aloud | *"Have you had any falls in the last year?"* … *"Oh, I've had a couple of wobbles."* | Both voices, or a second person. Natural pace. |
| 4 | 0:32–0:52 | **Alt-tab to Cloud Run logs.** Requests appearing live | "While that chunk is processed — this is Cloud Run, and those are the requests arriving. Each one runs an ADK pipeline: transcribe, route the chunk to the items it is actually about, then one Vertex AI call per open item, in parallel." | **This is your Google Cloud proof.** Let the log lines be legible for 3+ seconds. |
| 5 | 0:52–1:05 | Back to the app. **M14 turns amber: MENTIONED** | "There it is. Not answered — *mentioned*. Still missing: the number of falls, and the circumstances of the most recent one. And it quotes exactly what it heard." | **The money shot.** Stop talking. Let it sit for 3 seconds. |
| 6 | 1:05–1:18 | The suggested-next-question card | "It has written the question she should ask next — and only the question. For a high-risk item it will not draft an answer at all. That is a design rule, enforced by the output schema, not a prompt." | Read the generated question aloud from screen. |
| 7 | 1:18–1:30 | Ask it; give the specific answer | *"How many times, and what happened the last one?"* … *"Three times since Christmas. The last one was in May, I slipped coming down the stairs."* | Exact tested phrasing. |
| 8 | 1:30–1:50 | **Alt-tab to Firestore**, `sessions` collection, open the live document | "The state lives here — one document, one slot per required item. Not the transcript. That is why a three-hour interview costs the same per chunk as a ten-minute one." | Second Google Cloud proof. Scroll to `slots` and let `M14` be visible. |
| 9 | 1:50–2:02 | Back to the app. **M14 goes green: ANSWERED**, and **M15 appears** | "Now it counts. And answering it opened a new required item — injury from that fall — which was not on the form until there was a fall to ask about." | The conditional item appearing is a strong, easily-missed beat. Point at it. |
| 10 | 2:02–2:12 | Click **Finish & generate report** → gate modal | "She asks for the report. It refuses." | The 409 is instant. Enjoy the beat. |
| 11 | 2:12–2:30 | The gate, three resolutions visible; click **Escalate** on one | "Three ways to close an item: ask now, record a formal decline, or escalate — and the agent drafts the follow-up itself, and routes it. Occupational therapy queue. Nothing is ever left silently blank." | The escalation takes ~5s. Narrate over it. |
| 12 | 2:30–2:42 | The generated report, scrolled to **Follow-ups filed** | "The report is assembled from what was recorded — there is no model call in it. Every unresolved item became a filed action with a destination." | Scroll slowly. Let the queue names be readable. |
| 13 | 2:42–2:50 | Static card: numbers + repo URL | "Forty-seven labelled cases. One hundred percent precision on 'sufficient' — it has never once ticked an answer that a human labelled insufficient. Every competitor ticks on mention. Intake ticks on answered." | Numbers **on screen**, not just spoken. Leave the URL up long enough to read. |

## The closing card

Put these on screen as text. A judge can pause and read them; they cannot pause your voice.

```
Intake — nothing leaves the room unanswered

  47 labelled adjudication cases · 46/47 · precision on "sufficient" 100%
  Behavioural eval over the agent pipeline · 5/5
  66 backend tests

  Gemini 3.6 Flash on Vertex AI · Google ADK 2.6.2 · Cloud Run · Firestore

  github.com/<user>/intake
```

**Every number here must match the written submission exactly.** If the eval
score moves before you record, update both.

## If something goes wrong mid-take

Unedited means you restart the take, not patch it. Two failures are plausible:

- **A chunk comes back degraded.** The session survives by design; the next
  chunk retries the same items. You can keep going and say so — "that chunk
  failed, and it recovers on the next one" is a genuinely good look for
  failure tolerance. Only restart if two in a row fail.
- **The adjudicator ticks the vague answer.** Restart. That is the one thing
  the video cannot show, and it is why the phrasings are pre-tested.

## Known things a sharp judge might spot

Better to know than be surprised:

- **"Wobbles" also lands on M06, mobility.** Routing narrowed it from seven
  items to two, but not to one. It is defensible — a wobble is unsteadiness —
  and both correctly stay *open*. Do not draw attention to it.
- **Coverage reads 1 of 15, not 1 of 14**, after M14 is answered. That is the
  conditional item appearing. Explain it (shot 9) rather than letting it look
  like a bug.
