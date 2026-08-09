# 0013 — Stay on a custom BaseAgent; do not migrate to the Workflow graph

- **Status:** Accepted (corrects a factual error in ADR-0008, and supersedes the
  "migration path" section of ADR-0008 and ADR-0010)
- **Date:** 2026-08-09

## Context

ADR-0008 recorded that migrating off the deprecated `SequentialAgent` was
blocked because *"`Workflow` cannot yet take an `LlmAgent` as a sub-agent"*.
ADR-0010 repeated it, and `agent.py` stated it in a docstring.

**That is a misreading, and it is backwards.** The warning `google-adk==2.6.2`
actually emits when a `SequentialAgent` is constructed is:

    SequentialAgent is deprecated in favor of Workflow and will be removed in a
    future version. Workflow cannot yet be used as an LlmAgent sub-agent.

It says a `Workflow` cannot be nested **inside** an `LlmAgent`. It says nothing
about `LlmAgent`s inside a `Workflow`. Verified against the install:

    LlmAgent subclass of BaseNode?  True
    BaseAgent subclass of BaseNode? True
    Workflow(name="probe", edges=[(START, a), (a, b)])  -> builds, two LlmAgents

So both our `LlmAgent` stages and our custom `AdjudicationAgent` would drop into
a graph as nodes. The migration was never blocked by what we said blocked it.

Re-examining it on the merits produced a different, durable blocker.

## The real blocker: graph events carry no `content`

`agents-cli eval generate` parses every event off `/run_sse` and raises on any
that lacks `author` or `content` (`eval/cmd_generate.py:198`). The parse is a
list comprehension over the whole stream, so **the first malformed event fails
the entire eval case** — no per-event skip.

The graph engine's node-to-node data passing emits exactly such events. Measured
with a two-function workflow and `InMemoryRunner`:

    author='probe'  content=NONE  output='one'  -> eval REJECTS
    author='probe'  content=NONE  output='two'  -> eval REJECTS

This is the same failure that forced `SequentialAgent` out in ADR-0010, for the
same underlying reason: an ADK orchestration primitive emitting container or
data-transport events that ADK's own eval CLI refuses.

| Orchestrator | Deprecated | Emits content-less events | `agents-cli eval` |
|---|---|---|---|
| `SequentialAgent` | yes | yes (container event) | breaks |
| `Workflow` graph | no | yes (`Event(output=…)`) | breaks |
| custom `BaseAgent` | no | only if we write one | works |

It is a tax rather than a wall. A node returning an explicit
`Event(output=x, content=…)` is accepted:

    output='rich'  content=SET  -> eval accepts

But that is the whole point: hand-authoring `content` on every node is precisely
what `TurnPipeline` already does, in four lines, without the graph.

## Decision

Keep the turn pipeline as a custom `BaseAgent` (`TurnPipeline`). Do not migrate
to `Workflow` for this submission.

This is no longer "defer a migration we are blocked from doing". `BaseAgent` is
not deprecated in 2.6.2 and is a first-class extension point; of the three
orchestration options it is the only one compatible with ADK's current eval
tooling without per-node workarounds. Migrating would cost a rewrite of the one
component whose event shape is load-bearing for evaluation, and buy per-node
`RetryConfig` and a conditional edge the pipeline has no use for — it is a
three-stage chain with no branch.

Rejected alongside it: replacing the adjudication fan-out with a
`@node(parallel_worker=True)`. That primitive does handle dynamic runtime lists,
so the usual objection to `ParallelAgent` does not apply — but
`asyncio.gather(..., return_exceptions=True)` already gives per-item isolation,
and the current code turns one failed item into "stays open, retried next
chunk", behaviour that would have to be rebuilt inside the node. The gain is
ADK-native span naming.

## What would make this wrong

- ADK giving graph nodes a default `content`, or `agents-cli eval` tolerating
  content-less events. Either removes the blocker entirely.
- A genuine branch appearing in the turn — the likeliest is a degraded or
  silent chunk short-circuiting past adjudication. A plain function node
  emitting `Event(route=…)` is the idiomatic shape for that, and at two or more
  such branches the graph starts earning its keep.
- Needing per-node retry/timeout around the Vertex calls badly enough to want
  `RetryConfig` rather than owning the retry.

## Not verified

- That an auto-wrapped `LlmAgent` node emits `content` of its own. It plausibly
  does, being a model response; it was not run, because it costs a Vertex call.
- The rejection was reproduced in-process via `InMemoryRunner`, not over the
  `/run_sse` HTTP path `eval generate` actually uses. `content=None` serialises
  as absent, so the outcome should be identical — but it was not proven.

## Consequences

`google.adk.workflow` is unused. Edge literal forms, recorded so the next person
does not rediscover them: `(from, to)` and `(from, to, route)`-as-`Edge(...)`
and `{"route": node}` are accepted; a bare **3-tuple is not** — it raises
`ValidationError`. `DEFAULT_ROUTE` is `'__DEFAULT__'`, and a route with no
matching edge ends that branch and warns.
