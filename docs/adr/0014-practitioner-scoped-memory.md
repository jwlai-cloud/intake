# 0014 — Memory is scoped to the practitioner, and enforced there

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

The Collaborative Partner track is judged on "how data is ingested, processed,
and leveraged for continuous self-improvement over time". Until now the session
schema documented `practitioners/{id}` with dismissed categories and phrasing
notes, and nothing read or wrote it — the capability the track is scored on was
a docstring.

The obvious version of agent memory is the wrong one here. "People like this
one usually under-report falls" would be useful, would demo well, and would
destroy the guarantee that makes the product deployable: no interviewee
identity, ever (ADR-0007). A care record is not a place to accumulate
inferences about the person being recorded.

## Decision

Memory is keyed on `practitioner_id` and holds exactly two kinds of fact:

- **question phrasings that closed an item on the first ask** — text the *agent*
  wrote, from a human-authored template
- **item ids whose highlights she repeatedly dismisses** — an id, never the
  quote she rejected

The distinction that makes this safe is the difference between a question and
an answer. A question is the agent's own composition. An answer is a person
speaking about their own health. The first may cross sessions; the second may
not.

It lives in `memory.py`, separate from `store.py`, so the boundary is visible in
the file tree rather than only in review: a session write may carry interviewee
speech, a memory write may not, and they do not share a code path.

`_carries_interviewee_speech()` rejects a candidate phrasing that is quoted, is
not a question, or has a first-person subject. It logs a warning rather than
failing silently, because a silent drop would hide a real leak.

## Consequences

The coach brief gains a section only from the second interview onward, offering
a phrasing that previously worked for a still-open item, and naming categories
whose highlights should not be proposed. A muted category is still **asked** —
muting a highlight must never mute a required question, and there is a test that
fails if it does.

`tests/test_memory.py` includes five samples of real interviewee speech and
asserts none of them can be stored by any route. The privacy claim appears in
the README, the submission text and the demo narration, so it needed to be a
claim the suite can fail on.

## What would make this wrong

- A practitioner sharing an id with a colleague, which would pool their
  phrasings. Firebase Auth (ADR-0012) makes the id a real identity and fixes it.
- The heuristic guard being too blunt in the other direction. It already was
  once: an early version rejected "could you tell me what prompted the
  referral?" because it matched on the word "me". Narrowed to first-person
  subjects.
- Evidence that phrasing transfers poorly between practitioners, which would
  make the whole signal noise. Untested — there is one practitioner.
