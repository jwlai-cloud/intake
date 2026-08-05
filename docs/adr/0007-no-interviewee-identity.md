# 0007 — Practitioner-scoped memory, no interviewee identity

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

The Collaborative Partner track requires the agent to adapt to "the user's unique way of thinking", and the contest resources name persistent memory and real-time context retrieval as what the track's judging is built around. An earlier design stored per-subject visit history, which pointed the memory at the wrong party and created a large personal-data surface.

## Decision

Store no interviewee identity of any kind — no names, no identifiers, no per-subject history. Sessions are scoped to a job. Persistent memory is scoped to the practitioner: highlight-category acceptance rates, question phrasing preferences, report voice, pacing. Retrieval runs over the form's own guidance-note corpus, which contains no personal data.

## Consequences

Closer to the literal track wording than per-subject memory was. Removes an entire class of legal exposure — the transcript can be discarded on session close. Gives a memorable and architecturally true claim: "we never store who you spoke to". Also materially simplifies any future App Store submission, where health-data guidelines would otherwise apply.
