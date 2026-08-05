# Templates

The entire vertical lives here. No domain logic exists in code — see ADR-0003.

Two synthetic examples ship with the repo: community nursing assessment and
insurance loss adjusting. Swapping between them requires no code change, and
that swap is the test of whether the engine is honestly decoupled. If adding a
template forces a code change, fix the engine.

**Real client or employer forms are never committed.** Put them in
`templates/private/`, which is gitignored. The examples here are derived from
published standards.

## Item fields

| Field | Effect |
|---|---|
| `required` | Included in the completeness gate |
| `depends_on` | Conditional branching — required-ness is dynamic |
| `high_risk` | No AI-suggested answer; show the transcript quote, human writes it |
| `accepts_declined` | "Declined, reason X" counts as a real resolution |
| `guidance_ref` | Retrieval target used to judge answer sufficiency |
| `answer_type` | Structured extraction shape |
