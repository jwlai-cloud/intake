"""The template *is* the vertical (ADR-0003).

Nothing in this module knows what a fall, a water leak or a fire door is. It
knows that items have guidance, that some items are required, and that some
items become required only once another item has been answered in a particular
way. Adding a second vertical must not add a line of code here.
"""

from __future__ import annotations

import functools
import json
import os
import pathlib
import re
from dataclasses import dataclass, field

TEMPLATE_DIR = pathlib.Path(
    os.environ.get(
        "INTAKE_TEMPLATE_DIR",
        pathlib.Path(__file__).resolve().parents[2] / "templates",
    )
)

# `depends_on.when` values. Deliberately a closed set rather than an expression
# language: a template is authored by a domain expert, not a programmer, and an
# eval'd expression in a config file is an injection surface.
WHEN_ANSWERED = "answered"
WHEN_ANSWERED_AND_MATCHES = "answered_and_matches"
WHEN_VALUES = {WHEN_ANSWERED, WHEN_ANSWERED_AND_MATCHES}


class TemplateError(Exception):
    """A template is malformed, missing, or refers to an item that does not exist."""


@dataclass(frozen=True)
class Item:
    id: str
    prompt: str
    guidance: str
    required: bool = False
    answer_type: str = "free_text"
    high_risk: bool = False
    accepts_declined: bool = False
    guidance_ref: str = ""
    depends_on: dict | None = None
    section_id: str = ""
    section_title: str = ""


@dataclass(frozen=True)
class Template:
    template_id: str
    title: str
    subtitle: str
    items: dict[str, Item]
    section_order: list[tuple[str, str]] = field(default_factory=list)

    # --- loading -----------------------------------------------------------

    @staticmethod
    def available() -> list[str]:
        return sorted(p.stem for p in TEMPLATE_DIR.glob("*.json"))

    @staticmethod
    @functools.lru_cache(maxsize=8)
    def load(template_id: str) -> Template:
        path = TEMPLATE_DIR / f"{template_id}.json"
        if not path.is_file():
            raise TemplateError(
                f"no template {template_id!r} in {TEMPLATE_DIR} "
                f"(have: {', '.join(Template.available()) or 'none'})"
            )
        return Template.from_dict(json.loads(path.read_text()))

    @staticmethod
    def from_dict(raw: dict) -> Template:
        items: dict[str, Item] = {}
        sections: list[tuple[str, str]] = []
        for section in raw.get("sections", []):
            sections.append((section["id"], section["title"]))
            for spec in section.get("items", []):
                item = Item(
                    id=spec["id"],
                    prompt=spec["prompt"],
                    guidance=spec.get("guidance", ""),
                    required=bool(spec.get("required", False)),
                    answer_type=spec.get("answer_type", "free_text"),
                    high_risk=bool(spec.get("high_risk", False)),
                    accepts_declined=bool(spec.get("accepts_declined", False)),
                    guidance_ref=spec.get("guidance_ref", ""),
                    depends_on=spec.get("depends_on"),
                    section_id=section["id"],
                    section_title=section["title"],
                )
                if item.id in items:
                    raise TemplateError(f"duplicate item id {item.id!r}")
                items[item.id] = item

        template = Template(
            template_id=raw["template_id"],
            title=raw["title"],
            subtitle=raw.get("subtitle", ""),
            items=items,
            section_order=sections,
        )
        template._validate()
        return template

    def _validate(self) -> None:
        for item in self.items.values():
            dep = item.depends_on
            if dep is None:
                continue
            if dep.get("item") not in self.items:
                raise TemplateError(
                    f"{item.id}.depends_on points at unknown item {dep.get('item')!r}"
                )
            if dep.get("when") not in WHEN_VALUES:
                raise TemplateError(
                    f"{item.id}.depends_on.when must be one of {sorted(WHEN_VALUES)}"
                )
            if dep["when"] == WHEN_ANSWERED_AND_MATCHES:
                try:
                    re.compile(dep.get("pattern", ""))
                except re.error as exc:
                    raise TemplateError(f"{item.id}.depends_on.pattern: {exc}") from exc

    # --- interpretation ----------------------------------------------------

    def __getitem__(self, item_id: str) -> Item:
        try:
            return self.items[item_id]
        except KeyError:
            raise TemplateError(f"unknown item {item_id!r}") from None

    def required_ids(self, slots: dict[str, dict]) -> list[str]:
        """Item ids required *given what has been answered so far*.

        An item with `depends_on` is required exactly when its condition holds.
        An item without one is required exactly when `required` is true. The
        required set is therefore recomputed after every chunk, not fixed at
        session start.
        """
        out = []
        for item in self.items.values():
            if item.depends_on is not None:
                if self._dependency_met(item.depends_on, slots):
                    out.append(item.id)
            elif item.required:
                out.append(item.id)
        return out

    def _dependency_met(self, dep: dict, slots: dict[str, dict]) -> bool:
        parent = slots.get(dep["item"]) or {}
        if parent.get("state") != "answered":
            return False
        if dep["when"] == WHEN_ANSWERED:
            return True
        return bool(re.search(dep.get("pattern", ""), parent.get("value") or ""))

    def ordered(self, item_ids) -> list[Item]:
        """Item objects in template order — the order the form itself is in."""
        wanted = set(item_ids)
        return [i for i in self.items.values() if i.id in wanted]
