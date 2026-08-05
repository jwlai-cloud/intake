# 0009 — Slots as a map on the session document, with a memory fallback

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

ADR-0004 settled that we own session state in Firestore rather than using ADK's
session service. It did not settle the document shape, and shape drives both the
realtime UI and the write pattern.

Two candidates: slots as a `slots/{itemId}` subcollection, or slots as a map
field on the session document.

Separately, the development project's default database turned out to be in
Datastore Mode, where the Firestore native API rejects every write. The client
constructs successfully and fails only on first use — so a naive "try to
construct, fall back on error" guard passes at startup and then takes the
session down mid-interview.

## Decision

**Slots are a map on the session document.** A template has tens of items, not
thousands, so the 1MiB ceiling is not in play. In exchange: the entire coverage
view arrives in a single realtime snapshot, and each chunk is one atomic write
rather than N.

**The store falls back to memory after a real round-trip probe**, not after a
successful constructor. `FirestoreStore.probe()` performs an actual read at
startup; failure logs a warning and swaps in `MemoryStore`.

## Consequences

A subcollection would have allowed per-slot listeners and unbounded item counts.
Neither is needed, and both would cost a fan-out of writes per chunk and a
messier client.

The fallback means a demo survives an unreachable or wrong-mode database, at the
cost of state that does not outlive a restart. The warning is loud and
`/healthz` reports which store is live, so "it silently wasn't using Firestore"
is not a failure mode we can walk into unknowingly — which matters when a
contest requires demonstrating genuine Google Cloud usage.

Firestore in **native mode** is a hard requirement. On a project whose default
database is Datastore Mode, create a named native database and set
`FIRESTORE_DATABASE`.
