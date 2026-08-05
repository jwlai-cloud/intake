# 0003 — Template as config, zero domain logic in code

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

The product must work for community nursing, insurance loss adjusting, safety inspection and similar regulated field interviews. The contest's Architectural Discipline criterion (30%) asks specifically how well systems are decoupled.

## Decision

The entire vertical lives in a JSON template artifact: sections, items, and per-item `required`, `depends_on`, `high_risk`, `accepts_declined`, `guidance_ref`, `answer_type`. No nursing-specific or insurance-specific logic exists in code. The healthcare template may additionally be expressed as a FHIR Questionnaire via an optional adapter over the generic schema — never as the core format.

## Consequences

Adding the loss-adjusting template is the test of whether this holds. If it requires a code change, the engine is not decoupled and the engine gets fixed, not the template. Demonstrating a live template swap is the architecture argument made visually.
