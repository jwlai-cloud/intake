# Learning notes

For reading slowly, after the hackathon. What each piece actually does, why it
was chosen, and where the primary sources are.

## Google ADK (Agent Development Kit)

ADK 2.0 went GA for Python on 19 May 2026 and for Go on 30 Jun 2026; TypeScript,
Java and Kotlin remain on 1.x. In 2.0 agents subclass `BaseNode`, callbacks moved
to `BeforeAgentCallback`/`AfterAgentCallback`, events must be yielded from nodes,
and the event schema gained `node_info`/`output`. **Anything written before 2.0
will not copy-paste.** The package moves fast — 2.6.0, 2.6.1 and 2.6.2 all
shipped within a week of this project starting.

Default session storage is in-memory and dies on Cloud Run instance recycle.
That is why session state lives in Firestore instead (ADR-0004).

- https://adk.dev/2.0/
- https://pypi.org/project/google-adk/
- https://github.com/google/adk-docs/blob/main/docs/deploy/cloud-run.md

## Why not the Gemini Live API

The obvious design for a live interview assistant is bidirectional streaming.
Three reasons it was rejected: sessions cap at roughly 10–15 minutes against a
30–60 minute interview, requiring context compression and session resumption;
Cloud Run session affinity is only best-effort, so a reconnect can hit a cold
instance; and the only general-purpose Live model, `gemini-3.1-flash-live-preview`,
is *below* this contest's mandatory Gemini 3.5 floor. The one 3.5-generation Live
model is translation-specific.

- https://ai.google.dev/gemini-api/docs/live-api
- https://ai.google.dev/gemini-api/docs/models
- https://docs.cloud.google.com/run/docs/triggering/websockets

## Gemini native audio, and why there is no separate speech-to-text

Gemini accepts audio directly and will do speaker diarization and timestamps in
the same call that does the reasoning. Cost works out roughly equivalent to batch
Speech-to-Text, but it replaces two components with one — the same call returns
transcript, slot verdicts, next question and candidate highlights as structured
output. Cloud Speech-to-Text v2 (`chirp_3`) is the alternative and has no free
tier.

- https://ai.google.dev/gemini-api/docs/audio
- https://cloud.google.com/speech-to-text/pricing

## Structured output as an architectural device

The interesting property is not the JSON, it is that a fixed output schema makes
the state bounded. Because the model returns verdicts against a known set of
items, the state can be a fixed-size struct rather than a growing transcript —
which is what keeps context flat across a long interview.

## Firestore realtime listeners

`onSnapshot` turns the backend into the only writer and the UI into a pure
function of stored state — no polling code, no optimistic update reconciliation.
Offline persistence matters here beyond convenience: home visits lose signal as
the normal case.

- https://firebase.google.com/docs/firestore/query-data/listen

## FHIR Questionnaire / QuestionnaireResponse

Worth knowing even though it stays an optional adapter: FHIR already models
exactly "a structured assessment template" (`Questionnaire`) and "a filled-in
assessment" (`QuestionnaireResponse`). Mapping onto it costs a schema decision
rather than engineering time, and it reads as domain-native to anyone in health
IT. Kept as an adapter over the generic schema so the general engine stays the
core.

## MedGemma 1.5 and MedASR

Released as open weights on 13 Jan 2026. MedASR is medical-domain speech
recognition at 5.2% WER against Whisper large-v3's 12.5% on the same task, free
for commercial use. Relevant if the healthcare template's audio path needs better
clinical vocabulary.

- https://research.google/blog/next-generation-medical-image-interpretation-with-medgemma-15-and-medical-speech-to-text-with-medasr/

## Platform churn worth remembering

Vertex AI was folded into the Gemini Enterprise Agent Platform; the Vertex AI
console was removed around 21 May 2026 and the `vertexai.generative_models`,
`language_models`, `vision_models`, `tuning` and `caching` SDK modules were
removed on 24 Jun 2026 in favour of the `google-genai` SDK. The
`aiplatform.googleapis.com` endpoint is unchanged. Any tutorial older than that
is wrong in the imports.

## The regulatory reading

NHS England's guidance on AI-enabled ambient scribing products (v3, last updated
29 Jul 2026) is the single most relevant document. Section A1.2 asks suppliers to
guard against users instructing products to "suggest diagnoses or identify
missing consultation components" — note that this is framed as an
intended-purpose concern, **not** a device-classification criterion; NHS England
explicitly declines to classify products, and the actual qualification triggers
in Box 2 are administrative functions, clinical decision support, and diagnosis
or treatment plans. Under EU MDR, intended purpose including marketing copy is
legally determinative.

- https://www.england.nhs.uk/long-read/guidance-on-the-use-of-ai-enabled-ambient-scribing-products-in-health-and-care-settings/
