# Progress log

Update this at the **end of every session** — not just at milestones. Newest
entry at the top.

---

## 2026-08-05 — repo scaffolded

**Done**

- Repo initialised. Docs, seven ADRs (0001–0007) recording every decision made
  during planning, eval harness skeleton, gitignore protecting private material.
- Strategy material archived under `docs/strategy/` — competitive audit, rubric
  fit analysis, cut-down build plan.

**Next, in priority order**

1. **Obtain the real assessment form and its guidance notes.** Then derive a
   *synthetic* version from published standards for the repo and the demo — the
   real form is likely employer-confidential and both repo and video are public.
2. **Build the adjudicator and its eval harness. Nothing else.** ~30 labelled
   cases in `eval/cases/`: for each required item, answers that should count and
   answers that shouldn't. The bar is that it never marks an insufficient answer
   sufficient. If it can't separate *"a couple of wobbles"* from *"three falls,
   the last in May on the stairs"*, stop and escalate — the project needs a
   different headline.
3. Encode the synthetic template per ADR-0003 and check `depends_on` branching.
4. ADK agent on Cloud Run wrapping the adjudicator; Firestore session schema.
5. React front end: mic → chunks → POST; Firestore listener → live UI.
6. Three-state gate (ADR-0005), report generation, share.
7. Loss-adjusting template — the decoupling test.
8. Failure tolerance: chunk retry with local queue, malformed-output reprompt,
   network-drop reconciliation. Draw all three on the architecture diagram as
   named failure modes.

**Admin, not code, and time-sensitive**

- Register on Devpost.
- Request the $150 Google Cloud credits. Write "Collaborative Partner"
  exactly — requests naming a non-existent track are auto-declined. Review
  takes up to 72 business hours and the form closes 28 Aug.
- Push the repo public (`gh repo create --public --source=. --push`).

**Open questions**

- Is Firestore vector search GA? If not, a small in-memory index over the single
  guidance document is fine and still genuine retrieval.
- Does MedASR count as an "additional Google AI model" for the 0.2 bonus? A
  plain Gemma model doing a small classification step is the safe fallback.
- BrightHire's live interview guide: does it dynamically detect which questions
  were asked and answered, or just display a static list? Marketing pages are
  ambiguous. It is the one competitor that might hold a prior claim on
  answer-level tracking. Worth a demo before relying on the claim on camera.
- Which two vague-answer phrasings will be used in the demo script? They must be
  pre-tested against the adjudicator until behaviour is stable — the unedited
  rule means a wrong tick on camera cannot be trimmed out.

**Deferred to September (Shipaton, deadline 30 Sep)**

iOS build and framework choice · RevenueCat paywall · App Store listing
positioned generically rather than as healthcare · Google Drive export ·
offline capture with deferred sync.

Tag `ata-submission-2026-08-31` at the All Things Agentic deadline and point
the Devpost entry at the **tag**, not `main`, so September work never touches
the frozen submission.
