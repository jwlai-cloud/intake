# Progress log

Update this at the **end of every session** — not just at milestones. Newest
entry at the top.

---

## 2026-08-05 (evening) — adjudicator and eval harness

**Score: 35/35 cases correct. Precision on `sufficient` 100%, recall 100%.**
No case labelled insufficient was marked sufficient — the gate passes. Stable
across three consecutive runs at `temperature=0`, which matters because the
demo take is unedited. Model `gemini-3.6-flash` via Vertex AI (`location=global`),
`google-genai==1.50.1`.

**Done**

- `backend/intake_agent/adjudicator.py` — one Gemini call per item, Vertex AI,
  `response_schema`-constrained JSON returning `verdict` / `evidence` /
  `missing` / `reason`. Verdict is the three-state vocabulary from ADR-0005:
  `sufficient` · `insufficient` · `declined`. The system instruction is the
  product: it defaults to insufficient, forbids inference to fill a gap,
  requires the evidence span to be verbatim, and makes the template's guidance
  note authoritative over the model's own taste (ADR-0003, ADR-0006).
- `eval/run_eval.py` — loads `eval/cases/*.json`, adjudicates them in a thread
  pool, prints a 3×3 confusion matrix plus precision/recall on `sufficient`,
  and exits 1 if any insufficient case was marked sufficient. `--item`,
  `--demo`, `--model`, `--workers`.
- `eval/cases/` — 35 cases across 14 required items of the synthetic community
  nursing template. 15 sufficient · 16 insufficient · 4 declined, including
  partial answers, answers arriving across two turns, deflections that are
  *not* declines, and explicit declines on items with `accepts_declined`.
- `eval/test_gate.py` — offline check that the harness itself fails when it
  should. An always-"sufficient" stub must exit 1. No model calls.
- Root `pyproject.toml` pinning `google-genai==1.50.1`.
- `LICENSE.md` — PolyForm Noncommercial 1.0.0. Public repo, noncommercial use.
- `docs/design/intake-prototype.html` — static UI reference for step 5, not
  wired to anything.

**Notes and caveats**

- 100% is a signal to *harden the cases*, not to celebrate. The set does not
  yet contain a case the adjudicator gets wrong, so it cannot currently detect
  a prompt regression that is subtler than the ones it was written against.
  Before recording, add adversarial cases: an answer that satisfies the
  guidance in unusual word order, a confident-sounding non-answer, and an
  interviewee correcting an earlier sufficient answer into an insufficient one.
- Two cases were sharpened during the run rather than left ambiguous:
  `M28-insufficient-some-bits` originally ended "I couldn't tell you what",
  which is a genuine borderline between insufficient and declined. If a case
  is arguable, it does not belong in a gate.
- Threading detail worth remembering: constructing the `genai.Client` inside
  worker threads races, and the discarded duplicate closes the shared
  transport, producing `Cannot send a request, as the client has been closed`.
  Build it once and pass it in.
- The item ids and guidance notes currently live inline in each case file. Step
  3 (encode the template) should make the template the single source and have
  the cases reference it by item id, so the two cannot drift.

**Next, in priority order**

1. Encode the synthetic nursing template per ADR-0003; point the eval cases at
   it by `item_id` instead of duplicating item and guidance inline. Check
   `depends_on` branching.
2. Harden the eval set with the adversarial cases described above.
3. ADK agent on Cloud Run wrapping the adjudicator; Firestore session schema.
4. React front end: mic → chunks → POST; Firestore listener → live UI.
5. Three-state gate (ADR-0005), report generation, share.
6. Loss-adjusting template — the decoupling test.
7. Failure tolerance: chunk retry with local queue, malformed-output reprompt,
   network-drop reconciliation.

Admin items from the previous entry are unchanged and still time-sensitive.

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
