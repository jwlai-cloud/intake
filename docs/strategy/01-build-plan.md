# Second Chair — Plan v3 (cut down)

Supersedes the scope in the earlier specs. Architecture, config schema, guardrails and competitive positioning from `second-chair-build-spec.md` and `second-chair-edge-and-dual-track.md` still stand — this replaces the build plan and the platform decisions.

## Locked

| | |
|---|---|
| Platform | **Web only** for the 31 Aug deadline. Plain React, `MediaRecorder` for mic. No cross-platform framework. |
| iOS | **Deferred to September**, for Shipaton. Decide the path then — Capacitor wrapping this React app is likely cheaper than a separate React Native build (verify RevenueCat's Capacitor support when you get there). |
| Demo vertical | **Nurse-facing**, unchanged. Generalisation was always about the engine and the store listing, not the demo. |
| Drive export | **Cut.** Share sheet / `mailto:` only. Drive goes in "What's next". |
| Second template | **Kept** — it's the architecture proof and it's cheap if the engine is honest. |
| Recording | Screen capture + mic. One phone shot of the laptop on a table to establish the in-person setting. |

Cutting the mobile build and Drive export removes both things I flagged as uncut scope creep. This is now a plan with slack in it.

## Build order — the adjudicator comes first

The one thing that must be true for this project to have a headline: the model can tell a substantive answer from a vague one. Everything else is plumbing. So it gets built and measured before any UI exists.

**Weekend 1 (8–9 Aug) — the adjudicator, nothing else.**
Get her real form. Encode a handful of items as config. Write ~30 labelled examples: for each required item, several answers that should count and several that shouldn't. Then build the single Gemini call — audio or transcript in, `{transcript, slots_filled, next_question, candidate_flags}` out — and **measure it against the 30**. Target: it never ticks an answer you labelled insufficient. If it can't reliably separate *"a couple of wobbles"* from *"three falls, the last in May on the stairs"*, you need a different headline, and you want to know that on 9 August.

Deliverable: a script, a JSON output you trust, and a number.

**Evenings 10–14 Aug.** Cloud Run + ADK wrapper around the adjudicator. Firestore session schema. Conditional branching (`depends_on`). Guidance-corpus retrieval if it's cheap; drop it if it isn't — the practitioner memory below matters more for the rubric.

**Weekend 2 (15–16 Aug).** React front end. Mic → 15–20s chunks → POST. Firestore listener → live coverage ring, next-question card, tap-to-confirm highlight chips. Visible recording indicator and session timer.

**Evenings 17–21 Aug.** The completeness gate, with declined-with-reason. Report generation, in-browser edit, email/share. Practitioner style profile (dismissed highlight categories stop being proposed) — this is the track's persistent-memory requirement, don't skip it.

**Weekend 3 (22–23 Aug).** Loss-adjusting template as a second config — if this needs code changes, fix the engine. Failure-tolerance pass (below). Architecture diagram. README spin-up instructions.

**Evenings 24–28 Aug.** Pre-test the scripted vague answers. Rehearse. Record. Write the four required sections. Content piece + social post for the 0.4 bonus.

**29–30 Aug.** Final cut, upload, **submit 30 Aug**. Freeze until ~8 Oct.

## Two rubric gaps to close deliberately

**The 40% criterion says "high-value, autonomous execution over simple chat queries."** Second Chair is deliberately non-autonomous, which is a mismatch you have to argue past rather than ignore. Frame it in these words: the gate is an **autonomous judgement** — the agent decides, unprompted and against an external standard, that the work isn't finished and says so — and report generation plus delivery is an **executed action chain**, not a suggestion. Say it explicitly in the write-up. Don't let a judge infer it.

**The 30% architecture criterion asks for "robust, failure-tolerant" systems.** Currently you have one line about offline persistence. Spend two hours in Weekend 3 on: chunk POST retry with local queue; malformed-JSON retry with a stricter reprompt; and graceful degradation when the network drops mid-session (queue chunks locally, reconcile on reconnect). Then put those three paths on the architecture diagram as named failure modes. This is cheap and it's explicitly scored — most submissions won't have it.

## Demo notes

Don't shrink the form to fit the video. Load the **real** form, open with coverage already partway complete, and run the unedited segment across the last few items. A short form makes the gate look trivial; a big form with a short live window keeps the stake and fits the runtime.

The unedited segment, roughly 75 seconds, needs to contain: a required item surfacing while the conversation is still running, the vague answer being **refused**, the proper answer being accepted with its transcript quote, a highlight confirmed, and the gate blocking then clearing. Everything outside that can be cut or labelled-fast-forwarded.

The vague-answer refusal is the most valuable fifteen seconds in the video — it's what visibly beats Otter Live Assist, Balto and Microsoft Facilitator, all of which tick on mention rather than on answer. Pre-test the exact wording.

Mandatory: Cloud Run dashboard or Vertex AI logs on screen before you switch anything off.

## Deferred to September (Shipaton)

iOS build and platform choice · RevenueCat paywall · App Store listing positioned generically, not as healthcare (guideline 5.1.1(ix)) · Drive export · offline capture with deferred sync.

One repo throughout. Tag `ata-submission-2026-08-31` at the deadline and point the Devpost entry at the tag, not `main`, so you can keep building in September without touching the frozen submission.

## Today

Register on Devpost. Request the $150 credits — write "Collaborative Partner" exactly, 72-hour review. Initialise the repo. Ask her for the form and its guidance notes.
