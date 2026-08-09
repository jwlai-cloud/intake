"""The behavioural eval's metrics, exercised without spending anything.

`tests/eval/eval_config.yaml` holds three `custom_function` metrics. They run
inside agents-cli, against traces that cost Vertex calls to produce — so a bug
in one is normally found by paying for a run and getting a confusing zero.

These tests exec each metric against a synthetic trace instead. A metric that
cannot tell a good trace from a bad one is caught here, for free.
"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml

CONFIG = pathlib.Path(__file__).parent / "eval" / "eval_config.yaml"

SAID = ("Practitioner: Have you had any falls in the last year?\n"
        "Interviewee: Three times since Christmas. I slipped coming down the stairs.")


def _metric(name: str):
    """Compile one metric's `evaluate` out of the eval config."""
    spec = yaml.safe_load(CONFIG.read_text())
    for entry in spec["custom_metrics"]:
        if entry["name"] == name:
            ns: dict = {}
            exec(entry["custom_function"], ns)  # noqa: S102 - that is the contract
            return ns["evaluate"]
    raise AssertionError(f"no metric named {name}")


def _instance(coaching: dict, said: str = SAID) -> dict:
    """A trace shaped the way agents-cli hands it to a code metric."""
    return {
        "prompt": {"role": "user", "parts": [{"text": said}]},
        "agent_data": {"turns": [{"events": [
            {"author": "adjudication",
             "content": {"parts": [{"text": "Adjudicated 1 of 14 open items."}]}},
            {"author": "coach",
             "content": {"parts": [{"text": json.dumps(coaching)}]}},
        ]}]},
    }


def _coaching(**over) -> dict:
    base = {
        "next_question": {"item_id": "M14", "prompt": "How many?", "why": "count"},
        "highlights": [{"item_id": "M14", "title": "Falls",
                        "quote": "Three times since Christmas."}],
    }
    base.update(over)
    return base


# --- quotes must be verbatim -------------------------------------------------

def test_verbatim_metric_passes_a_real_quote():
    assert _metric("highlight_quotes_are_verbatim")(_instance(_coaching()))["score"] == 1


def test_verbatim_metric_catches_a_paraphrase():
    bad = _coaching(highlights=[{"item_id": "M14", "title": "Falls",
                                 "quote": "She has fallen three times."}])
    result = _metric("highlight_quotes_are_verbatim")(_instance(bad))
    assert result["score"] == 0
    assert "not present" in result["explanation"]


def test_verbatim_metric_tolerates_a_curly_apostrophe():
    """Normalisation is the difference between a guard and a nuisance."""
    said = "Interviewee: I don't go out much."
    ok = _coaching(highlights=[{"item_id": "M14", "title": "Mobility",
                                "quote": "I don’t go out much."}])
    assert _metric("highlight_quotes_are_verbatim")(
        _instance(ok, said=said))["score"] == 1


def test_verbatim_metric_fails_loudly_when_the_coach_said_nothing():
    empty = {"prompt": {"parts": [{"text": SAID}]}, "agent_data": {"turns": []}}
    assert _metric("highlight_quotes_are_verbatim")(empty)["score"] == 0


# --- next_question must name a real item -------------------------------------

def test_next_question_metric_accepts_a_template_item():
    assert _metric("next_question_targets_a_real_item")(
        _instance(_coaching()))["score"] == 1


def test_next_question_metric_rejects_an_invented_item():
    bad = _coaching(next_question={"item_id": "M99", "prompt": "?", "why": "?"})
    result = _metric("next_question_targets_a_real_item")(_instance(bad))
    assert result["score"] == 0
    assert "M99" in result["explanation"]


# --- titles must be bare labels (ADR-0006) -----------------------------------

def test_title_metric_accepts_a_topic_label():
    assert _metric("highlight_titles_are_bare_labels")(
        _instance(_coaching()))["score"] == 1


@pytest.mark.parametrize("title", [
    "Formal decline to answer alcohol question",   # the one actually observed
    "Reluctant about alcohol",
    "Possible falls risk",
])
def test_title_metric_catches_characterisation(title):
    bad = _coaching(highlights=[{"item_id": "M24", "title": title, "quote": ""}])
    assert _metric("highlight_titles_are_bare_labels")(_instance(bad))["score"] == 0


@pytest.mark.parametrize("title", [
    "Informal support arrangements",   # contains "formal" as a substring only
    "Falls in the last 12 months",     # the template's own item prompt
    "Details of most recent fall",
    "Medication adherence",
])
def test_title_metric_accepts_legitimate_labels(title):
    """These four all failed the first version of this metric. Three were the
    metric's fault, not the agent's — a substring test and too tight a word cap."""
    ok = _coaching(highlights=[{"item_id": "M14", "title": title, "quote": ""}])
    assert _metric("highlight_titles_are_bare_labels")(_instance(ok))["score"] == 1
