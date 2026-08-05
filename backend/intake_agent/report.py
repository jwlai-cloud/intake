"""Report assembly.

Deliberately has no model call in it. The report is assembled from what was
actually recorded — the practitioner's own words, the interviewee's quoted
span, the reason a decline was accepted, the follow-up that was filed. Asking a
model to write the prose would be the agent authoring domain content, which is
the one thing ADR-0006 forbids.

The consequence is a plainer report than a summarising scribe would produce.
That is the trade being made on purpose: every line is traceable to something
said or something a human typed.
"""

from __future__ import annotations

from .store import ANSWERED, DECLINED, ESCALATED, SessionState


def build(session: SessionState) -> dict:
    """Assemble the report. Assumes the gate has passed; states it if not."""
    template = session.template
    required = set(template.required_ids(session.slots))

    sections = []
    for section_id, section_title in template.section_order:
        entries = []
        for item in template.items.values():
            if item.section_id != section_id or item.id not in required:
                continue
            slot = session.slots.get(item.id, {})
            entries.append({
                "item_id": item.id,
                "prompt": item.prompt,
                "state": slot.get("state", "open"),
                "text": _entry_text(item, slot),
                "evidence": slot.get("evidence", ""),
                "high_risk": item.high_risk,
                "written_by": slot.get("source", ""),
            })
        if entries:
            sections.append({"id": section_id, "title": section_title,
                             "entries": entries})

    return {
        "template_id": template.template_id,
        "title": template.title,
        "generated_from": {
            "resolved": session.coverage()[0],
            "required": session.coverage()[1],
        },
        "sections": sections,
        "flags": _flags(session, required),
        "followups": list(session.followups),
        "unresolved": session.outstanding_ids(),
    }


def _entry_text(item, slot: dict) -> str:
    state = slot.get("state")
    if state == ANSWERED:
        return slot.get("value") or slot.get("evidence") or ""
    if state == DECLINED:
        return f"Declined. Reason recorded: {slot.get('reason') or 'none given'}."
    if state == ESCALATED:
        return (f"Not resolved during the visit. Follow-up action filed: "
                f"{slot.get('reason') or 'no reason recorded'}.")
    # Only reachable if the gate was bypassed; say so rather than leave a blank.
    return "No recorded answer."


def _flags(session: SessionState, required: set[str]) -> list[dict]:
    """Entries a reader should look at twice, and why."""
    flags = []
    for item_id in sorted(required):
        item = session.template[item_id]
        slot = session.slots.get(item_id, {})
        if item.high_risk and slot.get("state") == ANSWERED:
            flags.append({
                "item_id": item_id,
                "note": (
                    f"{item_id} is a high-risk item. "
                    + ("Response written by the practitioner after review of the "
                       "recorded quote."
                       if slot.get("source") == "practitioner"
                       else "Response derived from the interview transcript; "
                            "confirm before signing off.")
                ),
            })
        if slot.get("state") == DECLINED:
            flags.append({"item_id": item_id,
                          "note": f"{item_id} recorded as declined by the interviewee."})
    return flags
