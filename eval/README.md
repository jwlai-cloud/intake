# Adjudicator eval

The adjudicator is the product. This harness exists so its quality is a
measured number rather than a vibe, and so a regression is visible immediately.

## The bar

**It must never mark an answer sufficient that a case labels insufficient.**

False "sufficient" is the failure that destroys the product: it silently ticks
an item that was never really answered, which is exactly the behaviour every
competitor already has and the thing Intake exists to fix. False "insufficient"
is annoying but safe — it asks one extra question.

So the target is high precision on *sufficient*. Track both, optimise that one.

## Layout

One JSON file per case in `cases/`:

```jsonc
{
  "case_id": "M14-vague-wobbles",
  "item": {
    "id": "M14",
    "prompt": "Falls in the last 12 months",
    "answer_type": "structured",
    "required": true
  },
  "guidance": "A sufficient answer records the number of falls and the circumstances of the most recent. 'A few' or 'some' is not sufficient.",
  "utterance": "Oh, I've had a couple of wobbles.",
  "label": "insufficient",
  "why": "No count, no circumstances. Mentioned, not answered — this is the demo's headline beat."
}
```

Aim for roughly 30 cases: for each required item in the template, several
answers that should count and several that should not. Include the awkward ones —
partial answers, answers that arrive across two turns, and answers where the
subject declines (which is `declined`, not `insufficient`).

## Running

```bash
uv run python run_eval.py            # all cases
uv run python run_eval.py --item M14 # one item
```

Print a confusion matrix and fail non-zero if any `insufficient` case was marked
sufficient. Commit the score in `PROGRESS.md` whenever the prompt changes.

## Demo cases

Cases used in the demo script are tagged `"demo": true`. Those phrasings must be
stable — the contest requires an unedited take, so a wrong tick on camera cannot
be edited out. Run them repeatedly before recording day.
