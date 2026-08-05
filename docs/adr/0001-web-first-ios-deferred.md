# 0001 — Web first, iOS deferred

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

Two contests are in play: All Things Agentic (deadline 31 Aug 2026, web allowed, a hosted URL is "highly encouraged") and RevenueCat Shipaton (deadline 30 Sep 2026, requires a store-published native app). A cross-platform framework chosen now would be a tax paid in August for a platform not shipped until September. Flutter web audio capture was unverified; browser MediaRecorder in plain React is well-trodden.

## Decision

Build web-only in plain React for the 31 Aug deadline. Defer the iOS path and its framework choice to September. Evaluate wrapping the React app (e.g. Capacitor) versus a separate native build at that point.

## Consequences

The hosted-URL requirement becomes trivial and the "capable of being installed and run consistently" clause stops being a risk. The in-person differentiator becomes harder to *show* on a screen recording, so the demo needs one establishing shot of the laptop on a table with two people. Verify RevenueCat's Capacitor support before committing in September.
