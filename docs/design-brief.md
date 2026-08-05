# Design brief — Intake interview screen

Paste the block below into your design tool (Claude, Pencil, or a fresh Claude
Code session). It's self-contained.

---

## The prompt

Design the primary screen for a web app called **Intake**, tagline *"your second chair — nothing leaves the room unanswered."*

**What the product does.** A professional runs a structured interview against a mandated form — a community nurse doing a home care assessment, an insurance loss adjuster inspecting water damage. The app listens to the conversation through the laptop mic and tracks which required form items have received a **substantive answer**. It surfaces the remaining gaps *while the interview is still happening and the other person can still answer*, then refuses to produce the report until every mandatory item is resolved.

**The physical context, which drives everything.** The laptop is open on someone's kitchen table. The practitioner is talking to a real human being, making eye contact, occasionally writing. She glances at the screen for one or two seconds at a time, from about 60cm away, at an angle. The person being interviewed may be able to see the screen. She is not reading it — she is checking it.

So: large type, high contrast, very few things on screen, and state changes obvious in peripheral vision. Nothing that requires focused reading. Nothing that would be embarrassing or alarming if the interviewee glanced over.

**The one design idea that matters most.** Every competing product ticks a form item when the topic is *mentioned*. Intake ticks only when the item is genuinely *answered*. So the interface needs three visibly distinct states, not two:

- **Open** — not raised yet
- **Mentioned, not answered** — the topic came up but the answer was insufficient. This state must look clearly different from both of the others, and it must say what is still missing in plain words: *"count given — circumstances missing."*
- **Answered** — resolved, showing the exact quote from the conversation it was drawn from, as evidence

That middle state is the product's entire differentiator. Make it the most legible thing on the screen.

**Screens and states to design.**

1. **Live interview view** (the main one). Needs: which template is loaded; elapsed session time; an unmissable recording indicator; a progress reading of required items resolved out of total; the list of still-unresolved required items with their state and what's missing; a single prominent suggested next question; and proposed "highlights" the practitioner taps once to confirm or dismiss. Plus a way to finish and generate the report.

2. **The gate.** When she tries to finish with items unresolved, she is not simply blocked. Every outstanding item offers exactly three resolutions, and the design should make all three feel equally legitimate:
   - **Ask now** — return to the interview with that item pinned
   - **Record as declined** — with a reason
   - **Escalate** — the agent drafts and files a follow-up action for what couldn't be closed
   
   The tone here is a colleague handing you a checklist, not a system denying you.

3. **High-risk item.** Some items are flagged so the app deliberately offers *no* suggested answer — it shows only the relevant quote from the conversation and requires the human to write the answer herself. Design that restraint so it reads as care rather than as a missing feature.

4. **Report view.** Generated sections, editable inline, with a flags section and a follow-ups section.

**Hard constraints.**

- **No chat interface.** This is not a chatbot. No message bubbles, no assistant avatar, no typing indicator, no conversational thread. The agent speaks through state changes and one card at a time.
- **The app never talks.** No audio output — the practitioner is in someone's living room. Everything is visual.
- **No identity anywhere.** The app stores nothing about who is being interviewed. There is no name field, no photo, no client record, no case header with a person in it. Sessions belong to a job, not a person.
- **Language stays administrative, never advisory.** *"Item 14 — no recorded answer"* is correct. *"This may indicate falls risk"* is forbidden. No recommending, ranking, or implying a professional next action, anywhere in the copy, including button labels.
- **It has to survive being screen-recorded.** This UI appears in a 4-minute demo video watched at 1080p, possibly in a small window. No thin grey-on-grey text, no 12px labels, no state changes conveyed by subtle colour shifts alone. If a change matters, it should be visible at a glance in a compressed video.

**Deliverable.** A single self-contained HTML file — inline CSS and JS, no build step, no external dependencies, no browser storage. Include small controls so I can click through each state to review it: empty session, mid-interview, an item in "mentioned not answered", a high-risk item, the gate open with two items outstanding, and the finished report.

Use realistic placeholder content from a community nursing assessment — mobility, falls, medication, home environment — and make the falls item the one sitting in "mentioned, not answered", with the missing pieces spelled out. Keep the visual language calm and professional: this is a tool used in someone's home, in a regulated job, by someone who is already busy.

---

## Why these constraints (context, not part of the prompt)

- The glanceability and screen-recording constraints come from the demo: 30% of the score is Demo & Production Readiness, judged on a 4-minute video showing unedited live execution.
- The three-state item design is what visibly beats Otter Live Assist, Balto and Microsoft Teams' Facilitator, all of which mark an item when the topic is merely raised. See `docs/strategy/03-competitive-audit-and-shipaton.md`.
- The three-resolution gate is ADR-0005. It exists both to answer the "practitioners will resent being blocked" objection and to satisfy the contest's "autonomous execution" criterion via the escalation path.
- The no-identity rule is ADR-0007; the administrative-language rule is ADR-0006. Both are load-bearing, not stylistic.
