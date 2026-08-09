# Behavioural eval — the pipeline, not the adjudicator

Two eval suites exist and they test different things. Neither replaces the other.

| | `eval/run_eval.py` | `backend/tests/eval/` (here) |
|---|---|---|
| Unit under test | `adjudicate()` — a function | the whole turn pipeline |
| Question | did this answer satisfy the guidance? | what did the coach do with the verdict? |
| Cases | 47 labelled | 3 |
| Grading | exact label match, hard gate | deterministic code metrics |
| Calls per run | 47 | ~15 |

The first is the product's core guarantee and the reason the project exists.
This one covers the layer it cannot see: the adjudicator can be perfectly right
and the coach can still fabricate a quote, invent an item id, or characterise
the person. Those are trajectory properties, and they are what ADK's eval
harness is for.

## Running it

```bash
cd backend
uv run agents-cli eval run --config tests/eval/eval_config.yaml
```

`eval run` chains `generate` (inference — this is the part that costs money)
and `grade` (free, see below). Results land in `artifacts/grade_results/` as
timestamped `.json` and `.html`.

## Cost, deliberately

Roughly **15 Gemini calls per run**: 3 cases through
`transcribe → route → ~2 × adjudicate → coach`.

Two choices keep it there, and both are load-bearing:

**Every metric is a `custom_function`.** Code metrics execute locally,
in-process, and make **no model calls**. Grading is free. The built-in metrics
(`multi_turn_task_success`, `final_response_quality`, …) are LLM-as-judge — one
judge call per case per metric — and they cannot check any property here
anyway. A judge asked "is this quote verbatim?" is strictly worse than `in`.
Do not add them without deciding you want to pay for them.

**The dataset uses text prompts, not audio.** Audio tokens dominate this
pipeline's cost and none of these properties need real speech. The transcriber
still runs; it just runs cheap.

For scale: the demo's TTS cache holds 115 clips / 48MB, and every script edit
invalidates clips by content hash. That, not evaluation, is where this project's
Vertex spend has gone.

## The metrics

| Metric | Guards | Fails when |
|---|---|---|
| `highlight_quotes_are_verbatim` | ADR-0006 | a quote shown to the practitioner as verbatim is not in the transcript |
| `next_question_targets_a_real_item` | coverage | the coach invents an item id, so the panel silently shows no next question |
| `highlight_titles_are_bare_labels` | ADR-0006 | a title characterises the answer or the person rather than naming a topic |

The third exists because behavioural review found the hole the schema does not
close: the coach's output schema forbids an answer *field*, but not an
interpretive *label*. The agent once emitted `"Formal decline to answer alcohol
question"` — a characterisation, not a topic. That exact string is a test case.

## The metrics are tested without running the eval

`backend/tests/test_eval_metrics.py` execs each metric against synthetic traces
and asserts it separates a good trace from a bad one. A broken metric is
normally discovered by paying for a run and getting a confusing zero; those
tests catch it for free, in `pytest`.

Run them like any other test:

```bash
cd backend && uv run pytest tests/test_eval_metrics.py
```
