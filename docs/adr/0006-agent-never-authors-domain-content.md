# 0006 — The agent never authors domain content

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

NHS England's ambient-scribing guidance (v3, last updated 29 Jul 2026, section A1.2) asks suppliers to guard against users instructing products to "suggest diagnoses or identify missing consultation components". This is an intended-purpose and scope-creep concern rather than a device-classification criterion — NHS England explicitly declines to classify — but under EU MDR intended purpose including marketing copy is legally determinative.

## Decision

The agent tracks coverage against a human-authored form and quotes the transcript span it relied on. Nudges derive from the template and its guidance notes, both human-authored artifacts, never from the model's own domain inference. No ranking, recommending or implying a next action, and no "call to action" phrasing in UI or demo copy. For items flagged `high_risk`, offer no suggested answer at all: show the transcript quote and require the human to write it (Birdie SmartPlans ships this pattern, so it is defensible by precedent).

## Consequences

Slot-filling over a fixed schema with span citations is cheaper to build, easier to evaluate and easier to demo than open-ended reasoning. Keeps the declared intended purpose administrative. Combined with ADR-0007, healthcare becomes one configuration of a general documentation tool rather than the product's identity.
