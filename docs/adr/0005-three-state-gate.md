# 0005 — Three-state gate, not a refusal

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

A gate that only says "no" is a blocker practitioners may reject — Inspect Point deliberately declined to gate its field copilot, noting technicians retain control of the report output. Separately, the contest's heaviest criterion (Innovation & Operational Utility, 40%) rewards "high-value, autonomous execution", and a purely advisory copilot scores poorly against that clause.

## Decision

Every required item resolves into exactly one of three states before the report is produced: **answered** with its transcript span as evidence; **formally declined** with a recorded reason; or **escalated**, where the agent autonomously drafts and files a follow-up action stating what is outstanding, why it could not be closed, and where it needs to go.

## Consequences

The gate becomes a router rather than a wall, which answers the practitioner-resistance objection. The escalation path is genuine autonomous execution — unprompted judgement, multi-step chain, real artifact — which addresses the 40% criterion directly. The Twist is stated as **"nothing is ever silently blank"**, not "it refuses". The demo gains three visible outcomes instead of one.
