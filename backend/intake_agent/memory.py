"""What the agent learns, and the hard limit on what it may learn.

Intake gets better at helping *one practitioner* across her interviews. It
learns nothing whatsoever about the people she interviews.

That is not a policy note bolted onto a general-purpose memory. It is the
design, and this module is where it is enforced:

* memory is keyed on `practitioner_id`, and there is no other key
* only two kinds of fact are storable — a **question phrasing** the agent
  itself authored, and an **item id** whose highlights she keeps dismissing
* `_carries_interviewee_speech()` rejects anything that looks like a recorded
  answer before it can be written

The distinction that makes this safe: a *question* is the agent's own text,
composed from a human-authored template. An *answer* is a person speaking about
their own health. The first can be remembered across interviews. The second is
the thing this product exists to keep inside one session (ADR-0007).

So the useful version of "the agent learns" is:

    nurses who ask M14 this way close it first time;
    your usual phrasing takes three turns

and never:

    people like this one usually under-report falls
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# How many phrasings to keep per item. This is a nudge, not a corpus: the coach
# gets one worked example, and a long list would crowd out the brief that
# actually describes the interview in front of her.
PHRASINGS_PER_ITEM = 3

# Dismiss this many times before the agent stops proposing that category. Two
# is impatient — a practitioner may dismiss a good suggestion because she was
# mid-sentence. Four takes too long to be felt inside a hackathon demo.
DISMISS_THRESHOLD = 3


@dataclass
class PractitionerMemory:
    """Everything remembered about one practitioner. Never about a subject."""

    practitioner_id: str
    # item_id -> [question phrasings that closed it on the first ask]
    effective_phrasings: dict[str, list[str]] = field(default_factory=dict)
    # item_id -> how many times she has dismissed a highlight for it
    dismissed_counts: dict[str, int] = field(default_factory=dict)
    interviews: int = 0

    def to_dict(self) -> dict:
        return {
            "practitioner_id": self.practitioner_id,
            "effective_phrasings": {k: list(v) for k, v in self.effective_phrasings.items()},
            "dismissed_counts": dict(self.dismissed_counts),
            "interviews": self.interviews,
        }

    @staticmethod
    def from_dict(raw: dict) -> PractitionerMemory:
        return PractitionerMemory(
            practitioner_id=raw["practitioner_id"],
            effective_phrasings={k: list(v) for k, v in
                                 (raw.get("effective_phrasings") or {}).items()},
            dismissed_counts=dict(raw.get("dismissed_counts") or {}),
            interviews=int(raw.get("interviews") or 0),
        )

    def muted_items(self) -> set[str]:
        """Items whose highlights she has told us, repeatedly, not to propose."""
        return {i for i, n in self.dismissed_counts.items() if n >= DISMISS_THRESHOLD}


# A phrasing is a question the agent wrote. These are the shapes that betray a
# recorded answer instead — first person, or a quoted span. Cheap and blunt on
# purpose: the cost of a false reject is one unlearned phrasing, and the cost of
# a false accept is a patient's words surviving their session.
# Deliberately narrow. "me" and "we" are not markers of interviewee speech —
# "could you tell me…" and "shall we start with…" are ordinary questions, and an
# early version rejected both. What betrays a recorded answer is a first-person
# *subject*: someone describing their own life.
_FIRST_PERSON = re.compile(r"\b(i|i'm|i've|i'd|i'll|my|mine)\b", re.IGNORECASE)


def _carries_interviewee_speech(text: str) -> bool:
    if '"' in text or "“" in text or "”" in text:
        return True          # a quoted span is a recorded answer, not a question
    if not text.rstrip().endswith("?"):
        return True          # the agent's phrasings are questions; answers are not
    return bool(_FIRST_PERSON.search(text))


class PractitionerMemoryMixin:
    """Memory operations for a store. Mixed into `BaseStore`.

    Kept apart from the session methods so the two never share a code path: a
    session write may carry interviewee speech, a memory write may not, and the
    separation should be visible in the file tree rather than only in review.
    """

    def _load_memory(self, practitioner_id: str) -> PractitionerMemory:
        raise NotImplementedError

    def _save_memory(self, memory: PractitionerMemory) -> None:
        raise NotImplementedError

    def memory(self, practitioner_id: str) -> PractitionerMemory:
        return self._load_memory(practitioner_id)

    def remember_effective_phrasing(self, practitioner_id: str, item_id: str,
                                    phrasing: str) -> None:
        """Record a question that closed an item on the first ask."""
        phrasing = " ".join((phrasing or "").split())
        if not phrasing:
            return
        if _carries_interviewee_speech(phrasing):
            # Loud, because silently dropping this would hide a real leak.
            log.warning("refusing to remember a phrasing for %s: it does not "
                        "look like a question the agent wrote", item_id)
            return

        mem = self._load_memory(practitioner_id)
        known = mem.effective_phrasings.setdefault(item_id, [])
        if phrasing in known:
            return
        known.insert(0, phrasing)
        del known[PHRASINGS_PER_ITEM:]
        self._save_memory(mem)
        log.info("learned a phrasing that closed %s first time for %s",
                 item_id, practitioner_id)

    def remember_dismissal(self, practitioner_id: str, item_id: str) -> None:
        mem = self._load_memory(practitioner_id)
        mem.dismissed_counts[item_id] = mem.dismissed_counts.get(item_id, 0) + 1
        self._save_memory(mem)
        if mem.dismissed_counts[item_id] == DISMISS_THRESHOLD:
            log.info("%s has dismissed %s highlights %d times — muting them",
                     practitioner_id, item_id, DISMISS_THRESHOLD)

    def count_interview(self, practitioner_id: str) -> None:
        mem = self._load_memory(practitioner_id)
        mem.interviews += 1
        self._save_memory(mem)


def brief_section(mem: PractitionerMemory, open_item_ids: list[str]) -> str:
    """The memory's contribution to the coach brief. Empty on a first interview.

    Only phrasings for items that are *currently open* are included — memory
    should sharpen the next question, not pad the prompt with everything ever
    learned.
    """
    if mem.interviews < 1:
        return ""

    lines: list[str] = []
    relevant = [(i, mem.effective_phrasings[i]) for i in open_item_ids
                if mem.effective_phrasings.get(i)]
    if relevant:
        lines.append(
            "\nFrom this practitioner's previous interviews — phrasings that "
            "closed these items on the first ask. Reuse or adapt them:")
        for item_id, phrasings in relevant:
            lines.append(f'- {item_id}: "{phrasings[0]}"')

    muted = sorted(mem.muted_items() & set(open_item_ids))
    if muted:
        lines.append(
            "\nShe has repeatedly dismissed highlights for these items. Still "
            "ask the question if the item is open, but do not propose a "
            "highlight for them: " + ", ".join(muted))

    return "\n".join(lines)
