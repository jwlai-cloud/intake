# Progress log

Update this at the **end of every session** — not just at milestones. Newest
entry at the top.

---

## 2026-08-06 — deployed on Cloud Run, on the personal project

**Live:** https://intake-agent-320877670799.us-central1.run.app
**Eval: 46/47, precision on `sufficient` 100%.** 51 backend tests.
Project **agent-era** (personal), Firestore native database `intake`,
region us-central1.

**The account mix-up, and what it cost**

The `gcloud` configuration named `personal` was pointing at account
`junwei.lai@trafficguard.ai` and project `tgds-dev` — the work project. Read at
face value at session start, so every Vertex call up to this point billed there.
Nothing was *created* on the work project: Cloud Run, Secret Manager and
Artifact Registry were listed and contain no `intake` resource, and the single
Firestore write attempt was rejected outright because that project's default
database is Datastore mode. Now on `agent-era` throughout.

Second trap, which cost longer: `GOOGLE_APPLICATION_CREDENTIALS` is exported in
the shell profile pointing at a TrafficGuard service-account key. It silently
overrides `gcloud auth application-default login`, so the first attempt against
`agent-era` authenticated as that service account and returned 403. Any terminal
running Intake must unset it. Now documented in README and `.env.example`.

**Done**

- **Router** (`router.py`) — fixes the evidence bleed that headed the last
  known-issues list. One small call decides which open items a chunk bears on;
  only those are adjudicated. Items touched by "a couple of wobbles" went
  7 → 5 → **2**. Recall-biased and fails open, because an unrouted item is an
  unasked question.
- **12 adversarial eval cases** (47 total) and they found a real bug on the
  first run: a retracted answer ("I'm thinking of my sister") was read as a
  clean nil return and the item ticked. Fixed with rule 8 — the later turn
  governs only when it is itself a clear answer or refusal; a hedged retraction
  settles nothing and a contradiction is the practitioner's to resolve.
- **Firestore native database created and verified.** Session documents written,
  chunk sequences recorded, slot states persisted. The probe was also fixed: it
  used a document id of `__probe__`, which Firestore reserves, so it failed on a
  perfectly healthy database.
- **Deployed to Cloud Run** and verified end to end against the live URL: 401
  without the key, M14 partial after chunk one, answered after chunk two, M15
  opening conditionally, the gate returning 409, and the agent drafting a
  follow-up routed to the Occupational therapy queue.
- **Harness hole fixed.** With every case erroring it printed "precision 100%"
  over a table of zeroes, because precision on an empty denominator was
  hardcoded to 1.0. A totally broken run read as a perfect one.
- `/healthz` renamed to `/health` — Cloud Run's frontend reserves that path and
  answers it itself, so the request never reached the container.
- `requirements.txt` is now generated from the resolved environment. Hand-pinned
  `fastapi==0.121.2` conflicted with ADK 2.6.2's `fastapi>=0.133` and the first
  image build failed, even though the tested venv was correct.

**Known issues**

1. **The API key ships in the browser bundle.** `--allow-unauthenticated` plus
   an `X-Intake-Key` header is the only workable gate for a browser client with
   no user accounts, but the key is readable by anyone who opens the JS. It
   stops drive-by traffic and nothing more. A hard project spend cap and taking
   the service down between demos are what actually carry the risk.
2. **No spend cap set yet.** Do this before leaving the service up.
3. One eval miss remains, `M12-adversarial-indirect-quantity` — weight loss
   evidenced by a wedding ring resized twice, where the adjudicator wants
   unintentionality stated outright. False-insufficient, the safe direction, and
   kept deliberately: a suite where everything passes cannot show it is able to
   fail.
4. The web client has not been driven against the deployed URL in a browser —
   only curl. Build it with `VITE_API_BASE`/`VITE_API_KEY` and click through.
5. Practitioner memory still unwritten; no Firestore realtime listener yet.

**Next, in priority order**

1. Set a billing budget/alert on agent-era, then leave the service up or take it
   down.
2. Point the web client at the deployed URL and click through the whole flow in
   a browser, including microphone capture.
3. Capture the Cloud Run dashboard and Vertex AI logs for the demo video.
4. Demo script; pre-test the vague phrasings until stable on camera.
5. Realtime listener; practitioner memory.

---

## 2026-08-05 (late) — all components built, end to end on live Vertex AI

**Eval: 35/35. Precision on `sufficient` 100%, recall 100%. Backend suite: 45
tests, no network.** Stable across repeated runs at `temperature=0`.

Branch `dev`. Not yet deployed to Cloud Run; everything else runs.

**Done**

- **Template engine** (`template.py`) + two synthetic verticals, community
  nursing (14 required items) and loss adjusting (10). `depends_on` is a closed
  condition set, not an expression language, and required-ness is recomputed
  after every chunk. `test_second_template_needs_no_code_change` is ADR-0003's
  claim made falsifiable.
- **Eval cases now reference the template** by `template_id` + `item_id`. Two
  M14 cases had already drifted to different guidance text; that is now
  structurally impossible.
- **ADK pipeline** (`agent.py`): `SequentialAgent` of transcriber (LlmAgent) →
  adjudication (custom `BaseAgent`, fans out one call per open item) → coach
  (LlmAgent). Plus `Escalator`, which drafts and files the follow-up action.
- **Session store** (`store.py`): Firestore document per session, slots as a
  map, `partial` as a first-class state. In-memory fallback behind a real
  round-trip probe.
- **HTTP service** (`main.py`): sessions, chunks, resolve, highlights, report.
  Gate returns 409 *with* the outstanding items and whether each may be
  declined. Shared-secret header, 8MB audio cap, replay-safe chunk claims,
  degraded-but-alive on turn failure.
- **Report** (`report.py`): assembled deterministically, no model call — the
  agent authoring the prose is exactly what ADR-0006 forbids.
- **React front end** (`web/`): the prototype's CSS ported verbatim, mic capture
  at 18s chunks, local queue with in-order replay, live coverage, gate modal
  with all three resolutions, editable report. Typed-input path drives the same
  pipeline for noisy rooms and for demos without a microphone.
- **Cloud Run**: `backend/Dockerfile`, pinned `requirements.txt`, `deploy.sh`
  that stages `templates/` into the build context.
- **Docs**: ARCHITECTURE rewritten to current state, ADR-0008 (ADK), ADR-0009
  (Firestore shape + fallback), LEARNING corrected and extended, README spin-up
  rewritten and its architecture diagram corrected.

**Verified live, not just mocked**

A chunk containing *"oh, I've had a couple of wobbles"* leaves M14 **partial**
with the quote attached, coverage 1 of 14, and generates the next question
*"Roughly when did these wobbles first start?"*. The gate refuses the report
with the outstanding list. Escalating M20 with no reason had the agent draft the
follow-up and route it to the Occupational therapy queue. That is the whole
product working against real Vertex AI.

**Corrections to previously recorded beliefs**

- `CLAUDE.md` said ADK 2.x agents subclass `BaseNode`. They subclass
  `BaseAgent`. `BaseNode` belongs to the separate `google.adk.workflow` graph
  API. Corrected in CLAUDE.md, LEARNING.md, and ADR-0008.
- `google-adk==2.6.2` requires `google-genai>=2.9,<3`, so the `1.50.1` pin from
  the previous session was incompatible. Now on 2.16.0; eval re-scored after
  the bump.
- LEARNING.md claimed one Gemini call per chunk would do everything. The build
  deliberately does not — see the corrected section there for why.

**Known issues, in the order they should be fixed**

1. **Evidence bleed.** A vague utterance about falls gets attached as
   `evidence` to unrelated items — M02, M06, M16, M26 all claimed the "wobbles"
   quote. Adding the `addressed` boolean cut it from 7 items to 5; it did not
   solve it. Every open item independently judges relevance against the same
   turns, and a vague remark is weakly relevant to many. The fix is a routing
   call: one cheap classification of which items a chunk bears on, then
   adjudicate only those. That also cuts per-chunk cost from ~14 calls to ~2.
   Safe direction (nothing is falsely ticked, the gate still holds) but visibly
   sloppy in the UI, and it must be fixed before recording.
2. **The eval set has no case the adjudicator fails.** 100% means it cannot
   currently detect a subtle prompt regression. Add adversarial cases: guidance
   satisfied in unusual word order, a confident-sounding non-answer, and an
   interviewee walking back an earlier sufficient answer.
3. **Not deployed.** Cloud Run deploy is scripted but unrun, and the contest
   needs visible proof of Google Cloud in the video.
4. **Firestore is untested against a real native database.** The development project's
   default database is Datastore mode, so every live run so far used the memory
   fallback. Create a native database before claiming Firestore on camera.
5. Practitioner memory (`practitioners/{id}`) is in the schema and not written.
6. No realtime listener yet — the client uses the POST response. The document
   shape already supports `onSnapshot`.

**Next, in priority order**

1. Routing call to fix evidence bleed (known issue 1).
2. Create the native Firestore database; re-run the live walkthrough against it.
3. Deploy to Cloud Run; capture the dashboard and Vertex logs for the video.
4. Harden the eval set (known issue 2).
5. Firestore realtime listener in the client, replacing response-driven updates.
6. Demo script, and pre-test the two vague phrasings until behaviour is stable.

Admin items from the first entry are unchanged and still time-sensitive.

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
