# Devpost submission — working draft

Deadline **31 Aug 2026, 5:00pm PT**. Submissions lock at the deadline: do not
touch the repo, the video, or anything linked from the form after that.

## Form answers

| Field | Answer |
|---|---|
| Project name | Intake |
| Tagline | Your second chair. Nothing leaves the room unanswered. |
| Track | Collaborative Partner |
| Gemini model | `gemini-3.6-flash` via **Vertex AI** |
| Agent framework | **Google ADK 2.6.2** (Python) |
| Google Cloud services | Cloud Run, Firestore, Secret Manager, Cloud Logging |
| Google SDK used | `google-adk` 2.6.2 · `google-genai` 2.16.0 |
| Hosted project URL | https://intake-agent-320877670799.us-central1.run.app |
| Repo | https://github.com/jwlai-cloud/intake (public) |
| Reproducible testing instructions in README? | Yes — *For reviewers and judges* + *Spin-up* |
| Date started | 3 Aug 2026 |

**Testing instructions (paste into the form, with the key filled in):**

> The service scales to zero — call `/health` once and wait for
> `{"ok":true,"store":"FirestoreStore"}` before using the UI; the first request
> can take ~15s.
>
> The API is gated so an open endpoint cannot drain Vertex credit. Use
> `X-Intake-Key: <KEY>`, or paste the key into the web client when prompted.
> `practitioner_id` is a free-text label, not a login — any value works.
>
> To check the core claim without deploying anything:
> `cd eval && uv run python run_eval.py` — 47 labelled cases, exits non-zero if
> the agent ever accepts an answer a human labelled insufficient.

## The story

**Inspiration.** A community nurse has ninety minutes and a form she is legally
required to complete. She asks about falls. The answer is *"oh, I've had a
couple of wobbles."* Every AI scribe on the market ticks that item — it was
mentioned. It was never answered. She finds the gap that evening, at her desk,
and now it needs a phone call, a guess, or a second visit.

**What it does.** Intake listens to a structured interview and adjudicates, per
required item, whether it actually received a substantive answer — not whether
the topic came up. It surfaces the gaps while the interview is still running,
and refuses to produce a report until every mandatory item resolves into one of
three states: answered with the transcript span it came from, formally declined
where the form permits it, or escalated with a follow-up the agent drafts and
routes itself.

Microsoft Teams' Facilitator marks a topic covered "once the discussion has
started". Balto ticks on mention. Otter checks off objectives. None of them
adjudicate whether a required item received a real answer, and none gate the
output on it.

**How we built it.** Gemini 3.6 Flash on Vertex AI, orchestrated with Google ADK
2.6.2 on Cloud Run, session state in Firestore. Audio arrives in 15–20s chunks;
each turn runs transcribe → route → adjudicate → coach. Adjudication is one
schema-constrained call *per open item*, fanned out concurrently, so a wrong
verdict on one item cannot corrupt another and each is separately scoreable.

The eval came before the UI: 47 labelled cases with a hard gate that exits
non-zero if a single insufficient answer is ever ticked.

**Challenges.** ADK 2.x moved fast and our own notes were wrong about it. The
sharpest one: we recorded that the graph `Workflow` migration was blocked
because a `Workflow` cannot take an `LlmAgent` sub-agent. The deprecation
warning says the *reverse*. Re-testing found the real blocker — graph nodes emit
events with no `content`, and ADK's own eval CLI rejects those, failing the whole
case. So the deprecated orchestrator and the current one are both incompatible
with the current eval tooling, and a four-line custom `BaseAgent` is the only
shape that can be evaluated. Every API claim in the project was afterwards
verified by inspecting the installed package rather than reading a summary.

**Accomplishments.** 47 labelled cases at **100% precision** on `sufficient` — it
has never once ticked an answer a human labelled insufficient. A behavioural
eval over the pipeline at 18/18. 116 backend tests. A second template — insurance
loss adjusting — runs on the same engine with no code change.

**What we learned.** Write the adversarial eval cases first; they found a real
bug in the first hour. And read signatures off the installed package, not off
documentation — the one time we trusted a written note instead, it was wrong in
the direction that blocked a migration for three days.

**What's next.** Practitioner-scoped memory: which question phrasings actually
close which items, learned across interviews. Never about the people being
interviewed — that would break the privacy guarantee that makes this deployable.

## Checklist

- [x] Public repo, opens in incognito — **master was stuck on the scaffold commit until 20 Aug; 52 commits were unpushed**
- [x] Architecture diagram as an uploadable image — `docs/diagrams/intake-architecture.png`
- [x] README spin-up + reviewer instructions
- [x] Known limitations documented
- [ ] Redeploy Cloud Run from current `master` — **blocked**: `gcloud` is denied
      `run.services.get` on `agent-era` for both accounts, though the running
      service and Vertex both work. Fix with `gcloud auth login` as the project
      owner, then `GOOGLE_CLOUD_PROJECT=agent-era ./backend/deploy.sh`
- [ ] Re-render the demo video (narration now names Gemini 3.6 Flash aloud)
- [ ] Upload video to YouTube **public**, in English — allow hours for processing
- [ ] Submission form drafted and saved
- [ ] Verify the video is under 4:00 and the Cloud Console proof is visible in it
