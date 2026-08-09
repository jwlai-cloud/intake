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

`agents-cli eval run` does **not** work here, and the reason is worth knowing:
it derives the ADK app name from the manifest's `agent_directory`, so it asks
the server for an app called `backend/adk_apps/intake`. ADK's `api_server`
serves apps by *directory name* — `intake` — and returns 404 for the path form.

Start the server yourself, rooted at the package's parent, and point eval at it:

```bash
# terminal 1 — from backend/
PYTHONPATH=$PWD uv run adk api_server adk_apps --port 18099
curl -s localhost:18099/list-apps          # => ["intake"]

# terminal 2 — from the repo root
uv run agents-cli eval generate --url http://127.0.0.1:18099 --app-name intake \
    --dataset backend/tests/eval/datasets/pipeline.json
uv run agents-cli eval grade --config backend/tests/eval/eval_config.yaml \
    --traces artifacts/traces/<the file generate just wrote>
```

**Pass `--traces` explicitly.** Without it, `grade` loads *every* trace file in
`artifacts/traces/` and averages them together. Stale traces from an earlier
run will drag a passing score down and, worse, report failures that the current
code does not produce — which is exactly what happened the first time this ran:
a title bug fixed days earlier reappeared in the summary because a 6 Aug trace
was still sitting in the directory.

If Vertex returns `403 PERMISSION_DENIED` on `aiplatform.endpoints.predict`
despite you owning the project, check `GOOGLE_APPLICATION_CREDENTIALS` — if it
points at another project's service account it silently overrides ADC, and
every call authenticates as the wrong principal. `env -u
GOOGLE_APPLICATION_CREDENTIALS` in front of the command is the quick check.

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

They earned their keep immediately. The first real run scored the title metric
at 0.667, and three of its four failures were the metric's fault, not the
agent's: a substring test flagged `"Informal support arrangements"` for
containing `"formal"`, and a four-word cap rejected the template's own item
prompt `"Falls in the last 12 months"`. Both are now regression tests.

## Result, 9 Aug 2026

Three cases, current code, graded against today's traces only:

| Metric | Score |
|---|---|
| `highlight_quotes_are_verbatim` | 1.00 |
| `next_question_targets_a_real_item` | 1.00 |
| `highlight_titles_are_bare_labels` | 1.00 |

Titles emitted were `Mobility`, `Falls`, `Alcohol intake` — the decline case,
which historically produced `"Formal decline to answer alcohol question"`, now
names the topic and nothing more.

Three cases is a small sample and should not be read as more than it is: it
says the pipeline holds on the three scenarios the demo shows, not that it
holds generally.
