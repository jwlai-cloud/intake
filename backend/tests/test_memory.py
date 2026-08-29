"""Practitioner memory — and the boundary it must never cross.

The product's privacy guarantee is that Intake learns about the *practitioner*
and never about the people she interviews. That is a claim in the README, in
the submission, and in the demo narration, so it needs to be a claim the test
suite can fail on.
"""

from __future__ import annotations

import pytest

from intake_agent.memory import (DISMISS_THRESHOLD, PHRASINGS_PER_ITEM,
                                 PractitionerMemory, brief_section)
from intake_agent.store import MemoryStore


@pytest.fixture
def store():
    return MemoryStore()


# --- the boundary ------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "I've had a couple of wobbles.",
    "Three times since Christmas. I slipped coming down the stairs.",
    'She said "I don\'t go out much" when asked about mobility.',
    "My daughter Sarah drives me on Mondays.",
    "The patient reports falling twice.",
])
def test_interviewee_speech_is_never_remembered(store, text):
    """Every one of these is someone talking about their own life. None of it
    may survive the session, whatever route it arrives by."""
    store.count_interview("nurse-a")
    store.remember_effective_phrasing("nurse-a", "M14", text)
    assert store.memory("nurse-a").effective_phrasings == {}


@pytest.mark.parametrize("question", [
    "How many times, and what happened the last one?",
    "Could you tell me what prompted the referral, and roughly when it started?",
    "Is that patch at the bottom of your back red, sore, or is the skin broken?",
])
def test_the_agents_own_questions_are_remembered(store, question):
    store.count_interview("nurse-a")
    store.remember_effective_phrasing("nurse-a", "M14", question)
    assert store.memory("nurse-a").effective_phrasings["M14"] == [question]


def test_memory_never_crosses_between_practitioners(store):
    store.count_interview("nurse-a")
    store.remember_effective_phrasing("nurse-a", "M14", "How many falls, and when?")
    store.remember_dismissal("nurse-a", "M18")

    other = store.memory("nurse-b")
    assert other.effective_phrasings == {}
    assert other.dismissed_counts == {}
    assert brief_section(other, ["M14", "M18"]) == "", \
        "a second practitioner must inherit nothing"


# --- behaviour ---------------------------------------------------------------

def test_a_category_is_muted_only_after_repeated_dismissal(store):
    for n in range(1, DISMISS_THRESHOLD + 1):
        store.remember_dismissal("nurse-a", "M18")
        muted = store.memory("nurse-a").muted_items()
        assert ("M18" in muted) is (n >= DISMISS_THRESHOLD), \
            "one impatient dismissal must not silence a category"


def test_only_the_most_recent_phrasings_are_kept(store):
    store.count_interview("nurse-a")
    for n in range(PHRASINGS_PER_ITEM + 3):
        store.remember_effective_phrasing("nurse-a", "M14", f"Question number {n}?")
    kept = store.memory("nurse-a").effective_phrasings["M14"]
    assert len(kept) == PHRASINGS_PER_ITEM
    assert kept[0] == f"Question number {PHRASINGS_PER_ITEM + 2}?", "newest first"


def test_a_duplicate_phrasing_is_not_stored_twice(store):
    store.count_interview("nurse-a")
    for _ in range(3):
        store.remember_effective_phrasing("nurse-a", "M14", "How many, and when?")
    assert store.memory("nurse-a").effective_phrasings["M14"] == ["How many, and when?"]


# --- what reaches the coach --------------------------------------------------

def test_the_first_interview_carries_no_memory(store):
    mem = PractitionerMemory(practitioner_id="nurse-a",
                             effective_phrasings={"M14": ["How many, and when?"]})
    assert brief_section(mem, ["M14"]) == "", \
        "nothing has been learned yet, so the brief must not claim otherwise"


def test_the_brief_offers_a_phrasing_only_for_items_still_open(store):
    store.count_interview("nurse-a")
    store.remember_effective_phrasing("nurse-a", "M14", "How many falls, and when?")
    store.remember_effective_phrasing("nurse-a", "M06", "How do you get around indoors?")

    brief = brief_section(store.memory("nurse-a"), ["M14"])
    assert "How many falls, and when?" in brief
    assert "M06" not in brief, "a closed item must not pad the brief"


def test_a_muted_category_still_gets_asked_but_not_highlighted(store):
    for _ in range(DISMISS_THRESHOLD):
        store.remember_dismissal("nurse-a", "M18")
    store.count_interview("nurse-a")
    brief = brief_section(store.memory("nurse-a"), ["M18"])
    assert "M18" in brief
    assert "do not propose a highlight" in brief
    assert "Still" in brief and "ask the question" in brief, \
        "muting a highlight must never mute the required question"
