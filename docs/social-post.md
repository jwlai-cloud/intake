# Social post drafts

Both must be **public**, not unlisted. The blog must state it was created for
this hackathon — `docs/blog-post.md` says so in its subtitle. Fill in the two
links before posting.

---

## LinkedIn

> A community nurse asks: "any falls in the last year?"
>
> The answer is "oh, I've had a couple of wobbles."
>
> Every AI scribe on the market ticks that box. It was mentioned. It was never
> answered. She finds the gap that evening, at her desk, and now she needs a
> phone call, a guess, or a second visit.
>
> I spent August building the thing that doesn't tick it.
>
> **Intake** listens to a structured interview and adjudicates, per required
> item, whether it actually received a substantive answer — not whether the
> topic came up. It surfaces the gaps while the interview is still running,
> and it refuses to produce a report until every mandatory item resolves into
> one of three states: answered, formally declined, or escalated with a
> follow-up the agent drafts and routes itself.
>
> Three things I'd defend:
>
> • **The eval came before the UI.** 47 labelled cases that exit non-zero if a
> single answer a human called insufficient gets ticked. 100% precision on
> that class. The twelve adversarial cases found a real bug in the first hour.
>
> • **The slot state is the state, not the transcript.** A three-hour
> interview costs the same per chunk as a ten-minute one.
>
> • **The agent never authors domain content** — and that's enforced by the
> output schema having no field an answer could go into, not by asking it
> nicely in a prompt.
>
> Built on Google ADK 2.6.2, Gemini 3.6 Flash on Vertex AI, Cloud Run and
> Firestore.
>
> Write-up: [LINK]
> Code: [REPO]
>
> #AllThingsAgenticHackathon

---

## X

> Every AI meeting assistant ticks a checklist item when it's *mentioned*.
>
> Ask a nurse's patient about falls and get "oh, I've had a couple of
> wobbles" — that ticks. It was never answered.
>
> Built an agent that adjudicates the difference, and won't emit a report
> until every mandatory item is answered, declined, or escalated.
>
> Eval before UI: 47 labelled cases, exits non-zero if it ever ticks an
> answer a human called insufficient. 100% precision there.
>
> ADK 2.6.2 · Gemini 3.6 Flash on Vertex · Cloud Run · Firestore
>
> [LINK]
>
> #AllThingsAgenticHackathon
