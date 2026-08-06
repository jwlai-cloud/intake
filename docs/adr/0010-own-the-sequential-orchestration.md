# 0010 — Own the sequential orchestration; drop SequentialAgent

- **Status:** Accepted (supersedes the "stay on SequentialAgent" part of ADR-0008)
- **Date:** 2026-08-06

## Context

ADR-0008 decided to keep `SequentialAgent` despite its deprecation in ADK 2.6.2,
on the grounds that the replacement graph `Workflow` API cannot yet take an
`LlmAgent` as a sub-agent, and that a deprecation warning in test output harms
nobody.

Adding behavioural evaluation with `agents-cli eval` invalidated that reasoning.
`eval generate` rejects any agent event lacking `content`:

    Malformed agent event: missing content.

`SequentialAgent` always emits a container event carrying only `actions`. So
does the `before_agent_callback` state-initialisation pattern that ADK's own
eval documentation recommends. **ADK's deprecated orchestrator and its
documented state-init pattern are both incompatible with ADK's current eval
tooling.** Every one of the six eval cases failed at parse time, before a single
metric ran.

## Decision

Replace `SequentialAgent` with `TurnPipeline`, a `BaseAgent` whose
`_run_async_impl` iterates `self.sub_agents` and forwards their events. Replace
the `before_agent_callback` in the ADK entrypoint with an override that sets the
state key inline and yields nothing extra.

Sequential composition is a four-line loop. Owning it costs almost nothing and
buys total control over what appears in a trace.

## Consequences

Behavioural evaluation became possible, and immediately earned its place: the
first clean run scored 4.2/5 on the "never supplies the answer" metric and found
a real ADR-0006 hole. The coach's `highlights[].title` is unconstrained free
text — the output schema forbids an answer *field* but not an interpretive
*label*, and the coach had emitted "Formal decline to answer alcohol question".
A title like "Client appears to be hiding drinking" would have passed the schema
just as easily. The instruction now requires `title` to be a bare noun phrase.

The deprecation warning is gone as a side effect, which was never the point.

We lose whatever `SequentialAgent` does beyond ordering — currently nothing we
use. If ADK later adds behaviour there worth having, or `Workflow` gains
`LlmAgent` composition, revisit. The migration target in ADR-0008 still stands;
this decision only changes what we do in the meantime.

**Generalisation worth keeping:** an event with no content is invisible. Not
just to eval — to `adk web` and to anything reading a trace. The adjudication
stage now emits a one-line audit summary alongside its state delta for the same
reason.
