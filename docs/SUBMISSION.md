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

## Data sources

**No real client, patient or employer material is used anywhere** — not in the
repo, not in the demo, not in the eval.

- **The form template** (`templates/community-nursing-v1.json`) is *synthetic*,
  written for this project and informed by the shape of published community
  nursing assessment standards. It is not any employer's form. Item ids, wording
  and guidance notes are ours.
- **The second template** (insurance loss adjusting) is likewise synthetic, and
  exists to demonstrate that the vertical is configuration rather than code.
- **The 47 eval cases** (`eval/cases/`) are hand-written by us. The interviewee
  answers are invented to probe specific failure modes — vague quantifiers,
  answers split across turns, retractions, formal declines.
- **The demo dialogue** (`demo/script.toml`) is scripted and voiced by Gemini
  TTS. There is no recording of a real person in the video.
- **Runtime data**: sessions hold verbatim quotes from whoever is speaking, and
  are scoped to a job and a practitioner — never to a named subject. See
  *Privacy by architecture* in the README.

## Pre-existing and third-party code

**All project code was written during the submission period (3–31 Aug 2026).**
Nothing was carried in from an earlier project.

Third-party dependencies, all used as published packages under their own
licences — none vendored or modified:

| Dependency | Use |
|---|---|
| `google-adk` 2.6.2 | agent framework — the whole orchestration layer |
| `google-genai` 2.16.0 | Gemini calls via Vertex AI |
| `google-cloud-firestore` 2.28.0 | session state |
| `fastapi` 0.141.1 · `uvicorn` 0.52.1 | HTTP surface |
| `opentelemetry-exporter-gcp-trace` 1.9.0 | tracing (wired, disabled — see Known limitations) |
| `react` 18 · `react-dom` 18 · `vite` 6 | web client |
| `playwright` | demo capture only, not shipped |
| `pip-audit`, `pytest`, `pytest-asyncio`, `pyyaml` | CI and tests only |

No third-party JavaScript or CSS is loaded from a CDN — the client has no
external asset requests at all. No code was copied from tutorials, samples or
the ADK reference recipes; ADK is consumed strictly through its public API.

Generative assets in the demo video: the three voices are **Gemini 2.5 Flash
TTS** on Vertex AI (`demo/voices.py`). No stock footage, music or images.

**AI assistance:** the project was built with Claude Code as a pair programmer.
Design decisions, architecture and the eval methodology are recorded with their
reasoning in `docs/adr/`.

Licence: PolyForm Noncommercial 1.0.0.

## Checklist

- [x] Public repo, opens in incognito — **master was stuck on the scaffold commit until 20 Aug; 52 commits were unpushed**
- [x] Architecture diagram as an uploadable image — `docs/diagrams/intake-architecture.png`
- [x] README spin-up + reviewer instructions
- [x] Known limitations documented
- [x] Redeployed to `agent-era` — revision `intake-agent-00020-fft`, verified by
      the new security headers being live. The `gcloud` CLI credential is still
      broken for this project; ADC is not, so deploys work with
      `CLOUDSDK_AUTH_ACCESS_TOKEN=$(gcloud auth application-default print-access-token)`
- [x] Demo video re-rendered — 3:37, 84% speech, worst gap 4.1s, narration says "Gemini three point six Flash on Vertex A-I" aloud
- [ ] Upload video to YouTube **public**, in English — allow hours for processing
- [ ] Submission form drafted and saved
- [x] Data sources documented (all synthetic — no real patient or employer material)
- [x] Pre-existing / third-party code disclosed (none pre-existing; deps listed)
- [x] Category selected: Collaborative Partner
- [x] Model is Gemini 3.5+ (3.6 Flash)
- [ ] Teammates added and invitations accepted (solo entry? confirm)
- [ ] Startup Excellence — opt in only if entering, needs incorporated org name + corporate email
- [ ] Optional bonus: publish `docs/blog-post.md`, post `docs/social-post.md` with #AllThingsAgenticHackathon
- [x] Verified under 4:00 and frame-sampled: app renders, captions and cursor present, high-risk item shows "no suggested answer", eval card visible
