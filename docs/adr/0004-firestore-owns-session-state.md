# 0004 — Firestore owns session state, not ADK sessions

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

ADK's default session storage is in-memory and does not survive a Cloud Run instance recycle. Cloud Run session affinity is documented as best-effort only, so a reconnect can land on a cold instance.

## Decision

Interview state lives in Firestore, not in ADK sessions. The React client subscribes with Firestore realtime listeners, so the backend writes and the UI updates with no polling code. Offline persistence is enabled.

## Consequences

State survives instance recycling and the live-updating UI comes free. Firestore also serves as the datastore for the practitioner style profile and for guidance-note retrieval, keeping one datastore for state and retrieval. Showing Firestore documents updating during the demo directly satisfies the rubric's "database updates" wording.
