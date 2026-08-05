# 0002 — Chunked audio, not bidirectional streaming

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

A real assessment interview runs 30–60 minutes. The Gemini Live API caps sessions at roughly 10–15 minutes, requires PCM16/16kHz plumbing and WebSocket transport, and would need context-window compression plus session resumption. Cloud Run session affinity is best-effort only. Separately, the only general-purpose Live model is gemini-3.1-flash-live-preview, which is below the contest's mandatory Gemini 3.5 floor.

## Decision

Record in rolling 15–20 second chunks and POST each to the backend. One Gemini call per chunk performs transcription, slot adjudication, branching evaluation, next-question generation and highlight extraction together, returning structured output. No audio output at all — suggestions render on screen.

## Consequences

The **slot state is the state**, not the transcript: each call carries the open template items, a fixed-size struct of current slot values, and the new audio. Context is bounded and roughly constant regardless of interview length, so a three-hour session costs the same per chunk as a ten-minute one and never degrades. This is the correct state model, not an expedient — frame it that way in the submission. Also sidesteps the Gemini 3.5 floor problem entirely.
