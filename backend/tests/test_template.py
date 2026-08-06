"""Template engine: the whole vertical is config, so this is where it is proved."""

import pytest

from intake_agent.template import Template, TemplateError


def test_loads_the_shipped_nursing_template():
    t = Template.load("community-nursing-v1")
    assert t.title == "Community nursing · home visit"
    assert t["M14"].high_risk is True
    assert t["M14"].accepts_declined is False
    assert t["M08"].accepts_declined is True


def test_every_required_item_carries_guidance():
    # Without a guidance note the adjudicator has nothing authoritative to judge
    # against and falls back on its own taste, which is the failure mode ADR-0006
    # exists to prevent.
    for tid in Template.available():
        for item in Template.load(tid).items.values():
            assert item.guidance.strip(), f"{tid}/{item.id} has no guidance"


def test_unconditional_required_set_excludes_conditional_items():
    t = Template.load("community-nursing-v1")
    required = t.required_ids({})
    assert "M14" in required
    assert "M15" not in required, "conditional item must not be required up front"
    assert "M05" not in required


def test_depends_on_opens_a_conditional_item():
    t = Template.load("community-nursing-v1")
    slots = {"M14": {"state": "answered", "value": "Three falls, the last in May."}}
    assert "M15" in t.required_ids(slots)


def test_depends_on_stays_shut_when_the_pattern_does_not_match():
    t = Template.load("community-nursing-v1")
    slots = {"M14": {"state": "answered", "value": "None at all in the last year."}}
    assert "M15" not in t.required_ids(slots)


def test_depends_on_stays_shut_while_the_parent_is_unresolved():
    t = Template.load("community-nursing-v1")
    slots = {"M14": {"state": "open", "value": "Three falls maybe"}}
    assert "M15" not in t.required_ids(slots)


def test_declining_the_parent_does_not_open_the_child():
    t = Template.load("community-nursing-v1")
    slots = {"M14": {"state": "declined", "value": "", "reason": "Not today"}}
    assert "M15" not in t.required_ids(slots)


def test_second_template_needs_no_code_change():
    # ADR-0003's actual test. If this file ever needs a branch on template_id,
    # the engine is not decoupled.
    t = Template.load("loss-adjusting-v1")
    assert t.items, "loss adjusting template is empty"
    assert t.required_ids({})


def test_unknown_template_is_a_clear_error():
    with pytest.raises(TemplateError):
        Template.load("no-such-template")


def test_depends_on_pointing_at_a_missing_item_is_rejected_at_load():
    with pytest.raises(TemplateError, match="M99"):
        Template.from_dict(
            {
                "template_id": "broken",
                "title": "Broken",
                "sections": [
                    {
                        "id": "s",
                        "title": "S",
                        "items": [
                            {
                                "id": "A1",
                                "prompt": "p",
                                "guidance": "g",
                                "required": True,
                                "depends_on": {"item": "M99", "when": "answered"},
                            }
                        ],
                    }
                ],
            }
        )


def test_duplicate_item_ids_are_rejected_at_load():
    item = {"id": "A1", "prompt": "p", "guidance": "g", "required": True}
    with pytest.raises(TemplateError, match="A1"):
        Template.from_dict(
            {
                "template_id": "dupes",
                "title": "Dupes",
                "sections": [
                    {"id": "s1", "title": "S1", "items": [item]},
                    {"id": "s2", "title": "S2", "items": [dict(item)]},
                ],
            }
        )


def test_the_medication_condition_reads_meaning_not_keywords():
    """M05 opens when someone else prepares the doses, or adherence is shaky.

    Pinned because the original pattern contained a bare "miss", which matched
    "I take them with breakfast and never miss" — the exact opposite of what it
    was looking for, and it silently added a required item to every session.
    """
    import re
    t = Template.load("community-nursing-v1")
    pattern = t["M05"].depends_on["pattern"]

    opens = [
        "I do forget the evening one two or three times a week.",
        "My daughter helps me with the box.",       # someone else prepares them
        "She helps me with the dosette box.",
        "I'm not sure what half of them are for.",
        "Someone else sets them out for me.",
    ]
    stays_shut = [
        "Ramipril and atorvastatin, I take them with breakfast and never miss.",
        "I manage them all myself, always have.",
    ]
    for text in opens:
        assert re.search(pattern, text), f"should have opened M05: {text}"
    for text in stays_shut:
        assert not re.search(pattern, text), f"should not have opened M05: {text}"
