# 0008 — ADK 2.6.2: SequentialAgent now, Workflow later

- **Status:** Superseded by ADR-0010 (the orchestrator) and ADR-0013 (the
  migration path). **Contains a factual error — see the correction below.**
- **Date:** 2026-08-05

> **Correction (2026-08-09).** This ADR reads the deprecation warning
> backwards. ADK says a `Workflow` cannot be nested *inside* an `LlmAgent`; it
> does not say a `Workflow` cannot *contain* one. `LlmAgent` and `BaseAgent`
> are both `BaseNode` subclasses and compose into a graph fine. The migration
> was never blocked by the reason given here. ADR-0013 records the real
> blocker and the decision that replaces this one.

## Context

The project's working notes recorded that "ADK 2.x agents subclass `BaseNode`".
Checked against a real install of `google-adk==2.6.2` before writing any
integration code, that is not the API for agents:

- `google.adk.agents` exports `BaseAgent`, `LlmAgent`, `SequentialAgent`,
  `ParallelAgent`, `LoopAgent`. Custom agents override `_run_async_impl` and
  yield `Event`s. There is no `BaseNode` in that package.
- `BaseNode` does exist, in `google.adk.workflow._base_node`, as part of a new
  graph-based `Workflow` API. Its contract is different:
  `_run_impl(self, *, ctx, node_input)` yielding values rather than Events.
- Constructing a `SequentialAgent` emits: *"SequentialAgent is deprecated in
  favor of Workflow and will be removed in a future version. Workflow cannot
  yet be used as an LlmAgent sub-agent."*
- `google-adk==2.6.2` requires `google-genai>=2.9,<3`, which invalidated the
  earlier `google-genai==1.50.1` pin.

## Decision

Build the turn pipeline as a `SequentialAgent` of three stages, with the
adjudication stage as a custom `BaseAgent`. Do not migrate to `Workflow` for
this submission.

Two of the three stages are `LlmAgent`s, and ADK itself says Workflow cannot yet
be a sub-agent of an LlmAgent — so a migration today would mean restructuring
the pipeline around a capability gap the framework has already flagged, during
a hackathon, for a deprecation warning no judge will run into.

## Consequences

The build carries a visible `DeprecationWarning` in test output. That is
accepted and recorded here rather than suppressed, because suppressing it would
hide the one signal that says when to migrate.

Migration path when Workflow supports LlmAgent composition: the three stages
become nodes with `edges=[(START, transcriber), (transcriber, adjudication),
(adjudication, coach)]`, and `AdjudicationAgent._run_async_impl` becomes
`_run_impl` returning its brief as `node_input` to the coach rather than
smuggling it through `state_delta`. The state-passing gets *cleaner* under
Workflow, which is the main reason to expect the migration to be worth doing.

Also: pin both `google-adk` and `google-genai` together. They move as a pair.
