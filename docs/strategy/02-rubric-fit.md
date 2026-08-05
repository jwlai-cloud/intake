# Intake — Rubric Fit Review

**Product:** Intake · *your second chair. Nothing leaves the room unanswered.*
**Track:** Collaborative Partner · **Scoring:** Innovation & Operational Utility 40% · Architectural Discipline & Tech Stack 30% · Demo & Production Readiness 30% · bonus up to 1.0 on a maximum of 6

Line-by-line against the verbatim criteria. Bands are my estimate of how a skeptical judge reads the current v3 plan, not a promise.

---

## Stage One — pass/fail

> *"whether the Submission includes all Submission requirements, reasonably addresses a Challenge, and reasonably applies the requirements."*

| Requirement | Status |
|---|---|
| One category selected | Collaborative Partner ✓ |
| URL to hosted Project ("highly encouraged") | **Web app satisfies this trivially** — a genuine advantage of the v3 cut |
| Text description: features, technologies, other data sources, findings and learnings | Four sections, scheduled 24–28 Aug ✓ |
| Public code repository URL | ✓ — go public, the criterion text says "public" |
| Spin-up instructions in README | ✓ Weekend 3 |
| Architecture diagram | ✓ Weekend 3 |
| Demo video ≤4 min, public on YouTube/Vimeo, English | ✓ |
| Backend demonstrably running on Google Cloud, shown in video | ✓ Vertex AI logs + Cloud Run dashboard |
| New Projects Only, pre-existing code disclosed | ✓ repo initialised 5 Aug, nothing predates 3 Aug |
| Gemini 3.5+ / Google agent framework / Google Cloud infra service | `gemini-3.6-flash` via Vertex · ADK Python · Cloud Run **and** Firestore ✓ |
| *"capable of being successfully installed and run consistently on the platform for which it is intended"* | **Non-issue for a web app.** Would have been a real risk with an unpublished iOS build |

**Verdict: clean pass, and the web-first decision quietly de-risked two of these.**

---

## Criterion 1 — Innovation & Operational Utility (40%)

> *"Does the system eliminate real-world friction? Is the 'Twist' present? We are looking for **high-value, autonomous execution over simple chat queries**."*

**"Eliminates real-world friction" — strong.** A named practitioner, a real mandated form, a quantified cost. WellSky's own published figure is ~30 minutes saved per start-of-care visit, and a field discovered blank back at the office costs a phone call, a guess, or a second visit. This is the best part of the submission and it needs no work.

**"Is the Twist present" — strong, but only if you name it.** The rules use that exact word, so use it back. One caveat: don't describe the Twist as "it refuses." See below.

**"Autonomous execution" — this is the real gap, and it sits in the heaviest criterion.** Intake as currently designed never acts. It watches, tracks, suggests, and blocks. A judge reading that clause will score a careful assistant, not autonomous execution, and nothing in the plan currently argues otherwise.

### The fix — and it's the same gate with a better exit

Right now the gate has one outcome: no. That's both a rubric weakness *and* the answer to my earlier grill attack (Inspect Point deliberately declined to gate — "technicians still control the report output" — which suggests practitioners may reject being blocked by their own tool).

Change the gate so every required item resolves into exactly one of three states, never blank:

1. **Answered** — with the transcript span as evidence
2. **Formally declined** — with a recorded reason
3. **Escalated** — the agent autonomously drafts and files a follow-up action: what's outstanding, why it couldn't be closed, and where it needs to go

State three is genuine autonomous execution. Unprompted, the agent judges that an item cannot be closed in this session, generates a structured follow-up, and files it — a multi-step chain from a single trigger, with a real artifact at the end. And it's cheap: one more field in the structured output, one Firestore write, one section in the report.

**Restate the Twist accordingly.** Not "it refuses to produce the report" but:

> **Nothing is ever silently blank.** Every mandatory item leaves the session answered with evidence, formally declined with a reason, or escalated as a filed follow-up. The agent decides which — and acts on it.

That version is stronger on all three sub-clauses at once: it's the Twist, it's autonomous execution, and it defuses the "practitioners will hate a blocker" objection because the gate is a router, not a wall. It also improves the demo — the gate beat now has three visible outcomes instead of one refusal.

**This is the only feature I'd add back after the v3 cuts.** If it doesn't fit, cut the report's by-section formatting before you cut this.

**Band: likely 4 now → 5 with the three-state gate.**

---

## Criterion 2 — Architectural Discipline & Tech Stack (30%)

> *"We are evaluating your engineering decisions, not just your ability to call an API. How well did your team decouple systems, manage state, and design robust, failure-tolerant agentic systems?"*

**Decoupling — strong, and provable.** Zero domain logic in code; the entire vertical lives in a config artifact. The loss-adjusting template is the proof, and it's on camera. Nothing more needed.

**State management — strong, but say the quiet part.** You are deliberately *not* using ADK's default session storage, because it's in-memory and dies on Cloud Run instance recycle. That is precisely "engineering decisions, not just calling an API" — so write it up as a named decision with the reasoning, not as an implementation detail. One ADR, three sentences.

**Context-window efficiency — you have a strong story here and you haven't been telling it.** This matters because the judges' own materials hint at it, and because a judge might otherwise read your chunked architecture as "they couldn't manage real streaming."

The naive design accumulates the transcript in context and re-asks the model about completeness each turn. A 45-minute interview becomes tens of thousands of growing tokens — expensive, and degrading as it grows. Intake instead carries the **slot state** as the state, not the transcript: each call gets the open items from the template, a fixed-size struct of current slot values, and the new 15–20 seconds of audio. Context is bounded and roughly constant regardless of interview length, so a three-hour session costs the same per chunk as a ten-minute one and never degrades.

**Chunking is not a shortcut, it's the correct state model.** Frame it that way, because it's true and because it converts a perceived compromise into a design argument.

**Tool scoping — one free line.** Adjudication is scoped to a single item at a time, so a wrong call on item 14 cannot corrupt item 3. Worth a sentence on the diagram.

**Failure tolerance — still the weak spot.** The criterion names it explicitly and you have one line about offline persistence. Two hours in Weekend 3 buys: chunk POST retry with a local queue; malformed-structured-output retry with a stricter reprompt; and network-drop reconciliation on reconnect. Then draw all three on the architecture diagram as **named failure modes**. Home visits lose signal as the normal case, not the edge case, so this is also honest product work rather than rubric theatre.

**Band: likely 4 now → 5 with the failure-tolerance pass and the context-efficiency story written down.**

---

## Criterion 3 — Demo & Production Readiness (30%)

> *"The clarity of the technical documentation and the undeniable proof of execution in the video pitch. Does the 4-minute video clearly define the friction being solved **and explain the architecture**?"*
> *"**The Proof of Action:** Does the video show an unedited, live execution of the agent performing its task (via terminal logs, **database updates**, or UI changes)?"*
> *"**The Documentation:** Does the public GitHub repository feature a clean architecture diagram and reproducible setup instructions? Is there visual proof of Google Cloud deployment in the video?"*

**Two specific things to change in the demo plan.**

First, **"database updates" is named in the criterion's own words.** Your current plan shows UI changes only. Put the Firestore console in a split view during the unedited take so documents are visibly updating as slots fill. It costs nothing, and it hits the clause literally rather than by interpretation.

Second, **the video must explain the architecture, not just show a diagram at the end.** Fifteen seconds of static diagram is thin against a criterion that asks the question directly. Budget about thirty seconds of actual narration over the diagram — the config-driven decoupling, the bounded-state design, the named failure modes. Take it out of the setup section, not the unedited take.

**Documentation** — the README is explicitly scored. A web-only stack (React + Cloud Run + Firestore + Vertex) is a much shorter reproducible-setup document than the iOS variant would have been. Another quiet win from the v3 cut.

**Band: likely 4 → 5 with the Firestore split view and thirty seconds of architecture narration.**

---

## Track fit — Collaborative Partner

> *"Build an agent that **leads the way and takes notes**. It should ask clarifying questions, guide the user step-by-step, and have a clear way to capture feedback, so it constantly adapts to the user's unique way of thinking."*

Near enough a spec. Quote it in the write-up and let the judge connect it.

| Requirement | Where it lands |
|---|---|
| Leads the way and takes notes | The literal product |
| Asks clarifying questions | Next-question generation against open items |
| Guides step-by-step | Conditional branching — required-ness changes as answers land |
| Clear way to capture feedback | Tap-to-confirm highlights: labelled signals collected as a side effect of real work, no thumbs-up widget |
| Adapts to the user | Practitioner style profile — dismissed categories stop being proposed |

**One risk from the v3 cuts.** The Resources page says judging is built around *"stateful, multi-turn dialogue with real-time context retrieval (RAG) and persistent memory."* I earlier said the guidance-corpus retrieval was droppable — **reverse that.** Drop it and you have no RAG story at all, on a track that names RAG explicitly.

Keep it, and keep it cheap: embed the form's guidance-note chunks and retrieve top-k for the current item plus the candidate answer, using **Firestore vector search** so retrieval and state share one datastore. That's a tight architecture story, it hits the "schema and vector-embedding design" hint, and it's a couple of hours. *(Verify Firestore vector search is GA before committing — if not, a small in-memory index over one document is fine and still genuine retrieval.)*

Note the retrieval also does real work rather than decorating the rubric: the guidance notes are what let the adjudicator judge *sufficiency*, which is your whole differentiator. Without them you're judging answers against a field label.

---

## Bonus — up to 1.0 on a maximum of 6

Roughly a sixth of the ceiling, and the cheapest points available.

| Item | Points | Status |
|---|---|---|
| Public content piece, with language stating it was made for this hackathon | 0.2 | Write up the bounded-state decision or the three-state gate — both genuinely interesting |
| Social post tagged **#AllThingsAgenticHackathon** | 0.2 | Ten minutes |
| Each additional Google AI model, max 0.6 | 0.2–0.6 | One is realistic: a Gemma model doing a small local classification step, or MedASR on the audio path. Veo and Lyria have no honest use here — skip them |

Target 0.6. It's four hours of work for a sixth of the scale.

---

## Summary — the five changes

1. **Three-state gate** — answered with evidence, formally declined with reason, or autonomously escalated as a filed follow-up. Fixes the "autonomous execution" clause in the 40% criterion and defuses the objection that practitioners hate blockers. The only feature added back after the v3 cuts.
2. **Restate the Twist** as *"nothing is ever silently blank"* rather than *"it refuses."*
3. **Failure-tolerance pass**, two hours, three named failure modes drawn on the diagram.
4. **Keep the guidance-corpus retrieval** — it's the RAG story the track asks for by name, and it's what makes sufficiency judgement possible at all.
5. **Demo: Firestore console in split view** during the unedited take, and thirty seconds of architecture narration.

Everything else in v3 stands. Nothing here changes the schedule shape — items 1, 3 and 5 are hours, not days, and item 4 was already half-planned.
